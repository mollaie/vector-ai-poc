#!/bin/bash
# Stop the Vector AI Job Matching API service

echo "🛑 Stopping Vector AI service..."

# Kill by process name
pkill -f "python -m src.api.main" 2>/dev/null

# Kill by port (backup method)
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Verify
sleep 1
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "❌ Failed to stop service - port 8000 still in use"
    exit 1
else
    echo "✅ Service stopped"
fi

