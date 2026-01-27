"""
Agent executor for the Video Agent — handles A2A protocol integration.
"""
import os
import logging
from agent import VideoAgent

logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")
MEMORY_ID = os.getenv("MEMORY_ID")
MCP_REGION = os.getenv("MCP_REGION")


class VideoAgentExecutor:
    """Executor that bridges A2A protocol with the Video Agent."""

    def __init__(self):
        self.agent = None

    def _get_or_create_agent(self, memory_id: str, model_id: str, region: str, actor_id: str, session_id: str):
        if self.agent is None:
            self.agent = VideoAgent(
                memory_id=memory_id,
                model_id=model_id,
                region_name=region,
                actor_id=actor_id,
                session_id=session_id,
            )
        return self.agent

    async def execute(self, query: str, session_id: str, actor_id: str):
        """Execute a query against the video agent."""
        agent = self._get_or_create_agent(
            memory_id=MEMORY_ID,
            model_id=BEDROCK_MODEL_ID,
            region=MCP_REGION,
            actor_id=actor_id,
            session_id=session_id,
        )
        async for event in agent.stream(query, session_id):
            yield event
