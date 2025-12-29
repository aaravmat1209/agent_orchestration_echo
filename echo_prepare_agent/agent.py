import os
import logging
from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models import BedrockModel
from prompt import SYSTEM_PROMPT
from memory_tool import create_memory_tools
from tools import get_prepare_tools
import document_retrieval

logger = logging.getLogger(__name__)

# Environment configuration
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")
MEMORY_ID = os.getenv("MEMORY_ID")
MCP_REGION = os.getenv("MCP_REGION")

if not MEMORY_ID:
    raise RuntimeError("Missing MEMORY_ID environment variable")
if not MCP_REGION:
    raise RuntimeError("Missing MCP_REGION environment variable")


class EchoPrepareAgent:
    """
    Echo Prepare Agent - Student study and exam preparation assistant
    Uses Strands framework with Claude model
    """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self, session_id: str, actor_id: str):
        self.session_id = session_id
        self.actor_id = actor_id

        # Initialize Bedrock Claude model
        bedrock_model = BedrockModel(
            model_id=BEDROCK_MODEL_ID,
            region_name=MCP_REGION
        )

        # Initialize memory client
        memory_client = MemoryClient(region_name=MCP_REGION)

        # Initialize S3 document retrieval with session ID
        document_retrieval.set_session_id(session_id)

        # Get memory tools
        memory_tools = create_memory_tools(
            memory_id=MEMORY_ID,
            client=memory_client,
            actor_id=actor_id,
            session_id=session_id,
        )

        # Get study tools (web search + confidence tracking)
        study_tools = get_prepare_tools(
            memory_id=MEMORY_ID,
            memory_client=memory_client,
            actor_id=actor_id,
            session_id=session_id,
        )

        # Get document retrieval tools (read-only access to instructor materials)
        retrieval_tools = document_retrieval.get_document_retrieval_tools()

        # Combine all tools
        all_tools = study_tools + memory_tools + retrieval_tools

        logger.info(f"Initializing Echo Prepare Agent with {len(all_tools)} tools (including {len(retrieval_tools)} document retrieval tools)")

        # Create Strands agent
        self.agent = Agent(
            name="Echo Prepare Agent",
            description="Student study and exam preparation assistant that helps with research, practice questions, and study planning",
            system_prompt=SYSTEM_PROMPT,
            model=bedrock_model,
            tools=all_tools,
        )

        logger.info("Echo Prepare Agent initialized successfully")

    async def stream(self, query: str, session_id: str):
        """Stream agent responses"""
        response = str()
        try:
            async for event in self.agent.stream_async(query):
                if "data" in event:
                    # Stream text chunks to the client
                    chunk = event["data"]
                    response += chunk
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": chunk,
                    }
                elif "complete" in event:
                    # Final completion event
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
            # Send completion if we have content
            if response:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": "",
                }

    def invoke(self, query: str, session_id: str):
        """Invoke agent synchronously"""
        try:
            return str(self.agent(query))
        except Exception as e:
            logger.error(f"Error invoking agent: {e}", exc_info=True)
            raise Exception(f"Error invoking agent: {e}")


def create_agent(session_id: str, actor_id: str):
    """Factory function to create Echo Prepare Agent"""
    return EchoPrepareAgent(session_id=session_id, actor_id=actor_id)
