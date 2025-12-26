from bedrock_agentcore.memory import MemoryClient
from memory_hook import EchoInkMemoryHooks
from prompt import SYSTEM_PROMPT
from strands import Agent
from strands.models import BedrockModel
from echo_ink_orchestrator import (
    document_creator_agent,
    field_editor_agent,
    document_previewer_agent,
    document_finalizer_agent,
    session_manager_agent,
    initialize_session_storage,
)


class EchoInkAgent:
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

        # Initialize session storage with AgentCore Memory
        initialize_session_storage(memory_id, memory_client, actor_id)

        echo_ink_hooks = EchoInkMemoryHooks(
            memory_id=memory_id,
            client=memory_client,
            actor_id=actor_id,
            session_id=session_id,
        )

        # Sub-agents as tools
        sub_agent_tools = [
            document_creator_agent,
            field_editor_agent,
            document_previewer_agent,
            document_finalizer_agent,
            session_manager_agent,
        ]

        self.agent = Agent(
            name="Echo Ink Agent",
            description="An educational document creation agent that helps instructors create course materials",
            system_prompt=SYSTEM_PROMPT,
            model=bedrock_model,
            tools=sub_agent_tools,
            hooks=[echo_ink_hooks],
        )

    async def stream(self, query: str, session_id: str):
        response = str()
        try:
            async for event in self.agent.stream_async(query):
                if "data" in event:
                    # Only stream text chunks to the client
                    chunk = event["data"]
                    response += chunk
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": chunk,
                    }
                elif "complete" in event:
                    # Final completion event - don't send content, just signal done
                    yield {
                        "is_task_complete": True,
                        "require_user_input": False,
                        "content": "",
                    }
                    break

        except Exception as e:
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"We are unable to process your request at the moment. Error: {e}",
            }
        finally:
            # Only send completion if we haven't already
            if response:
                yield {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": "",
                }

    def invoke(self, query: str, session_id: str):
        try:
            response = str(self.agent(query))

        except Exception as e:
            raise f"Error invoking agent: {e}"
        return response
