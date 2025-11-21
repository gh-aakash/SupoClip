"""
Input validation utilities for security.
"""
from urllib.parse import urlparse
from fastapi import HTTPException


def validate_youtube_url(url: str) -> bool:
    """
    Validate that URL is from YouTube to prevent SSRF attacks.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid YouTube URL
        
    Raises:
        HTTPException: If URL is not from YouTube
    """
    try:
        parsed = urlparse(url)
        allowed_domains = [
            'youtube.com',
            'www.youtube.com',
            'youtu.be',
            'm.youtube.com'
        ]
        
        if parsed.netloc not in allowed_domains:
            raise HTTPException(
                status_code=400,
                detail=f"Only YouTube URLs are allowed. Got domain: {parsed.netloc}"
            )
        
        return True
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid URL format: {str(e)}"
        )


def validate_task_input(data: dict) -> dict:
    """
    Validate task creation input.
    
    Args:
        data: Request data
        
    Returns:
        Validated data
        
    Raises:
        HTTPException: If validation fails
    """
    raw_source = data.get("source")
    
    if not raw_source or not raw_source.get("url"):
        raise HTTPException(status_code=400, detail="Source URL is required")
    
    # Validate YouTube URL
    validate_youtube_url(raw_source["url"])
    
    # Validate font options
    font_options = data.get("font_options", {})
    font_size = font_options.get("font_size", 24)
    
    if not isinstance(font_size, int) or font_size < 10 or font_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Font size must be between 10 and 100"
        )
    
    return data
