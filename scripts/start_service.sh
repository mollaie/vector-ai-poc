#!/bin/bash
# Start the Vector AI Job Matching API service

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "🚀 Starting Vector AI service..."

# Check if port is already in use
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  Port 8000 is already in use"
    read -p "Kill existing process? (y/n): " KILL
    if [ "$KILL" = "y" ]; then
        ./scripts/stop_service.sh
    else
        echo "❌ Cannot start - port in use"
        exit 1
    fi
fi

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✓ Virtual environment activated"
fi

# Start the service
echo "✓ Starting API on http://localhost:8000"
echo "✓ Docs available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python -m src.api.main

