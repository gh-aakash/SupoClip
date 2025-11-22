"""
Task repository - handles all database operations for tasks.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TaskRepository:
    """Repository for task-related database operations."""

    @staticmethod
    async def create_task(
        db: AsyncSession,
        user_id: str,
        source_id: str,
        status: str = "processing",
        font_family: str = "TikTokSans-Regular",
        font_size: int = 24,
        font_color: str = "#FFFFFF"
    ) -> str:
        """Create a new task and return its ID."""
        import uuid
        task_id = str(uuid.uuid4())
        
        result = await db.execute(
            text("""
                INSERT INTO tasks (id, user_id, source_id, status, font_family, font_size, font_color, created_at, updated_at)
                VALUES (:id, :user_id, :source_id, :status, :font_family, :font_size, :font_color, NOW(), NOW())
                RETURNING id
            """),
            {
                "id": task_id,
                "user_id": user_id,
                "source_id": str(source_id),  # Convert UUID to string
                "status": status,
                "font_family": font_family,
                "font_size": font_size,
                "font_color": font_color
            }
        )
        await db.commit()
        # task_id is already known, but we can get it from result to be sure it was inserted
        inserted_id = result.scalar()
        logger.info(f"Created task {inserted_id} for user {user_id}")
        return inserted_id

    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID with source information."""
        result = await db.execute(
            text("""
                SELECT t.*, s.title as source_title, s.type as source_type
                FROM tasks t
                LEFT JOIN sources s ON t.source_id = s.id
                WHERE t.id = :task_id
            """),
            {"task_id": task_id}
        )
        row = result.fetchone()

        if not row:
            return None

        return {
            "id": row.id,
            "user_id": row.user_id,
            "source_id": row.source_id,
            "source_title": row.source_title,
            "source_type": row.source_type,
            "status": row.status,
            "progress": getattr(row, 'progress', None),
            "progress_message": getattr(row, 'progress_message', None),
            "generated_clips_ids": row.generated_clips_ids,
            "font_family": row.font_family,
            "font_size": row.font_size,
            "font_color": row.font_color,
            "created_at": row.created_at,
            "updated_at": row.updated_at
        }

    @staticmethod
    async def update_task_status(
        db: AsyncSession,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        progress_message: Optional[str] = None
    ) -> None:
        """Update task status and optional progress."""
        params = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "progress_message": progress_message
        }

        # Build dynamic query based on what's provided
        set_clauses = ["status = :status"]

        if progress is not None:
            set_clauses.append("progress = :progress")

        if progress_message is not None:
            set_clauses.append("progress_message = :progress_message")

        set_clauses.append("updated_at = NOW()")

        query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = :task_id"

        await db.execute(text(query), params)
        await db.commit()
        logger.info(f"Updated task {task_id} status to {status}" +
                   (f" (progress: {progress}%)" if progress else ""))

    @staticmethod
    async def update_task_clips(db: AsyncSession, task_id: str, clip_ids: List[str]) -> None:
        """Update task with generated clip IDs."""
        await db.execute(
            text("UPDATE tasks SET generated_clips_ids = :clip_ids, updated_at = NOW() WHERE id = :task_id"),
            {"clip_ids": clip_ids, "task_id": task_id}
        )
        await db.commit()
        logger.info(f"Updated task {task_id} with {len(clip_ids)} clips")

    @staticmethod
    async def get_user_tasks(db: AsyncSession, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all tasks for a user."""
        result = await db.execute(
            text("""
                SELECT t.*, s.title as source_title, s.type as source_type,
                       (SELECT COUNT(*) FROM generated_clips WHERE task_id = t.id) as clips_count
                FROM tasks t
                LEFT JOIN sources s ON t.source_id = s.id
                WHERE t.user_id = :user_id
                ORDER BY t.created_at DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit}
        )

        tasks = []
        for row in result.fetchall():
            tasks.append({
                "id": row.id,
                "user_id": row.user_id,
                "source_id": row.source_id,
                "source_title": row.source_title,
                "source_type": row.source_type,
                "status": row.status,
                "clips_count": row.clips_count,
                "created_at": row.created_at,
                "updated_at": row.updated_at
            })

        return tasks

    @staticmethod
    async def user_exists(db: AsyncSession, user_id: str) -> bool:
        """Check if a user exists in the database."""
        result = await db.execute(
            text("SELECT 1 FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        return result.fetchone() is not None

    @staticmethod
    async def delete_task(db: AsyncSession, task_id: str) -> None:
        """Delete a task by ID."""
        await db.execute(
            text("DELETE FROM tasks WHERE id = :task_id"),
            {"task_id": task_id}
        )
        await db.commit()
        logger.info(f"Deleted task {task_id}")
