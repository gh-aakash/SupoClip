# Use Python 3.11 slim image
FROM python:3.11-slim

# --- FIXES START ---
# Set environment variables to prevent network hangs
# PYTHONUNBUFFERED: Ensures logs stream immediately
# PIP_DEFAULT_TIMEOUT: Increases timeout to 100s (prevents metadata download hangs)
ENV PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file from backend
COPY backend/requirements.txt .

# 1. CRITICAL FIX: Upgrade pip first
# Old pip versions struggle with the new metadata resolution logic causing the hang
RUN pip install --upgrade pip

# 2. CRITICAL FIX: Install with verbose output (-v)
# This prevents the "silent hang" by keeping the output stream active
RUN pip install -r requirements.txt -v

# Force update yt-dlp to the absolute latest version
RUN pip install --upgrade --force-reinstall yt-dlp -v
RUN pip install --upgrade --force-reinstall "yt-dlp[default]" -v

# Copy source code from backend
COPY backend/src/ ./src/

# Copy fonts and transitions directories from backend
COPY backend/fonts/ ./fonts/
COPY backend/transitions/ ./transitions/

# Create necessary directories for video processing
RUN mkdir -p /app/uploads /app/clips /app/logs /tmp

# Expose the port FastAPI will run on
EXPOSE 8000

# Start the application
# Use PORT environment variable from Railway, default to 8000
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"
