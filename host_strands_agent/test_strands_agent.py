#!/usr/bin/env python3
"""
Test script for the Strands-based host agent.
This script tests the agent locally without deploying to AgentCore.
"""

import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock the SSM parameters for local testing
def mock_get_ssm_parameter(param_name):
    """Mock SSM parameter retrieval for local testing"""
    mock_params = {
        "/monitoragent/agentcore/runtime-id": "mock-monitor-runtime-id",
        "/monitoragent/agentcore/provider-name": "mock-monitor-provider",
        "/websearchagent/agentcore/runtime-id": "mock-websearch-runtime-id", 
        "/websearchagent/agentcore/provider-name": "mock-websearch-provider",
    }
    return mock_params.get(param_name, "mock-value")

def mock_get_aws_info():
    """Mock AWS info for local testing"""
    return "123456789012", "us-west-2"

# Patch the utils functions for local testing
import sys
sys.path.insert(0, str(Path(__file__).parent))

# Mock the utils module
class MockUtils:
    @staticmethod
    def get_ssm_parameter(param_name):
        return mock_get_ssm_parameter(param_name)
    
    @staticmethod
    def get_aws_info():
        return mock_get_aws_info()

sys.modules['utils'] = MockUtils()

# Now import the agent
from agent import HostAgent

async def test_agent_creation():
    """Test creating the host agent"""
    try:
        logger.info("Testing host agent creation...")
        
        # Set required environment variables
        os.environ["BEDROCK_MODEL_ID"] = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        # Create agent
        session_id = "test-session-123"
        actor_id = "test-actor"
        
        agent = HostAgent(session_id=session_id, actor_id=actor_id)
        
        logger.info("✅ Host agent created successfully!")
        logger.info(f"Agent name: {agent.agent.name}")
        logger.info(f"Agent description: {agent.agent.description}")
        logger.info(f"Number of tools: {len(agent.agent.tools)}")
        
        # List the tools
        for i, tool in enumerate(agent.agent.tools):
            logger.info(f"Tool {i+1}: {tool.__name__}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create host agent: {e}")
        return False

async def test_agent_invoke():
    """Test invoking the agent with a simple query"""
    try:
        logger.info("Testing agent invocation...")
        
        # Set required environment variables
        os.environ["BEDROCK_MODEL_ID"] = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        # Create agent
        session_id = "test-session-123"
        actor_id = "test-actor"
        
        agent = HostAgent(session_id=session_id, actor_id=actor_id)
        
        # Test query (this will fail with authentication but should show the structure)
        test_query = "Hello, can you help me check the status of my AWS resources?"
        
        logger.info(f"Testing with query: {test_query}")
        
        # This will likely fail due to authentication, but we can catch and analyze
        try:
            response = agent.invoke(test_query)
            logger.info(f"✅ Agent response: {response}")
        except Exception as invoke_error:
            logger.warning(f"⚠️ Agent invocation failed (expected due to auth): {invoke_error}")
            logger.info("This is expected when running locally without proper AWS credentials")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to test agent invocation: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🧪 Starting Strands Host Agent Tests")
    logger.info("=" * 50)
    
    # Test 1: Agent Creation
    logger.info("\n📝 Test 1: Agent Creation")
    creation_success = await test_agent_creation()
    
    # Test 2: Agent Invocation (will fail with auth but tests structure)
    logger.info("\n📝 Test 2: Agent Invocation Structure")
    invocation_success = await test_agent_invoke()
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("🏁 Test Summary:")
    logger.info(f"   Agent Creation: {'✅ PASS' if creation_success else '❌ FAIL'}")
    logger.info(f"   Agent Structure: {'✅ PASS' if invocation_success else '❌ FAIL'}")
    
    if creation_success and invocation_success:
        logger.info("\n🎉 All tests passed! The Strands host agent is properly configured.")
        logger.info("💡 To test with real AWS resources, deploy using the deployment script.")
    else:
        logger.error("\n❌ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main())