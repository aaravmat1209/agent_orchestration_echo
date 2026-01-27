"""
Main entry point for the Video Agent — A2A server on AgentCore.
"""
import os
import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IS_DOCKER = os.getenv("DOCKER_CONTAINER", "0") == "1"

if IS_DOCKER:
    from agent_executor import VideoAgentExecutor
else:
    from video_strands_agent.agent_executor import VideoAgentExecutor

executor = VideoAgentExecutor()
app = BedrockAgentCoreApp()


@app.agent_card(
    name="Video Agent",
    description="Educational video analytics agent — metadata, transcripts, engagement, polls, and insights",
    version="1.0",
)
def agent_card():
    pass


@app.action()
async def on_message(request):
    query = request.get("query", "")
    session_id = request.get("session_id", "")
    actor_id = request.get("actor_id", "")

    async for event in executor.execute(query, session_id, actor_id):
        yield event


if __name__ == "__main__":
    app.run()
