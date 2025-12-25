#!/bin/bash

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting FastAPI application..."

log "Waiting for database connection..."
DB_HOST="${DB_HOST:-host.docker.internal}"
DB_PORT="${DB_PORT:-3306}"

counter=0
max_attempts=30
while ! nc -z ${DB_HOST} ${DB_PORT} 2>/dev/null; do
    counter=$((counter+1))
    if [ $counter -ge $max_attempts ]; then
        log "Database connection timeout after $max_attempts attempts"
        log "Trying to continue anyway..."
        break
    fi
    log "Database is unavailable - sleeping (attempt $counter/$max_attempts)"
    sleep 2
done

if nc -z ${DB_HOST} ${DB_PORT} 2>/dev/null; then
    log "Database is up - continuing"
else
    log "Warning: Could not verify database connection, but continuing..."
fi

mkdir -p media/panoramas
mkdir -p media/uploads
log "Created media directories"

log "Starting uvicorn server..."
exec "$@" 