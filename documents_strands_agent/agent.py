"""
Documents Strands Agent — Educational document management, context retrieval, and analytics.
Runs on AgentCore with Memory, Observability, and Knowledge Base integration.
"""
import logging
from bedrock_agentcore.memory import MemoryClient
from strands import Agent
from strands.models import BedrockModel
from prompt import SYSTEM_PROMPT
from document_context_tools import search_documents, get_document, list_documents
from analytics_tools import log_document_access, get_document_analytics, get_course_analytics
from session_tools import get_session_context, update_session_context

logger = logging.getLogger(__name__)


class DocumentsAgent:
    """Documents agent for educational document management and analytics."""

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

        all_tools = [
            # Document Context
            search_documents,
            get_document,
            list_documents,
            # Analytics
            log_document_access,
            get_document_analytics,
            get_course_analytics,
            # Session
            get_session_context,
            update_session_context,
        ]

        self.agent = Agent(
            name="Documents Agent",
            description="Educational document management agent with context retrieval, analytics, and session management",
            system_prompt=SYSTEM_PROMPT,
            model=bedrock_model,
            tools=all_tools,
        )

        logger.info("Documents Agent initialized successfully")

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
