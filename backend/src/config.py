from dotenv import load_dotenv
import os
from urllib.parse import urlparse

load_dotenv()

class Config:
    def __init__(self):
        self.whisper_model = os.getenv("WHISPER_MODEL", "base")
        self.llm = os.getenv("LLM_MODEL", "google-gla:gemini-2.5-flash-lite")

        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.assembly_ai_api_key = os.getenv("ASSEMBLY_AI_API_KEY")

        # Paths
        self.max_video_duration = int(os.getenv("MAX_VIDEO_DURATION", "3600"))
        self.output_dir = os.getenv("OUTPUT_DIR", "outputs")
        self.temp_dir = os.getenv("TEMP_DIR", "/tmp/uploads")

        # ─── DATABASE ───────────────────────────────────────────

        # Full Supabase URL (async pg)
        self.database_url = os.getenv("DATABASE_URL")

        # ─── REDIS ──────────────────────────────────────────────

        redis_url = os.getenv("REDIS_URL")
        self.redis_url = redis_url

        if redis_url:
            parsed = urlparse(redis_url)
            self.redis_host = parsed.hostname
            self.redis_port = parsed.port
            self.redis_password = parsed.password
        else:
            # fallback to manual config
            self.redis_host = os.getenv("REDIS_HOST", "localhost")
            self.redis_port = int(os.getenv("REDIS_PORT", "6379"))
            self.redis_password = os.getenv("REDIS_PASSWORD")
            
            # Construct URL for consistency
            auth = f":{self.redis_password}@" if self.redis_password else ""
            self.redis_url = f"redis://{auth}{self.redis_host}:{self.redis_port}"
