from bedrock_agentcore.memory import MemoryClient
from memory_hook import EchoInkMemoryHooks
from prompt import SYSTEM_PROMPT
from strands import Agent
from strands.models import BedrockModel
from strands_tools import file_read, file_write, editor
import logging

# Import custom document tools
from document_tools import (
    create_educational_document,
    convert_document_to_pdf,
    get_document_template_info,
    search_documents,
    index_documents,
    validate_document_structure
)

logger = logging.getLogger(__name__)


class EchoInkAgent:
    """
    Echo Ink Agent - Sophisticated educational document creation assistant
    
    This agent helps instructors create professional course materials using:
    - AWS Bedrock Claude Sonnet 4.5 for intelligent content generation
    - Built-in Strands tools for file operations
    - Custom document creation tools with template system
    - Memory integration for context retention
    - Both sync and async operation modes
    """
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain", "application/json"]
    
    def __init__(
        self,
        memory_id: str,
        model_id: str = "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name: str = "us-west-2",
        actor_id: str = None,
        session_id: str = None,
    ):
        """
        Initialize Echo Ink Agent
        
        Args:
            memory_id: AgentCore memory ID for context retention
            model_id: Bedrock model ID (defaults to Claude Sonnet 4.5)
            region_name: AWS region
            actor_id: Actor identifier for memory hooks
            session_id: Session identifier for memory hooks
        """
        logger.info("Initializing Echo Ink Agent...")
        
        # Initialize Bedrock model
        self.bedrock_model = BedrockModel(model_id=model_id, region_name=region_name)
        logger.info(f"Using Bedrock model: {model_id}")
        
        # Initialize memory client and hooks
        memory_client = MemoryClient(region_name=region_name)
        
        self.memory_hooks = EchoInkMemoryHooks(
            memory_id=memory_id,
            client=memory_client,
            actor_id=actor_id or "echo_ink_user",
            session_id=session_id or "default_session",
        )
        
        # Combine built-in Strands tools with custom document tools
        all_tools = [
            # Built-in Strands tools for file operations
            file_read,
            file_write, 
            editor,
            
            # Custom document creation tools
            create_educational_document,
            convert_document_to_pdf,
            get_document_template_info,
            search_documents,
            index_documents,
            validate_document_structure,
        ]
        
        # Create the Strands agent
        self.agent = Agent(
            name="Echo Ink Agent",
            description="Sophisticated educational document creation assistant that helps instructors create professional course materials including syllabi, exams, assignments, lecture notes, and lab manuals",
            system_prompt=SYSTEM_PROMPT,
            model=self.bedrock_model,
            tools=all_tools,
            hooks=[self.memory_hooks],
        )
        
        logger.info("Echo Ink Agent initialized successfully")
        logger.info(f"Available tools: {len(all_tools)}")
        
    def get_capabilities(self) -> dict:
        """
        Get agent capabilities and available tools
        
        Returns:
            dict: Agent capabilities and tool information
        """
        return {
            "name": "Echo Ink Agent",
            "description": "Educational document creation assistant",
            "model": self.bedrock_model.model_id,
            "supported_content_types": self.SUPPORTED_CONTENT_TYPES,
            "tools": {
                "built_in": ["file_read", "file_write", "editor"],
                "document_creation": [
                    "create_educational_document",
                    "convert_document_to_pdf", 
                    "get_document_template_info"
                ],
                "document_management": [
                    "search_documents",
                    "index_documents",
                    "validate_document_structure"
                ]
            },
            "document_templates": [
                "syllabus", "exam", "assignment", 
                "lecture", "class_content", "lab"
            ],
            "features": [
                "Template-based document creation",
                "PDF conversion with Pandoc",
                "Document search and indexing",
                "Content validation",
                "Memory-based context retention",
                "Streaming responses",
                "Async/sync operations"
            ]
        }

    async def stream(self, query: str, session_id: str = None) -> str:
        """
        Stream response from the agent (async)
        
        Args:
            query: User query or instruction
            session_id: Optional session ID override
            
        Yields:
            dict: Streaming response events
        """
        response = ""
        try:
            logger.info(f"Processing streaming query: {query[:100]}...")
            
            async for event in self.agent.stream_async(query):
                if "data" in event:
                    # Stream text chunks to the client
                    chunk = event["data"]
                    response += chunk
                    yield {
                        "is_task_complete": "complete" in event,
                        "require_user_input": False,
                        "content": chunk,
                        "event_type": "content_chunk"
                    }
                elif "tool_call" in event:
                    # Notify about tool usage
                    yield {
                        "is_task_complete": False,
                        "require_user_input": False,
                        "content": f"🔧 Using tool: {event.get('tool_name', 'unknown')}",
                        "event_type": "tool_call"
                    }

        except Exception as e:
            logger.error(f"Error in streaming: {e}", exc_info=True)
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"❌ Error processing request: {str(e)}",
                "event_type": "error"
            }
        finally:
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
                "event_type": "completion"
            }

    def invoke(self, query: str, session_id: str = None) -> str:
        """
        Invoke agent synchronously
        
        Args:
            query: User query or instruction
            session_id: Optional session ID override
            
        Returns:
            str: Agent response
        """
        try:
            logger.info(f"Processing synchronous query: {query[:100]}...")
            response = str(self.agent(query))
            logger.info("Query processed successfully")
            return response
            
        except Exception as e:
            logger.error(f"Error invoking agent: {e}", exc_info=True)
            return f"❌ Error processing request: {str(e)}"

    async def invoke_async(self, query: str, session_id: str = None) -> str:
        """
        Invoke agent asynchronously
        
        Args:
            query: User query or instruction
            session_id: Optional session ID override
            
        Returns:
            str: Agent response
        """
        try:
            logger.info(f"Processing async query: {query[:100]}...")
            response = await self.agent.ainvoke(query)
            logger.info("Async query processed successfully")
            return str(response)
            
        except Exception as e:
            logger.error(f"Error in async invoke: {e}", exc_info=True)
            return f"❌ Error processing request: {str(e)}"

    def create_document_from_template(
        self, 
        doc_type: str, 
        course_code: str, 
        title: str, 
        **fields
    ) -> str:
        """
        Convenience method to create documents directly
        
        Args:
            doc_type: Document template type
            course_code: Course identifier
            title: Document title
            **fields: Template field values
            
        Returns:
            str: Creation result message
        """
        try:
            return create_educational_document(doc_type, course_code, title, fields)
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return f"❌ Error creating document: {str(e)}"

    def get_template_help(self, doc_type: str = None) -> str:
        """
        Get help information about templates
        
        Args:
            doc_type: Specific template type or None for all
            
        Returns:
            str: Template help information
        """
        try:
            return get_document_template_info(doc_type)
        except Exception as e:
            logger.error(f"Error getting template help: {e}")
            return f"❌ Error getting template information: {str(e)}"

    def __str__(self) -> str:
        return f"EchoInkAgent(model={self.bedrock_model.model_id}, tools={len(self.agent.tools)})"

    def __repr__(self) -> str:
        return self.__str__()
