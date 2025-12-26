#!/usr/bin/env python3
"""
Echo Ink Agent - Interactive Demo
Test the agents-as-tools pattern with AWS Bedrock integration
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise for demo

def print_banner():
    """Print welcome banner"""
    print("=" * 70)
    print("🎓 ECHO INK AGENT - INTERACTIVE DEMO")
    print("=" * 70)
    print("Conversational document creation using agents-as-tools pattern!")
    print("Powered by AWS Bedrock Claude Sonnet 4.5")
    print()
    print("💬 Just type natural language requests like:")
    print("   • I want to create a midterm exam for MAT343")
    print("   • Create a syllabus for CS101 programming")
    print("   • Show me my active sessions")
    print("   • The instructor name is Dr. Johnson")
    print("   • Finalize my exam document")
    print()
    print("🔧 Commands:")
    print("   • help    - Show examples")
    print("   • test    - Test AWS connection")
    print("   • quit    - Exit demo")
    print("   • clear   - Clear screen")
    print("=" * 70)

def print_help():
    """Print example interactions"""
    print("\n📖 EXAMPLE INTERACTIONS")
    print("-" * 50)
    print("🎯 CREATING DOCUMENTS:")
    print("   I want to create a midterm exam for MAT343 statistics")
    print("   Create a syllabus for CS101 introduction to programming")
    print("   Make a lab manual for PHYS201 mechanics")
    print("   Generate an assignment for CHEM101")
    print()
    print("✏️ EDITING DOCUMENTS:")
    print("   The instructor name is Dr. Sarah Johnson")
    print("   Set the exam duration to 90 minutes")
    print("   Total points should be 100")
    print("   The course title is Introduction to Statistics")
    print()
    print("👀 VIEWING PROGRESS:")
    print("   Show me my active document sessions")
    print("   What's the status of my exam?")
    print("   Preview my syllabus content")
    print("   List all my documents")
    print()
    print("✅ FINALIZING:")
    print("   Finalize my exam and create the PDF")
    print("   Complete my syllabus document")
    print()
    print("🔍 SEARCHING:")
    print("   Find all my statistics documents")
    print("   Search for CS101 materials")
    print()

def test_aws_connection():
    """Test AWS Bedrock connection"""
    print("\n🔧 Testing AWS Bedrock Connection...")
    print("-" * 50)
    
    try:
        import boto3
        from strands.models import BedrockModel
        
        # Test boto3 session
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials is None:
            print("❌ No AWS credentials found")
            print("💡 Run 'aws configure' or set AWS environment variables")
            return False
        
        print(f"✅ AWS credentials found")
        print(f"   Region: {session.region_name or 'default'}")
        
        # Test Bedrock model initialization
        try:
            model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
            model = BedrockModel(
                model_id=model_id,
                region_name=session.region_name or "us-west-2"
            )
            print("✅ Bedrock model initialized successfully")
            print(f"   Model: {model_id}")
            return True
            
        except Exception as e:
            print(f"❌ Bedrock model initialization failed: {e}")
            print("💡 Make sure Claude Sonnet 4.5 is enabled in your AWS region")
            return False
            
    except ImportError as e:
        print(f"❌ Missing dependencies: {e}")
        print("💡 Install required packages: pip install boto3 strands-agents")
        return False
    except Exception as e:
        print(f"❌ AWS connection test failed: {e}")
        return False

def initialize_agent():
    """Initialize the Echo Ink Agent"""
    try:
        from agent import EchoInkAgent
        import random
        import string
        
        print("\n🤖 Initializing Echo Ink Agent...")
        
        # Get AWS session info
        import boto3
        session = boto3.Session()
        region = session.region_name or "us-west-2"
        
        # Generate a valid memory ID that matches AWS pattern: [a-zA-Z][a-zA-Z0-9-_]{0,99}-[a-zA-Z0-9]{10}
        # Pattern: starts with letter, then letters/numbers/hyphens/underscores, then hyphen, then 10 alphanumeric chars
        random_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        memory_id = f"echo-ink-demo-{random_suffix}"
        
        agent = EchoInkAgent(
            memory_id=memory_id,
            model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name=region,
            actor_id="demo_user",
            session_id="demo_session"
        )
        
        print("✅ Echo Ink Agent initialized successfully!")
        print(f"   Model: Claude Sonnet 4.5")
        print(f"   Region: {region}")
        print(f"   Memory ID: {memory_id}")
        print(f"   Sub-agents: 5 specialized agents")
        
        return agent
        
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        print("💡 Check AWS credentials and Bedrock access")
        return None

async def handle_streaming_response(agent, query):
    """Handle streaming response from agent"""
    print("\n🤖 Echo Ink Agent (streaming):")
    print("-" * 50)

    try:
        async for event in agent.stream(query, session_id="demo_session"):
            content = event.get("content", "")
            is_complete = event.get("is_task_complete", False)

            # Print incremental chunks only, skip the final accumulated message
            if content and not is_complete:
                print(content, end="", flush=True)

            # End with newline when complete
            if is_complete:
                print("\n")
                break

    except Exception as e:
        print(f"\n❌ Streaming error: {e}")
        # Fallback to synchronous
        print("\n🔄 Falling back to synchronous mode...")
        response = agent.invoke(query, session_id="demo_session")
        print(response)

def main():
    """Main interactive loop with proper agent orchestration"""
    print_banner()
    
    # Create documents directory if it doesn't exist
    docs_dir = Path("documents")
    docs_dir.mkdir(exist_ok=True)
    print(f"📁 Documents will be saved to: {docs_dir.absolute()}")
    
    # Test AWS connection first
    if not test_aws_connection():
        print("\n❌ AWS connection failed. Please fix the issues above and try again.")
        return
    
    # Initialize the Echo Ink Agent
    agent = initialize_agent()
    if not agent:
        print("\n❌ Agent initialization failed. Please check the errors above.")
        return
    
    print("\n💡 Try: 'I want to create a midterm exam for MAT343'")
    print("💡 Or type 'help' for more examples")
    
    # Main interaction loop
    while True:
        try:
            # Get user input
            user_input = input("\n🎓 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thanks for testing Echo Ink Agent!")
                break
            
            elif user_input.lower() in ['help', 'h']:
                print_help()
                continue
            
            elif user_input.lower() == 'test':
                test_aws_connection()
                continue
            
            elif user_input.lower() == 'clear':
                os.system('clear' if os.name == 'posix' else 'cls')
                print_banner()
                continue
            
            elif user_input.lower() == 'caps':
                # Show agent capabilities
                print(f"\n🤖 Agent Capabilities:")
                print(f"   Name: Echo Ink Agent")
                print(f"   Architecture: agents-as-tools")
                print(f"   Sub-agents: 5")
                print(f"   • document_creator_agent - Creates document schemas")
                print(f"   • field_editor_agent - Edits document fields")
                print(f"   • document_previewer_agent - Shows document status")
                print(f"   • document_finalizer_agent - Finalizes documents")
                print(f"   • session_manager_agent - Manages sessions")
                continue
            
            # Process natural language input through the agent
            print("\n🤖 Echo Ink Agent:")
            print("-" * 50)

            try:
                # Use synchronous mode for simplicity in demo
                response = agent.invoke(user_input, session_id="demo_session")
                print(response)

            except Exception as e:
                print(f"❌ Error processing request: {e}")
                print("💡 Try rephrasing your request or type 'help' for examples")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            print("💡 Type 'help' for examples or 'quit' to exit")

def run_async_demo():
    """Run demo with async streaming support"""
    print_banner()
    
    # Create documents directory
    docs_dir = Path("documents")
    docs_dir.mkdir(exist_ok=True)
    print(f"📁 Documents will be saved to: {docs_dir.absolute()}")
    
    # Test AWS connection
    if not test_aws_connection():
        print("\n❌ AWS connection failed. Please fix the issues above and try again.")
        return
    
    # Initialize agent
    agent = initialize_agent()
    if not agent:
        print("\n❌ Agent initialization failed. Please check the errors above.")
        return
    
    print("\n💡 Try: 'I want to create a midterm exam for MAT343'")
    print("💡 This demo uses streaming responses for real-time feedback")
    
    async def async_loop():
        while True:
            try:
                user_input = input("\n🎓 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Thanks for testing Echo Ink Agent!")
                    break
                
                elif user_input.lower() in ['help', 'h']:
                    print_help()
                    continue
                
                elif user_input.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    print_banner()
                    continue
                
                # Process with streaming
                await handle_streaming_response(agent, user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    # Run the async loop
    asyncio.run(async_loop())

if __name__ == "__main__":
    # Choose demo mode
    print("Select demo mode:")
    print("1. Standard (synchronous responses)")
    print("2. Streaming (real-time responses)")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == "2":
            run_async_demo()
        else:
            main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception:
        # Default to standard mode
        main()