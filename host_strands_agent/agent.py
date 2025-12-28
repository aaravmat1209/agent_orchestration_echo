from bedrock_agentcore.identity.auth import requires_access_token
from prompt import SYSTEM_PROMPT
from strands import Agent, tool
from strands.models import BedrockModel
from urllib.parse import quote
import httpx
import os
import uuid
import logging
from uuid import uuid4
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, TextPart

IS_DOCKER = os.getenv("DOCKER_CONTAINER", "0") == "1"
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0")

if IS_DOCKER:
    from utils import get_ssm_parameter, get_aws_info
else:
    from host_strands_agent.utils import get_ssm_parameter, get_aws_info

logger = logging.getLogger(__name__)

# AWS and agent configuration
account_id, region = get_aws_info()

MONITOR_AGENT_ID = get_ssm_parameter("/monitoragent/agentcore/runtime-id")
MONITOR_PROVIDER_NAME = get_ssm_parameter("/monitoragent/agentcore/provider-name")
MONITOR_AGENT_ARN = (
    f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/{MONITOR_AGENT_ID}"
)

ECHOINK_AGENT_ID = get_ssm_parameter("/echoinkagent/agentcore/runtime-id")
ECHOINK_PROVIDER_NAME = get_ssm_parameter("/echoinkagent/agentcore/provider-name")
ECHOINK_AGENT_ARN = (
    f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/{ECHOINK_AGENT_ID}"
)

ECHOPREPARE_AGENT_ID = get_ssm_parameter("/echoprepareagent/agentcore/runtime-id")
ECHOPREPARE_PROVIDER_NAME = get_ssm_parameter("/echoprepareagent/agentcore/provider-name")
ECHOPREPARE_AGENT_ARN = (
    f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/{ECHOPREPARE_AGENT_ID}"
)


class A2AAgentTool:
    """A2A Agent Tool for communicating with remote agents via A2A protocol"""
    
    def __init__(self, agent_url: str, agent_name: str, provider_name: str, session_id: str, actor_id: str):
        self.agent_url = agent_url
        self.agent_name = agent_name
        self.provider_name = provider_name
        self.session_id = session_id
        self.actor_id = actor_id
        self.agent_card = None
        logger.info(f"Initializing A2A tool for {agent_name} at {agent_url}")

    def _get_authenticated_client(self) -> httpx.AsyncClient:
        """Create an authenticated httpx client"""
        @requires_access_token(
            provider_name=self.provider_name,
            scopes=[],
            auth_flow="M2M",
            into="bearer_token",
            force_authentication=True,
        )
        def _create_client(bearer_token: str = str()) -> httpx.AsyncClient:
            headers = {
                "Authorization": f"Bearer {bearer_token}",
                "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": self.session_id,
                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actorid": self.actor_id,
            }

            return httpx.AsyncClient(
                timeout=httpx.Timeout(timeout=300.0),
                headers=headers,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )

        return _create_client()

    async def call_agent(self, message: str) -> str:
        """
        Send a message to the A2A agent.

        Args:
            message: The message to send to the agent

        Returns:
            Response from the A2A agent
        """
        try:
            logger.info(f"Calling {self.agent_name} with message: {message[:100]}...")
            
            # Create authenticated client
            httpx_client = self._get_authenticated_client()
            
            # Get agent card
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=self.agent_url)
            agent_card = await resolver.get_agent_card()

            # Create client using factory
            config = ClientConfig(
                httpx_client=httpx_client,
                streaming=False,  # Use non-streaming mode for sync response
            )
            factory = ClientFactory(config)
            client = factory.create(agent_card)

            # Create and send message
            msg = Message(
                kind="message",
                role=Role.user,
                parts=[Part(TextPart(kind="text", text=message))],
                message_id=uuid4().hex,
            )

            # Send message and collect response
            response_text = ""
            async for event in client.send_message(msg):
                if isinstance(event, Message):
                    for part in event.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
                elif isinstance(event, tuple) and len(event) == 2:
                    # (Task, UpdateEvent) tuple - extract text from Task artifacts
                    task, update_event = event
                    if hasattr(task, "artifacts") and task.artifacts:
                        for artifact in task.artifacts:
                            if hasattr(artifact, "parts") and artifact.parts:
                                for part in artifact.parts:
                                    if hasattr(part, "root") and hasattr(part.root, "text"):
                                        response_text += part.root.text

            await httpx_client.aclose()
            
            if not response_text:
                response_text = f"No response received from {self.agent_name}"
                
            logger.info(f"Received response from {self.agent_name}: {response_text[:100]}...")
            return response_text

        except Exception as e:
            logger.error(f"Error contacting {self.agent_name}: {str(e)}", exc_info=True)
            return f"Error contacting {self.agent_name}: {str(e)}"


