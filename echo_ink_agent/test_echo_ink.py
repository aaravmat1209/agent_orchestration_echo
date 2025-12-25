#!/usr/bin/env python3
"""
Comprehensive test script for Echo Ink Agent
Tests document creation, template system, and agent capabilities
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock dependencies for testing
class MockMemoryClient:
    def __init__(self, region_name):
        self.region_name = region_name
    
    async def search_memories(self, **kwargs):
        return []
    
    async def add_memory(self, **kwargs):
        return {"memory_id": "test-memory"}
    
    def retrieve_memories(self, **kwargs):
        return []
    
    def create_event(self, **kwargs):
        return {"eventId": "test-event-123"}
    
    def get_last_k_turns(self, **kwargs):
        return []

# Mock the bedrock_agentcore module
class MockBedrockAgentCore:
    class memory:
        MemoryClient = MockMemoryClient

sys.modules['bedrock_agentcore'] = MockBedrockAgentCore()
sys.modules['bedrock_agentcore.memory'] = MockBedrockAgentCore.memory

# Mock strands_tools (in case they're not available)
def mock_tool(func):
    """Mock tool decorator"""
    return func

try:
    from strands_tools import file_read, file_write, editor
except ImportError:
    logger.warning("strands_tools not available, using mocks")
    
    def file_read(path: str) -> str:
        """Mock file_read tool"""
        try:
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"
    
    def file_write(path: str, content: str) -> str:
        """Mock file_write tool"""
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {e}"
    
    def editor(path: str, content: str) -> str:
        """Mock editor tool"""
        return file_write(path, content)

# Mock strands framework
class MockBedrockModel:
    def __init__(self, model_id, region_name):
        self.model_id = model_id
        self.region_name = region_name

class MockAgent:
    def __init__(self, name, description, system_prompt, model, tools, hooks):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.model = model
        self.tools = tools
        self.hooks = hooks
        self.messages = []
    
    def __call__(self, query):
        return f"Mock response to: {query}"
    
    async def ainvoke(self, query):
        return f"Mock async response to: {query}"
    
    async def stream_async(self, query):
        chunks = [
            {"data": "Processing your request..."},
            {"data": f" Generated response for: {query[:50]}..."},
            {"complete": True, "data": " Done!"}
        ]
        for chunk in chunks:
            yield chunk

sys.modules['strands'] = type('MockStrands', (), {
    'Agent': MockAgent,
    'tool': mock_tool
})()

sys.modules['strands.models'] = type('MockModels', (), {
    'BedrockModel': MockBedrockModel
})()

sys.modules['strands.hooks'] = type('MockHooks', (), {
    'Hook': object,
    'HookProvider': object,
    'HookRegistry': object,
    'MessageAddedEvent': object,
    'AfterInvocationEvent': object,
    'AgentInitializedEvent': object,
})()

# Now import our modules
from document_tools import (
    create_educational_document,
    get_document_template_info,
    search_documents,
    index_documents,
    validate_document_structure
)
from agent import EchoInkAgent


class EchoInkTester:
    """Comprehensive tester for Echo Ink Agent"""
    
    def __init__(self):
        self.test_results = []
        self.documents_created = []
    
    def log_test(self, test_name: str, success: bool, message: str = ""):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append((test_name, success, message))
        logger.info(f"{status} - {test_name}: {message}")
    
    async def test_template_system(self):
        """Test the document template system"""
        logger.info("🧪 Testing Template System...")
        
        # Test 1: Get all template info
        try:
            all_templates = get_document_template_info()
            success = "syllabus" in all_templates and "exam" in all_templates
            self.log_test("Template List", success, f"Found templates in response")
        except Exception as e:
            self.log_test("Template List", False, str(e))
        
        # Test 2: Get specific template info
        try:
            syllabus_info = get_document_template_info("syllabus")
            success = "Required Fields" in syllabus_info
            self.log_test("Specific Template Info", success, "Syllabus template info retrieved")
        except Exception as e:
            self.log_test("Specific Template Info", False, str(e))
        
        # Test 3: Invalid template
        try:
            invalid_info = get_document_template_info("invalid_template")
            success = "Error" in invalid_info
            self.log_test("Invalid Template Handling", success, "Properly handled invalid template")
        except Exception as e:
            self.log_test("Invalid Template Handling", False, str(e))
    
    async def test_document_creation(self):
        """Test document creation functionality"""
        logger.info("🧪 Testing Document Creation...")
        
        # Test 1: Create a syllabus
        try:
            result = create_educational_document(
                "syllabus",
                "CS101",
                "Introduction to Computer Science",
                {
                    "instructor_name": "Dr. Jane Smith",
                    "semester": "Fall 2024",
                    "credits": "3",
                    "description": "Fundamentals of programming and computer science concepts"
                }
            )
            success = "Successfully created" in result
            if success:
                self.documents_created.append("CS101_Syllabus_Introduction_DRAFT.md")
            self.log_test("Syllabus Creation", success, "Created syllabus document")
        except Exception as e:
            self.log_test("Syllabus Creation", False, str(e))
        
        # Test 2: Create an exam
        try:
            result = create_educational_document(
                "exam",
                "CS101",
                "Midterm Exam",
                {
                    "course_title": "Introduction to Computer Science",
                    "exam_type": "Midterm",
                    "duration": "90 minutes",
                    "total_points": "100"
                }
            )
            success = "Successfully created" in result
            if success:
                self.documents_created.append("CS101_Exam_Midterm_DRAFT.md")
            self.log_test("Exam Creation", success, "Created exam document")
        except Exception as e:
            self.log_test("Exam Creation", False, str(e))
        
        # Test 3: Missing required fields
        try:
            result = create_educational_document(
                "assignment",
                "CS101",
                "Homework 1",
                {
                    "assignment_number": "1"
                    # Missing required fields: due_date, total_points, overview
                }
            )
            success = "Missing required fields" in result
            self.log_test("Required Field Validation", success, "Properly validated missing fields")
        except Exception as e:
            self.log_test("Required Field Validation", False, str(e))
    
    async def test_document_management(self):
        """Test document management tools"""
        logger.info("🧪 Testing Document Management...")
        
        # Test 1: Index documents
        try:
            result = index_documents()
            success = "Document Index" in result or "No documents found" in result
            self.log_test("Document Indexing", success, "Document index generated")
        except Exception as e:
            self.log_test("Document Indexing", False, str(e))
        
        # Test 2: Search documents
        try:
            result = search_documents("CS101")
            success = "Found" in result or "No documents found" in result
            self.log_test("Document Search", success, "Document search executed")
        except Exception as e:
            self.log_test("Document Search", False, str(e))
        
        # Test 3: Validate document (if any exist)
        if self.documents_created:
            try:
                doc_path = f"documents/{self.documents_created[0]}"
                if Path(doc_path).exists():
                    result = validate_document_structure(doc_path)
                    success = "Document Validation" in result
                    self.log_test("Document Validation", success, "Document validation completed")
                else:
                    self.log_test("Document Validation", True, "No documents to validate")
            except Exception as e:
                self.log_test("Document Validation", False, str(e))
    
    async def test_agent_creation(self):
        """Test Echo Ink Agent creation and basic functionality"""
        logger.info("🧪 Testing Agent Creation...")
        
        try:
            # Create agent
            agent = EchoInkAgent(
                memory_id="test-memory-123",
                model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
                region_name="us-west-2",
                actor_id="test-user",
                session_id="test-session"
            )
            
            self.log_test("Agent Initialization", True, f"Agent created: {agent.agent.name}")
            
            # Test capabilities
            capabilities = agent.get_capabilities()
            success = "document_creation" in capabilities.get("tools", {})
            self.log_test("Agent Capabilities", success, f"Found {len(capabilities.get('tools', {}))} tool categories")
            
            # Test synchronous invoke
            response = agent.invoke("Hello, can you help me create a syllabus?")
            success = len(response) > 0
            self.log_test("Synchronous Invoke", success, f"Response length: {len(response)}")
            
            # Test asynchronous invoke
            async_response = await agent.invoke_async("What document templates are available?")
            success = len(async_response) > 0
            self.log_test("Asynchronous Invoke", success, f"Async response length: {len(async_response)}")
            
            # Test streaming
            stream_chunks = []
            async for chunk in agent.stream("Create a simple assignment template"):
                stream_chunks.append(chunk)
            
            success = len(stream_chunks) > 0
            self.log_test("Streaming Response", success, f"Received {len(stream_chunks)} chunks")
            
        except Exception as e:
            self.log_test("Agent Creation", False, str(e))
    
    async def test_integration_scenario(self):
        """Test a complete integration scenario"""
        logger.info("🧪 Testing Integration Scenario...")
        
        try:
            # Scenario: Create a complete course package
            agent = EchoInkAgent(
                memory_id="integration-test",
                actor_id="professor-test",
                session_id="integration-session"
            )
            
            # Step 1: Get template help
            help_response = agent.get_template_help()
            success = "Available Document Templates" in help_response
            self.log_test("Integration - Template Help", success, "Retrieved template help")
            
            # Step 2: Create syllabus using convenience method
            syllabus_result = agent.create_document_from_template(
                "syllabus",
                "MATH201",
                "Calculus II",
                instructor_name="Dr. Alice Johnson",
                semester="Spring 2025",
                credits="4",
                description="Advanced calculus including integration techniques and series"
            )
            success = "Successfully created" in syllabus_result
            self.log_test("Integration - Syllabus Creation", success, "Created syllabus via convenience method")
            
            # Step 3: Create assignment
            assignment_result = agent.create_document_from_template(
                "assignment",
                "MATH201",
                "Integration Techniques",
                assignment_number="3",
                due_date="2025-03-15",
                total_points="50",
                overview="Practice integration by parts and substitution methods"
            )
            success = "Successfully created" in assignment_result
            self.log_test("Integration - Assignment Creation", success, "Created assignment via convenience method")
            
        except Exception as e:
            self.log_test("Integration Scenario", False, str(e))
    
    def print_summary(self):
        """Print test summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for _, success, _ in self.test_results if success)
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*70)
        print("🏁 ECHO INK AGENT TEST SUMMARY")
        print("="*70)
        print(f"📊 Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for test_name, success, message in self.test_results:
                if not success:
                    print(f"   • {test_name}: {message}")
        
        print(f"\n📁 Documents Created: {len(self.documents_created)}")
        for doc in self.documents_created:
            print(f"   • {doc}")
        
        print("\n💡 Next Steps:")
        print("   • Deploy to AgentCore runtime for full functionality")
        print("   • Test with real AWS Bedrock integration")
        print("   • Install Pandoc for PDF conversion testing")
        print("   • Create CloudFormation template for deployment")
        
        return passed_tests == total_tests


async def main():
    """Main test execution"""
    print("🚀 Starting Echo Ink Agent Comprehensive Tests")
    print("="*70)
    
    tester = EchoInkTester()
    
    # Run all test suites
    await tester.test_template_system()
    await tester.test_document_creation()
    await tester.test_document_management()
    await tester.test_agent_creation()
    await tester.test_integration_scenario()
    
    # Print summary
    all_passed = tester.print_summary()
    
    if all_passed:
        print("\n🎉 All tests passed! Echo Ink Agent is ready for deployment.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())