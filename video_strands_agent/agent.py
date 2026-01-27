"""
Video Strands Agent — Educational video analytics agent.
Runs on AgentCore with Memory, Observability, and Gateway integration.
"""
import logging
from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models import BedrockModel
from prompt import SYSTEM_PROMPT
from video_tools import (
    fetch_metadata,
    fetch_transcript,
    fetch_engagement,
    fetch_polls,
    compute_video_insights,
)

logger = logging.getLogger(__name__)


class VideoAgent:
    """Video analytics agent for educational video content."""

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(
        self,
        memory_id: str,
        model_id: str,
        region_name: str,
        actor_id: str,
        session_id: str,
    ):
        bedrock_model = BedrockModel(model_id=model_id, region_name=region_name)
        memory_client = MemoryClient(region_name=region_name)

        video_tools = [
            fetch_metadata,
            fetch_transcript,
            fetch_engagement,
            fetch_polls,
            compute_video_insights,
        ]

        self.agent = Agent(
            name="Video Agent",
            description="Educational video analytics agent for metadata, transcripts, engagement, and insights",
            system_prompt=SYSTEM_PROMPT,
            model=bedrock_model,
            tools=video_tools,
        )

        logger.info("Video Agent initialized successfully")

    async def stream(self, query: str, session_id: str):
        """Stream agent responses."""
        response = str()
        try:
            async for event in self.agent.stream_async(query):
                if "data" in event:
                    chunk = event["data"]
                    response += chunk
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": chunk,
                    }
                elif "complete" in event:
                    yield {
                        "is_task_complete": True,
                        "require_user_input": False,
                        "content": "",
                    }
                    break
        except Exception as e:
            logger.error(f"Error during agent streaming: {e}", exc_info=True)
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"Error processing request: {e}",
            }
        finally:
            if response:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": "",
                }

    def invoke(self, query: str, session_id: str):
        """Invoke agent synchronously."""
        try:
            return str(self.agent(query))
        except Exception as e:
            logger.error(f"Error invoking agent: {e}", exc_info=True)
            raise Exception(f"Error invoking agent: {e}")
