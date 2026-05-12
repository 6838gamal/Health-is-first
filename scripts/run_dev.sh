#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Health is First - Development Startup Script
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

echo "🚀 Starting Health is First System..."

# Load env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create dirs
mkdir -p media/videos media/audio media/thumbnails media/broll logs

# Setup DB
echo "📦 Setting up database..."
python scripts/setup_db.py

# Start app
echo "🌐 Starting FastAPI server on port 5000..."
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 5000 \
    --reload \
    --log-level info
