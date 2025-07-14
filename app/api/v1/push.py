from fastapi import APIRouter, Request, Response, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List, Union
import json
import uuid
from datetime import datetime
import os
import base64
try:
    from pywebpush import webpush, WebPushException
except ImportError:
    print("Warning: pywebpush not installed. Push notifications will not work.")
    
router = APIRouter()

# Store subscriptions in memory for demo purposes
# In a real app, these would be stored in a database
subscriptions = []

# Get VAPID keys from environment variables
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
VAPID_CLAIMS = {
    "sub": "mailto:admin@wazir.ru"
}

@router.get("/vapid-key")
async def get_vapid_key():
    """Get the public VAPID key for push notifications"""
    if not VAPID_PUBLIC_KEY:
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": "VAPID keys not configured on the server"}
        )
    return {"publicKey": VAPID_PUBLIC_KEY}

@router.post("/subscribe")
async def subscribe(request: Request):
    """Save a new push subscription"""
    try:
        subscription_data = await request.json()
        
        # Validate subscription data
        if not subscription_data or not subscription_data.get("endpoint"):
            return JSONResponse(
                status_code=400, 
                content={"success": False, "message": "Invalid subscription data"}
            )
        
        # Create subscription object
        subscription = {
            "id": str(uuid.uuid4()),
            "user_id": "admin",  # In a real app, get from session
            "subscription": subscription_data,
            "created_at": datetime.now().isoformat()
        }
        
        # Update existing subscription or add new one
        for idx, sub in enumerate(subscriptions):
            if sub.get("subscription", {}).get("endpoint") == subscription_data.get("endpoint"):
                subscriptions[idx] = subscription
                return {"success": True, "message": "Subscription updated"}
        
        subscriptions.append(subscription)
        return {"success": True, "message": "Successfully subscribed to notifications"}
        
    except Exception as e:
        print(f"Error saving subscription: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

@router.post("/unsubscribe")
async def unsubscribe(request: Request):
    """Cancel a push subscription"""
    try:
        subscription_data = await request.json()
        
        if not subscription_data or not subscription_data.get("endpoint"):
            return JSONResponse(
                status_code=400, 
                content={"success": False, "message": "Invalid subscription data"}
            )
        
        # Remove subscription with matching endpoint
        endpoint = subscription_data.get("endpoint")
        for idx, sub in enumerate(subscriptions):
            if sub.get("subscription", {}).get("endpoint") == endpoint:
                del subscriptions[idx]
                return {"success": True, "message": "Subscription canceled"}
        
        return {"success": True, "message": "Subscription not found"}
        
    except Exception as e:
        print(f"Error canceling subscription: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

@router.post("/test")
async def send_test_push(request: Request, background_tasks: BackgroundTasks):
    """Send a test push notification"""
    try:
        if not subscriptions:
            return {"success": False, "message": "No active subscriptions"}
        
        # Data for test notification
        notification_data = {
            "title": "Wazir Test Notification",
            "body": "This is a test push notification. The notification system is working correctly!",
            "icon": "/static/layout/assets/img/logo_non.png",
            "url": "/admin/dashboard"
        }
        
        # Send notification to all subscribers in background task
        background_tasks.add_task(send_push_notifications, notification_data)
        
        return {"success": True, "message": "Test notification sent"}
        
    except Exception as e:
        print(f"Error sending test notification: {e}")
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e)}
        )

# Background task for sending push notifications
async def send_push_notifications(notification_data: Dict[str, Any]):
    """Send push notifications to all subscribers."""
    if not VAPID_PRIVATE_KEY:
        print("VAPID keys not configured, cannot send notifications")
        return
    
    for subscription in subscriptions:
        try:
            subscription_info = subscription.get("subscription")
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(notification_data),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except Exception as e:
            print(f"Error sending notification: {e}")
            # Remove expired subscriptions
            if hasattr(e, 'response') and getattr(e, 'response', None) and getattr(e.response, 'status_code', 0) == 410:
                for idx, sub in enumerate(subscriptions):
                    if sub.get("id") == subscription.get("id"):
                        del subscriptions[idx]
                        break 