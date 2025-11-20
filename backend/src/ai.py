"""
AI-related functions for transcript analysis with enhanced precision.
"""

from pathlib import Path
from typing import List, Dict, Any
import asyncio
import logging
import re

from pydantic_ai import Agent
from pydantic import BaseModel, Field

from .config import Config

logger = logging.getLogger(__name__)
config = Config()

class TranscriptSegment(BaseModel):
    """Represents a relevant segment of transcript with precise timing."""
    start_time: str = Field(description="Start timestamp in MM:SS format")
    end_time: str = Field(description="End timestamp in MM:SS format")
    text: str = Field(description="The transcript text for this segment")
    relevance_score: float = Field(description="Relevance score from 0.0 to 1.0", ge=0.0, le=1.0)
    reasoning: str = Field(description="Explanation for why this segment is relevant")

class TranscriptAnalysis(BaseModel):
    """Analysis result for transcript segments."""
    most_relevant_segments: List[TranscriptSegment]
    summary: str = Field(description="Brief summary of the video content")
    key_topics: List[str] = Field(description="List of main topics discussed")

# Simplified system prompt that trusts AssemblyAI timing
simplified_system_prompt = """You are an expert at analyzing video transcripts to find the most engaging segments for short-form content creation.

CORE OBJECTIVES:
1. Identify segments that would be compelling on social media platforms
2. Focus on complete thoughts, insights, or entertaining moments
3. Prioritize content with hooks, emotional moments, or valuable information
4. Each segment should be engaging and worth watching

SEGMENT SELECTION CRITERIA:
1. STRONG HOOKS: Attention-grabbing opening lines
2. VALUABLE CONTENT: Tips, insights, interesting facts, stories
3. EMOTIONAL MOMENTS: Excitement, surprise, humor, inspiration
4. COMPLETE THOUGHTS: Self-contained ideas that make sense alone
5. ENTERTAINING: Content people would want to share

TIMING GUIDELINES:
- Segments MUST be between 10-45 seconds for optimal engagement
- CRITICAL: start_time MUST be different from end_time (minimum 10 seconds apart)
- Focus on natural content boundaries rather than arbitrary time limits
- Include enough context for the segment to be understandable

TIMESTAMP REQUIREMENTS - EXTREMELY IMPORTANT:
- Use EXACT timestamps as they appear in the transcript
- Never modify timestamp format (keep MM:SS structure)
- start_time MUST be LESS THAN end_time (start_time < end_time)
- MINIMUM segment duration: 10 seconds (end_time - start_time >= 10 seconds)
- Look at transcript ranges like [02:25 - 02:35] and use different start/end times
- NEVER use the same timestamp for both start_time and end_time
- Example: start_time: "02:25", end_time: "02:35" (NOT "02:25" and "02:25")

Find 3-7 compelling segments that would work well as standalone clips. Quality over quantity - choose segments that would genuinely engage viewers and have proper time ranges."""

# Create simplified agent
transcript_agent = Agent(
    model=config.llm,
    system_prompt=simplified_system_prompt,
    result_type=TranscriptAnalysis
)

async def get_most_relevant_parts_by_transcript(transcript: str) -> TranscriptAnalysis:
    """Get the most relevant parts of a transcript for creating clips - simplified version."""
    logger.info(f"Starting AI analysis of transcript ({len(transcript)} chars)")

    try:
        result = await transcript_agent.run(
            f"""Analyze this video transcript and identify the most engaging segments for short-form content.

Find segments that would be compelling as standalone clips for social media.

Transcript:
{transcript}"""
        )

        analysis = result.data
        logger.info(f"AI analysis found {len(analysis.most_relevant_segments)} segments")

        # Simple validation - just ensure segments have content
        validated_segments = []
        for segment in analysis.most_relevant_segments:
            # Validate text content
            if not segment.text.strip() or len(segment.text.split()) < 3:  # At least 3 words
                logger.warning(f"Skipping segment with insufficient content: '{segment.text[:50]}...'")
                continue

            # Validate timestamps - CRITICAL: start and end must be different
            if segment.start_time == segment.end_time:
                logger.warning(f"Skipping segment with identical start/end times: {segment.start_time}")
                continue

            # Parse timestamps to validate duration
            try:
                start_parts = segment.start_time.split(':')
                end_parts = segment.end_time.split(':')

                start_seconds = int(start_parts[0]) * 60 + int(start_parts[1])
                end_seconds = int(end_parts[0]) * 60 + int(end_parts[1])

                duration = end_seconds - start_seconds

                if duration <= 0:
                    logger.warning(f"Skipping segment with invalid duration: {segment.start_time} to {segment.end_time} = {duration}s")
                    continue

                if duration < 5:  # Minimum 5 seconds
                    logger.warning(f"Skipping segment too short: {duration}s (min 5s required)")
                    continue

                validated_segments.append(segment)
                logger.info(f"Validated segment: {segment.start_time}-{segment.end_time} ({duration}s)")

            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping segment with invalid timestamp format: {segment.start_time}-{segment.end_time}: {e}")
                continue

        # Sort by relevance
        validated_segments.sort(key=lambda x: x.relevance_score, reverse=True)

        final_analysis = TranscriptAnalysis(
            most_relevant_segments=validated_segments,
            summary=analysis.summary,
            key_topics=analysis.key_topics
        )

        logger.info(f"Selected {len(validated_segments)} segments for processing")
        if validated_segments:
            logger.info(f"Top segment score: {validated_segments[0].relevance_score:.2f}")

        return final_analysis

    except Exception as e:
        logger.error(f"Error in transcript analysis: {e}")
        return TranscriptAnalysis(
            most_relevant_segments=[],
            summary=f"Analysis failed: {str(e)}",
            key_topics=[]
        )

def get_most_relevant_parts_sync(transcript: str) -> TranscriptAnalysis:
    """Synchronous wrapper for the async function."""
    return asyncio.run(get_most_relevant_parts_by_transcript(transcript))
