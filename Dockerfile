# ============================
# Base Image
# ============================
FROM python:3.11-slim

# ============================
# Environment & PIP Fixes
# ============================
ENV PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

# ============================
# System dependencies
# Important for opencv, asyncpg, moviepy, ffmpeg
# ============================
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    git \
    build-essential \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# ============================
# Working Directory
# ============================
WORKDIR /app

# ============================
# Copy Requirements
# ============================
COPY backend/requirements.txt .

# Upgrade pip and fix importlib metadata dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install "importlib_metadata>=7.0,<8.0"

# Install deps
RUN pip install -r requirements.txt --verbose --timeout 200

# Force stable yt-dlp
RUN pip install --upgrade --force-reinstall yt-dlp

# ============================
# Copy Application Source
# ============================
COPY backend/src/ ./src/
COPY backend/fonts/ ./fonts/
COPY backend/transitions/ ./transitions/

# ============================
# Create directories used by your app
# ============================
RUN mkdir -p /app/uploads /app/clips /app/logs /tmp

# ============================
# Environment Variables (Injected at runtime)
# Do NOT hardcode credentials here
# ============================
ENV TEMP_DIR=/tmp/uploads

# ============================
# Expose Backend Port
# ============================
EXPOSE 8000

# ============================
# Start App (Render sets PORT)
# ============================
# Start App (Render sets PORT)
# Copy startup script
COPY start.sh .
RUN chmod +x start.sh

# Run both Worker and Backend
CMD ["./start.sh"]
