#!/bin/bash
# Start FastAPI server

echo "Starting MT5 API server..."

# Wait for MT5 to be ready
while ! nc -z localhost 8001 2>/dev/null; do
    echo "Waiting for MT5 server to be ready..."
    sleep 5
done

echo "MT5 server is ready, starting API..."

# Start FastAPI with auto-reload in development
cd /app && python3 -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port ${API_PORT:-8000} \
    --log-level info