"""
Task service - orchestrates task creation and processing workflow.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, Callable
import logging

from ..repositories.task_repository import TaskRepository
from ..repositories.source_repository import SourceRepository
from ..repositories.clip_repository import ClipRepository
from .video_service import VideoService

logger = logging.getLogger(__name__)


class TaskService:
    """Service for task workflow orchestration."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_repo = TaskRepository()
        self.source_repo = SourceRepository()
        self.clip_repo = ClipRepository()
        self.video_service = VideoService()

    async def create_task_with_source(
        self,
        user_id: str,
        url: str,
        title: Optional[str] = None,
        font_family: str = "TikTokSans-Regular",
        font_size: int = 24,
        font_color: str = "#FFFFFF"
    ) -> str:
        """
        Create a new task with associated source.
        Returns the task ID.
        """
        # Validate user exists
        if not await self.task_repo.user_exists(self.db, user_id):
            raise ValueError(f"User {user_id} not found")

        # Determine source type
        source_type = self.video_service.determine_source_type(url)

        # Get or generate title
        if not title:
            if source_type == "youtube":
                title = await self.video_service.get_video_title(url)
            else:
                title = "Uploaded Video"

        # Create source
        source_id = await self.source_repo.create_source(
            self.db,
            source_type=source_type,
            title=title,
            url=url
        )

        # Create task
        task_id = await self.task_repo.create_task(
            self.db,
            user_id=user_id,
            source_id=source_id,
            status="queued",  # Changed from "processing" to "queued"
            font_family=font_family,
            font_size=font_size,
            font_color=font_color
        )

        logger.info(f"Created task {task_id} for user {user_id}")
        return task_id

    async def process_task(
        self,
        task_id: str,
        url: str,
        source_type: str,
        font_family: str = "TikTokSans-Regular",
        font_size: int = 24,
        font_color: str = "#FFFFFF",
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Process a task: download video, analyze, create clips.
        Returns processing results.
        """
        try:
            logger.info(f"Starting processing for task {task_id}")

            # Update status to processing
            await self.task_repo.update_task_status(
                self.db, task_id, "processing", progress=0, progress_message="Starting..."
            )

            # Progress callback wrapper
            async def update_progress(progress: int, message: str):
                await self.task_repo.update_task_status(
                    self.db, task_id, "processing", progress=progress, progress_message=message
                )
                if progress_callback:
                    await progress_callback(progress, message)

            # Process video with progress updates
            result = await self.video_service.process_video_complete(
                url=url,
                source_type=source_type,
                font_family=font_family,
                font_size=font_size,
                font_color=font_color,
                progress_callback=update_progress
            )

            # Save clips to database
            await self.task_repo.update_task_status(
                self.db, task_id, "processing", progress=95, progress_message="Saving clips..."
            )

            clip_ids = []
            for i, clip_info in enumerate(result["clips"]):
                clip_id = await self.clip_repo.create_clip(
                    self.db,
                    task_id=task_id,
                    filename=clip_info["filename"],
                    file_path=clip_info["path"],
                    start_time=clip_info["start_time"],
                    end_time=clip_info["end_time"],
                    duration=clip_info["duration"],
                    clip_text=clip_info["text"],
                    relevance_score=clip_info["relevance_score"],
                    reasoning=clip_info["reasoning"],
                    clip_order=i + 1
                )
                clip_ids.append(clip_id)

            # Update task with clip IDs
            await self.task_repo.update_task_clips(self.db, task_id, clip_ids)

            # Mark as completed
            await self.task_repo.update_task_status(
                self.db, task_id, "completed", progress=100, progress_message="Complete!"
            )

            logger.info(f"Task {task_id} completed successfully with {len(clip_ids)} clips")

            return {
                "task_id": task_id,
                "clips_count": len(clip_ids),
                "segments": result["segments"],
                "summary": result.get("summary"),
                "key_topics": result.get("key_topics")
            }

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            await self.task_repo.update_task_status(
                self.db, task_id, "error", progress_message=str(e)
            )
            raise

    async def get_task_with_clips(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details with all clips."""
        task = await self.task_repo.get_task_by_id(self.db, task_id)

        if not task:
            return None

        # Get clips
        clips = await self.clip_repo.get_clips_by_task(self.db, task_id)
        task["clips"] = clips
        task["clips_count"] = len(clips)

        return task

    async def get_user_tasks(self, user_id: str, limit: int = 50) -> list[Dict[str, Any]]:
        """Get all tasks for a user."""
        return await self.task_repo.get_user_tasks(self.db, user_id, limit)

    async def delete_task(self, task_id: str) -> None:
        """Delete a task and all its associated clips."""
        # Delete all clips for this task
        await self.clip_repo.delete_clips_by_task(self.db, task_id)

        # Delete the task
        await self.task_repo.delete_task(self.db, task_id)

        logger.info(f"Deleted task {task_id} and all associated clips")
