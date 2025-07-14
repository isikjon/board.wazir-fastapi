#!/bin/bash

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting FastAPI application..."

log "Waiting for database connection..."
while ! nc -z ${DB_HOST:-91.218.141.27} ${DB_PORT:-3306}; do
    log "Database is unavailable - sleeping"
    sleep 1
done
log "Database is up - continuing"

mkdir -p media/panoramas
mkdir -p media/uploads
log "Created media directories"

log "Starting uvicorn server..."
exec "$@" 