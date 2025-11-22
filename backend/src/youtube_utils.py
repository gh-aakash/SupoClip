"""
Utility functions for YouTube-related operations.
Optimized for high-quality downloads and better error handling.
"""

import re
from urllib.parse import urlparse, parse_qs
import yt_dlp
from typing import Optional, Dict, Any
from pathlib import Path
import logging
import time

from .config import Config

logger = logging.getLogger(__name__)
config = Config()

class YouTubeDownloader:
    """Enhanced YouTube downloader with optimized settings."""

    def __init__(self):
        self.temp_dir = Path(config.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_optimal_download_options(self, video_id: str) -> Dict[str, Any]:
        """Get optimal yt-dlp options for high-quality downloads with enhanced YouTube bypass."""
        output_path = self.temp_dir / f"{video_id}.%(ext)s"

        # Handle cookies for authentication (bypass bot detection)
        cookie_file = None
        
        # 1. Check environment variable (for Render)
        import os
        import tempfile
        
        env_cookies = os.getenv("YOUTUBE_COOKIES")
        if env_cookies:
            # Write env var content to a temp file
            try:
                # Create a temp file for cookies
                fd, path = tempfile.mkstemp(suffix='.txt', text=True)
                with os.fdopen(fd, 'w') as f:
                    f.write(env_cookies)
                cookie_file = path
                logger.info("🍪 Using cookies from environment variable")
            except Exception as e:
                logger.error(f"❌ Failed to process cookies from env: {e}")
        
        # 2. Check local file (fallback/local dev)
        if not cookie_file:
            local_cookies = Path("cookies.txt")
            if local_cookies.exists():
                cookie_file = str(local_cookies)
                logger.info("🍪 Using local cookies.txt file")

        opts = {
            'outtmpl': str(output_path),
            # More permissive format selection to avoid "format not available" errors
            'format': 'bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b',
            'merge_output_format': 'mp4',
            'writesubtitles': False,
            'writeautomaticsub': False,
            # Optimized for speed and reliability
            'socket_timeout': 30,
            'retries': 5,  # Increased retries
            'fragment_retries': 5,
            'http_chunk_size': 10485760,  # 10MB chunks
            # Quiet operation - only errors/warnings
            'quiet': True,
            'no_warnings': False,  # Show warnings but not info
            'ignoreerrors': False,
            # Enhanced headers to avoid 403 errors
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            },
            # Simplified YouTube bypass - use android client for better reliability
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
            # Post-processing options
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            # Metadata extraction
            'extract_flat': False,
            'writeinfojson': False,
            # Additional bypass options
            'nocheckcertificate': True,
            'prefer_insecure': False,
            'age_limit': None,
        }

        if cookie_file:
            opts['cookiefile'] = cookie_file
            
        return opts

def get_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.
    Supports standard, short, embed, and mobile URLs.
    """
    if not isinstance(url, str) or not url.strip():
        return None

    url = url.strip()

    # Comprehensive regex patterns for different YouTube URL formats
    patterns = [
        r"(?:youtube\.com/(?:.*v=|v/|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})",
        r"youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})",
        r"youtube\.com/v/([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/shorts/([A-Za-z0-9_-]{11})",
        r"m\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            video_id = match.group(1)
            # Validate video ID length (YouTube IDs are always 11 characters)
            if len(video_id) == 11:
                return video_id

    # Fallback: parse query parameters
    try:
        parsed_url = urlparse(url)
        if 'youtube.com' in parsed_url.netloc.lower():
            query = parse_qs(parsed_url.query)
            video_ids = query.get("v")
            if video_ids and len(video_ids[0]) == 11:
                return video_ids[0]
    except Exception as e:
        logger.warning(f"Error parsing URL query parameters: {e}")

    return None

def validate_youtube_url(url: str) -> bool:
    """Validate if URL is a proper YouTube URL."""
    video_id = get_youtube_video_id(url)
    return video_id is not None

def get_youtube_video_info(url: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive video information without downloading.
    Returns title, duration, description, and other metadata.
    """
    video_id = get_youtube_video_id(url)
    if not video_id:
        logger.error(f"Invalid YouTube URL: {url}")
        return None

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extractaudio': False,
            'skip_download': True,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
            },
            # Simplified extractor args for better compatibility
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                }
            },
            'nocheckcertificate': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'description': info.get('description', ''),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'upload_date': info.get('upload_date'),
                'view_count': info.get('view_count'),
                'like_count': info.get('like_count'),
                'thumbnail': info.get('thumbnail'),
                'format_id': info.get('format_id'),
                'resolution': info.get('resolution'),
                'fps': info.get('fps'),
                'filesize': info.get('filesize'),
            }

    except Exception as e:
        logger.error(f"Error extracting video info: {e}")
        return None

