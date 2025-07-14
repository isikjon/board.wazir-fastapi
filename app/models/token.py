from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TokenPayload(BaseModel):
    """
    JWT token payload schema
    """
    sub: Optional[str] = None  # subject (user id as string)
    exp: Optional[datetime] = None  # expiration time
    iat: Optional[datetime] = None  # issued at
    jti: Optional[str] = None  # JWT ID 