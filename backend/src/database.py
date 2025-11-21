import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import OperationalError, DBAPIError

from dotenv import load_dotenv
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Load env vars
load_dotenv()

# --- DATABASE CONFIG ---
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is missing! Set it in Render environment variables.")

# --- CONVERT TO ASYNC FORMAT ---
# Supabase gives URLs like:
# postgresql://postgres:password@host:5432/postgres
DATABASE_URL = DATABASE_URL.replace(
    "postgres://", "postgresql+asyncpg://"
).replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Remove any existing sslmode query parameter (asyncpg doesn't support it in URL)
if "?sslmode" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?sslmode")[0]

logger.info(f"📌 Final DB URL for SQLAlchemy: {DATABASE_URL}")

# --- CREATE ENGINE ---
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={
        "ssl": "require"  # SSL configuration for asyncpg
    }
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


# --- DATABASE INIT CHECK ---
@retry(
    stop=stop_after_attempt(10),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type((OperationalError, DBAPIError, OSError)),
    reraise=True
)
async def init_db():
    logger.info("🔌 Trying to connect to Supabase database...")
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("⚡ DB Connection Successful!")
            
            # Create tables if they don't exist
            logger.info("📊 Checking/Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Tables created/verified!")
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise


async def close_db():
    await engine.dispose()
    logger.info("🔻 Database connections closed")