def get_youtube_video_title(url: str) -> Optional[str]:
    """
    Get the title of a YouTube video from a URL.
    Enhanced with better error handling and validation.
    """
    video_info = get_youtube_video_info(url)
    return video_info.get('title') if video_info else None

def download_youtube_video(url: str, max_retries: int = 3) -> Optional[Path]:
    """
    Download YouTube video with optimized settings and retry logic.
    Returns the path to the downloaded file, or None if download fails.
    """
    logger.info(f"Starting YouTube download: {url}")

    video_id = get_youtube_video_id(url)
    if not video_id:
        logger.error(f"Could not extract video ID from URL: {url}")
        return None

    downloader = YouTubeDownloader()

    # Get video info first to validate and get metadata
    video_info = get_youtube_video_info(url)
    if not video_info:
        logger.error(f"Could not retrieve video information for: {url}")
        return None

    logger.info(f"Video: '{video_info.get('title')}' ({video_info.get('duration')}s)")

    # Check if video is too long (optional safeguard)
    duration = video_info.get('duration', 0)
    if duration > 3600:  # 1 hour limit
        logger.warning(f"Video duration ({duration}s) exceeds recommended limit")

    # Retry download with exponential backoff
    for attempt in range(max_retries):
        try:
            logger.info(f"Download attempt {attempt + 1}/{max_retries}")

            ydl_opts = downloader.get_optimal_download_options(video_id)

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video
                ydl.download([url])

                # Find the downloaded file
                logger.info(f"Searching for downloaded file: {video_id}.*")
                for file_path in downloader.temp_dir.glob(f"{video_id}.*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.mkv', '.webm']:
                        file_size = file_path.stat().st_size
                        logger.info(f"Download successful: {file_path.name} ({file_size // 1024 // 1024}MB)")
                        return file_path

                logger.warning(f"No video file found after download attempt {attempt + 1}")

        except yt_dlp.utils.DownloadError as e:
            logger.warning(f"Download attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1, 2, 4 seconds
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All download attempts failed for: {url}")

        except Exception as e:
            logger.error(f"Unexpected error during download attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"All download attempts failed for: {url}")

    return None

def get_video_duration(url: str) -> Optional[int]:
    """Get video duration in seconds without downloading."""
    video_info = get_youtube_video_info(url)
    return video_info.get('duration') if video_info else None

def is_video_suitable_for_processing(url: str, min_duration: int = 60, max_duration: int = 7200) -> bool:
    """
    Check if video is suitable for processing based on duration and other factors.
    Default limits: 1 minute to 2 hours.
    """
    video_info = get_youtube_video_info(url)
    if not video_info:
        return False

    duration = video_info.get('duration', 0)

    # Check duration constraints
    if duration < min_duration or duration > max_duration:
        logger.warning(f"Video duration {duration}s outside allowed range ({min_duration}-{max_duration}s)")
        return False

    # Additional checks could go here (e.g., content type, quality, etc.)

    return True

def cleanup_downloaded_files(video_id: str):
    """Clean up downloaded files for a specific video ID."""
    temp_dir = Path(config.temp_dir)

    for file_path in temp_dir.glob(f"{video_id}.*"):
        try:
            if file_path.is_file():
                file_path.unlink()
                logger.info(f"Cleaned up: {file_path.name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {file_path.name}: {e}")

# Backward compatibility functions
def extract_video_id(url: str) -> Optional[str]:
    """Backward compatibility wrapper."""
    return get_youtube_video_id(url)