class HostAgent:
    """Host Agent using Strands framework with A2A tools for orchestration"""
    
    def __init__(self, session_id: str, actor_id: str):
        self.session_id = session_id
        self.actor_id = actor_id
        
        # Create A2A agent tools
        monitor_agent_url = (
            f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/"
            f"{quote(MONITOR_AGENT_ARN, safe='')}/invocations"
        )

        echoink_agent_url = (
            f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/"
            f"{quote(ECHOINK_AGENT_ARN, safe='')}/invocations"
        )

        echoprepare_agent_url = (
            f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/"
            f"{quote(ECHOPREPARE_AGENT_ARN, safe='')}/invocations"
        )

        self.monitor_tool = A2AAgentTool(
            agent_url=monitor_agent_url,
            agent_name="monitor_agent",
            provider_name=MONITOR_PROVIDER_NAME,
            session_id=session_id,
            actor_id=actor_id
        )

        self.echoink_tool = A2AAgentTool(
            agent_url=echoink_agent_url,
            agent_name="echoink_agent",
            provider_name=ECHOINK_PROVIDER_NAME,
            session_id=session_id,
            actor_id=actor_id
        )

        self.echoprepare_tool = A2AAgentTool(
            agent_url=echoprepare_agent_url,
            agent_name="echoprepare_agent",
            provider_name=ECHOPREPARE_PROVIDER_NAME,
            session_id=session_id,
            actor_id=actor_id
        )

        # Create Bedrock model
        bedrock_model = BedrockModel(model_id=BEDROCK_MODEL_ID, region_name=region)
        
        # Create Strands agent with A2A tools
        self.agent = Agent(
            name="Host Agent",
            description="Intelligent orchestrator that delegates tasks to specialized agents",
            system_prompt=SYSTEM_PROMPT,
            model=bedrock_model,
            tools=[
                self._create_monitor_tool(),
                self._create_echoink_tool(),
                self._create_echoprepare_tool()
            ]
        )
        
        logger.info("Host Agent initialized with Strands framework and A2A tools")

    def _create_monitor_tool(self):
        """Create the monitor agent tool"""
        @tool
        async def monitor_agent(message: str) -> str:
            """
            Delegate monitoring tasks to the monitoring agent.
            Use for CloudWatch metrics, logs, alarms, and AWS service monitoring.
            
            Args:
                message: The monitoring query or task to delegate
                
            Returns:
                Response from the monitoring agent
            """
            return await self.monitor_tool.call_agent(message)
        
        return monitor_agent

    def _create_echoink_tool(self):
        """Create the echo ink agent tool"""
        @tool
        async def echoink_agent(message: str) -> str:
            """
            Delegate educational document creation tasks to the Echo Ink agent.
            Use for creating course materials, lesson plans, assessments, and educational content.

            Args:
                message: The document creation request or educational content task to delegate

            Returns:
                Response from the Echo Ink agent
            """
            return await self.echoink_tool.call_agent(message)

        return echoink_agent

    def _create_echoprepare_tool(self):
        """Create the echo prepare agent tool"""
        @tool
        async def echoprepare_agent(message: str) -> str:
            """
            Delegate student study and exam preparation tasks to the Echo Prepare agent.
            Use for helping students research topics, generate practice questions, create study notes,
            and track learning progress.

            Args:
                message: The study assistance request or exam preparation task to delegate

            Returns:
                Response from the Echo Prepare agent
            """
            return await self.echoprepare_tool.call_agent(message)

        return echoprepare_agent

    async def stream(self, query: str):
        """Stream response from the agent"""
        try:
            async for event in self.agent.stream_async(query):
                if "data" in event:
                    yield {
                        "is_task_complete": "complete" in event,
                        "require_user_input": False,
                        "content": event["data"],
                    }
        except Exception as e:
            logger.error(f"Error in agent streaming: {e}", exc_info=True)
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"Error processing request: {e}",
            }
        finally:
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "",
            }

    def invoke(self, query: str) -> str:
        """Invoke the agent synchronously"""
        try:
            return str(self.agent(query))
        except Exception as e:
            logger.error(f"Error invoking agent: {e}", exc_info=True)
            raise Exception(f"Error invoking agent: {e}")


def get_host_agent(session_id: str, actor_id: str) -> HostAgent:
    """Create and return a host agent instance"""
    return HostAgent(session_id=session_id, actor_id=actor_id)


async def get_agent_and_card(session_id: str, actor_id: str):
    """
    Get the host agent and return agent cards info for compatibility.
    This maintains compatibility with the existing main.py structure.
    """
    host_agent = get_host_agent(session_id=session_id, actor_id=actor_id)
    
    # Return agent cards info for compatibility
    agents_cards = {
        "monitor_agent": {
            "agent_card_url": f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{quote(MONITOR_AGENT_ARN, safe='')}/invocations/.well-known/agent-card.json"
        },
        "echoink_agent": {
            "agent_card_url": f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{quote(ECHOINK_AGENT_ARN, safe='')}/invocations/.well-known/agent-card.json"
        },
        "echoprepare_agent": {
            "agent_card_url": f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{quote(ECHOPREPARE_AGENT_ARN, safe='')}/invocations/.well-known/agent-card.json"
        }
    }

    return host_agent, agents_cards


if not IS_DOCKER:
    session_id = str(uuid.uuid4())
    actor_id = "webadk"
    host_agent = get_host_agent(session_id=session_id, actor_id=actor_id)
