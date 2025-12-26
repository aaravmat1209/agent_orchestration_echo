from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import EchoInkAgentExecutor
from starlette.responses import JSONResponse
import boto3
import logging
import os
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration with validation
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")

MEMORY_ID = os.getenv("MEMORY_ID")
if not MEMORY_ID:
    raise RuntimeError("Missing MEMORY_ID environment variable")

AWS_REGION = os.getenv("MCP_REGION")
if not AWS_REGION:
    raise RuntimeError("Missing MCP_REGION environment variable")

# Use the complete runtime URL from environment variable, fallback to local
runtime_url = os.environ.get("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000

agent_card = AgentCard(
    name="Echo Ink Agent",
    description="Educational document creation agent that helps instructors create course materials with templates and structured fields",
    url=runtime_url,
    version="1.0.0",
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
    skills=[
        AgentSkill(
            id="document_creator",
            name="Document Creator",
            description="Creates educational documents from templates with structured fields like title, learning objectives, assessments, etc.",
            tags=["education", "documents", "templates"],
        ),
        AgentSkill(
            id="field_editor",
            name="Field Editor",
            description="Edits specific fields in existing documents while preserving document structure",
            tags=["editing", "documents", "fields"],
        ),
        AgentSkill(
            id="document_previewer",
            name="Document Previewer",
            description="Generates and displays formatted previews of educational documents",
            tags=["preview", "documents", "formatting"],
        ),
        AgentSkill(
            id="document_finalizer",
            name="Document Finalizer",
            description="Finalizes documents for export in various formats (PDF, DOCX, HTML)",
            tags=["export", "documents", "finalization"],
        ),
        AgentSkill(
            id="session_manager",
            name="Session Manager",
            description="Manages document creation sessions, saves progress, and restores previous sessions",
            tags=["session", "persistence", "state"],
        ),
    ],
)

# Create request handler with executor
request_handler = DefaultRequestHandler(
    agent_executor=EchoInkAgentExecutor(), task_store=InMemoryTaskStore()
)

# Create A2A server
server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

# Build the app and add health endpoint
app = server.build()


@app.route("/ping", methods=["GET"])
async def ping(request):
    """Ping endpoint"""
    return JSONResponse({"status": "healthy"})


logger.info("✅ Echo Ink A2A Server configured")
logger.info(f"📍 Server URL: {runtime_url}")
logger.info(f"🏥 Health check: {runtime_url}/health")
logger.info(f"🏓 Ping: {runtime_url}/ping")

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
