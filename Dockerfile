# Use Python 3.11 slim image
FROM python:3.11-slim

# --- ENVIRONMENT FIXES ---
ENV PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies including ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file from backend
COPY backend/requirements.txt .

# -- IMPORTANT: Constrain importlib_metadata to avoid dependency resolution hang --
# You do NOT need to modify your requirements file,
# this keeps the fix inside Docker only.
RUN pip install --upgrade pip setuptools wheel
RUN pip install "importlib_metadata>=7.0,<8.0"

# Install dependencies with verbose output
RUN pip install -r requirements.txt --verbose --timeout 200

# Install yt-dlp exactly once (forces known working version)
RUN pip install --upgrade --force-reinstall yt-dlp

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
CMD sh -c "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"
