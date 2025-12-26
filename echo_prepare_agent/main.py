from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import EchoPrepareAgentExecutor
from dotenv import load_dotenv
from pathlib import Path
from starlette.responses import JSONResponse
import logging
import os
import uvicorn


# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

runtime_url = os.getenv("AGENTCORE_RUNTIME_URL", "http://127.0.0.1:9000/")
host, port = "0.0.0.0", 9000

agent_card = AgentCard(
    name="Echo Prepare Agent",
    description="Student study and exam preparation assistant that helps research topics, generate practice materials, create study notes, and track learning progress",
    url=runtime_url,
    version="0.1.0",
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    capabilities=AgentCapabilities(streaming=True, pushNotifications=False),
    skills=[
        AgentSkill(
            id="study_assistant",
            name="Study & Exam Preparation",
            description="Comprehensive study assistance including research, practice question generation, and study note creation",
            tags=["study", "practice", "notes", "learning", "exam-prep"],
            examples=[
                "Create 5 multiple choice questions on the Civil War",
                "Make flashcards for photosynthesis concepts",
                "Generate an outline for studying Python recursion",
                "Create practice essay prompts for Shakespeare's Macbeth",
            ],
        ),
        AgentSkill(
            id="research",
            name="Educational Research",
            description="Search for educational content, tutorials, and study materials on any topic",
            tags=["search", "research", "education", "resources"],
            examples=[
                "Find tutorials on calculus derivatives",
                "Search for explanations of cellular respiration",
                "Get practice problems for organic chemistry",
            ],
        ),
        AgentSkill(
            id="progress_tracking",
            name="Learning Progress Tracker",
            description="Track confidence levels and learning progress over time to identify areas needing focus",
            tags=["tracking", "confidence", "progress", "goals"],
            examples=[
                "Track my confidence in Python loops (7/10)",
                "Record that I'm struggling with recursion (3/10)",
                "Show my progress on algebra topics",
            ],
        ),
    ],
)

# Create request handler with executor
request_handler = DefaultRequestHandler(
    agent_executor=EchoPrepareAgentExecutor(), task_store=InMemoryTaskStore()
)

# Create A2A server
server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)

# Build the app and add health endpoint
app = server.build()


@app.route("/ping", methods=["GET"])
async def ping(request):
    """Ping endpoint"""
    return JSONResponse({"status": "healthy"})


logger.info("✅ A2A Server configured")
logger.info(f"📍 Server URL: {runtime_url}")
logger.info(f"🏥 Health check: {runtime_url}/health")
logger.info(f"🏓 Ping: {runtime_url}/ping")

if __name__ == "__main__":
    uvicorn.run(app, host=host, port=port)
