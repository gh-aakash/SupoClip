"""
Job queue setup using arq (async Redis queue).
"""
import logging
from typing import Optional
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from redis.exceptions import ConnectionError, TimeoutError
from src.config import Config

logger = logging.getLogger(__name__)
config = Config()

# Use URL directly from config
ARQ_REDIS_SETTINGS = RedisSettings.from_dsn(config.redis_url)


class JobQueue:
    """Handles pushing, inspecting, and retrieving jobs."""

    _pool: Optional[ArqRedis] = None

    @classmethod
    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def get_pool(cls) -> ArqRedis:
        if cls._pool:
            return cls._pool

        logger.info(f"🔌 Connecting to Redis: {config.redis_url}")
        cls._pool = await create_pool(ARQ_REDIS_SETTINGS)
        return cls._pool

    @classmethod
    async def enqueue(cls, task_name: str, **kwargs) -> str:
        """Enqueue a task to Redis using arq."""
        pool = await cls.get_pool()
        job = await pool.enqueue_job(task_name, **kwargs)
        if job:
            logger.info(f"🚀 Enqueued task {task_name} with ID: {job.job_id}")
            return str(job.job_id)
        return ""

    @classmethod
    async def get_job(cls, job_id: str):
        pool = await cls.get_pool()
        job = await pool.job(job_id)
        return job

    @classmethod
    async def get_job_result(cls, job_id: str):
        pool = await cls.get_pool()
        job = await pool.job(job_id)
        if job:
            return await job.result()
        return None

    @classmethod
    async def get_job_status(cls, job_id: str) -> Optional[str]:
        pool = await cls.get_pool()
        job = await pool.job(job_id)
        if job:
            return await job.status()
        return None
