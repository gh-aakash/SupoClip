# Use Python 3.11 slim image
FROM python:3.11-slim

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

# Install dependencies using pip
RUN pip install --no-cache-dir -r requirements.txt

# Force update yt-dlp to the absolute latest version to handle YouTube API changes
RUN pip install --no-cache-dir --upgrade --force-reinstall yt-dlp
RUN pip install --no-cache-dir --upgrade --force-reinstall "yt-dlp[default]"

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
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
