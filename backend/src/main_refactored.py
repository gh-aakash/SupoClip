"""
Refactored FastAPI application with proper layered architecture.

This is the new main entry point with:
- Separated concerns (routes, services, repositories, workers)
- Async job queue with arq
- Real-time progress updates via SSE
- Thread pool for blocking operations
"""
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Config
from .database import init_db, close_db, get_db
from .workers.job_queue import JobQueue
from .api.routes import tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/backend.log')
    ]
)

logger = logging.getLogger(__name__)
config = Config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    # Startup
    logger.info("🚀 Starting SupoClip API...")
    
    db_initialized = False
    queue_initialized = False
    
    try:
        # Try to initialize database with retry logic
        try:
            await init_db()
            logger.info("✅ Database initialized")
            db_initialized = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize database after retries: {e}")
            logger.warning("⚠️  Application starting without database connection")

        # Try to initialize job queue with retry logic
        try:
            await JobQueue.get_pool()
            logger.info("✅ Job queue initialized")
            queue_initialized = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize job queue after retries: {e}")
            logger.warning("⚠️  Application starting without job queue connection")

        if not db_initialized or not queue_initialized:
            logger.warning("⚠️  Application started with degraded functionality")
            logger.info("💡 Services will retry connections on first use")
        else:
            logger.info("✅ All services initialized successfully")

        yield

    finally:
        # Shutdown
        logger.info("🛑 Shutting down SupoClip API...")
        if db_initialized:
            await close_db()
        if queue_initialized:
            await JobQueue.close_pool()
        logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="SupoClip API",
    description="Refactored Python backend for SupoClip with async job processing",
    version="0.2.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving clips
clips_dir = Path(config.temp_dir) / "clips"
clips_dir.mkdir(parents=True, exist_ok=True)
app.mount("/clips", StaticFiles(directory=str(clips_dir)), name="clips")

# Include routers
app.include_router(tasks.router)

# Keep existing utility endpoints
from .api.routes.media import router as media_router
app.include_router(media_router)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "name": "SupoClip API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
        "architecture": "refactored with job queue"
    }


@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy"}


@app.get("/health/db")
async def check_database_health(db: AsyncSession = Depends(get_db)):
    """Check database connectivity."""
    from sqlalchemy import text
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.get("/health/redis")
async def check_redis_health():
    """Check Redis connectivity."""
    try:
        pool = await JobQueue.get_pool()
        await pool.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}
