#!/bin/bash
set -e

# Start the ARQ worker in the background
echo "🚀 Starting Background Worker..."
arq src.workers.tasks.WorkerSettings &

# Start the FastAPI backend in the foreground
echo "🚀 Starting Backend API..."
uvicorn src.main:app --host 0.0.0.0 --port $PORT
