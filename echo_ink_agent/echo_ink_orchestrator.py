#!/usr/bin/env python3
"""
Echo Ink Agent - Educational Document Creation System
Using the "Agents as Tools" pattern with Strands Agents SDK
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import markdown
from weasyprint import HTML, CSS

from strands import Agent, tool
from strands.models import BedrockModel

from templates import (
    get_template,
    populate_template,
    generate_filename,
    list_template_types
)
from document_tools import read_document, write_document, update_document, delete_document
from session_storage import AgentCoreSessionStorage

__all__ = ['initialize_session_storage']  # Export for agent.py to use

logger = logging.getLogger(__name__)

# ============================================================================
# SHARED STATE
# ============================================================================

# Session storage using AgentCore Memory (initialized when agent is created)
SESSION_STORAGE: Optional[AgentCoreSessionStorage] = None


def initialize_session_storage(memory_id: str, memory_client, actor_id: str):
    """
    Initialize the session storage with AgentCore Memory.
    This should be called when the agent is created.

    Args:
        memory_id: AgentCore memory ID
        memory_client: MemoryClient instance
        actor_id: Actor ID for the user
    """
    global SESSION_STORAGE
    SESSION_STORAGE = AgentCoreSessionStorage(memory_id, memory_client, actor_id)
    logger.info("✅ Session storage initialized with AgentCore Memory")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_missing_required_fields(session_data: Dict) -> List[str]:
    """Get list of missing required fields from session data"""
    required_fields = session_data.get("required_fields", [])
    current_fields = session_data.get("fields", {})
    return [field for field in required_fields if field not in current_fields]


def _get_completion_status(session_data: Dict) -> Dict[str, Any]:
    """Get completion status from session data"""
    missing_required = _get_missing_required_fields(session_data)
    total_required = len(session_data.get("required_fields", []))
    completed_required = total_required - len(missing_required)
    optional_fields = session_data.get("optional_fields", [])
    completed_optional = len([f for f in optional_fields if f in session_data.get("fields", {})])

    return {
        "required_complete": len(missing_required) == 0,
        "required_progress": f"{completed_required}/{total_required}",
        "optional_progress": f"{completed_optional}/{len(optional_fields)}",
        "missing_required": missing_required,
        "completion_percentage": (completed_required / max(total_required, 1)) * 100
    }


def _regenerate_document_file_from_data(session_data: Dict):
    """
    Regenerate the document file from current session data.

    Args:
        session_data: Session data dictionary
    """
    document_path = session_data.get("document_path")
    if not document_path:
        return

    try:
        # Get template
        doc_type = session_data.get("doc_type")
        template = get_template(doc_type)
        if not template:
            logger.error(f"Template not found for doc_type: {doc_type}")
            return

        # Build complete fields dict
        all_fields_data = {
            "course_code": session_data.get("course_code", "COURSE"),
            "title": session_data.get("title", "Untitled Document")
        }

        # Add all required and optional fields
        current_fields = session_data.get("fields", {})
        for field in template.get("required_fields", []) + template.get("optional_fields", []):
            if field in current_fields:
                all_fields_data[field] = current_fields[field]
            else:
                # Use placeholder for missing fields
                all_fields_data[field] = f"[{field.replace('_', ' ').title()} - TO BE COMPLETED]"

        # Generate content using template
        content = template["structure"].format(**all_fields_data)

        # Write to file
        with open(document_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Regenerated document file: {document_path}")

    except Exception as e:
        logger.error(f"Error regenerating document file: {e}")
        raise


def _generate_pdf_from_markdown(md_path: str, pdf_path: str):
    """
    Generate a PDF file from a markdown file.

    Args:
        md_path: Path to the markdown file
        pdf_path: Path to save the PDF file
    """
    try:
        # Read markdown content
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # Convert markdown to HTML
        html_content = markdown.markdown(
            md_content,
            extensions=['extra', 'nl2br', 'sane_lists']
        )

        # Add basic CSS styling for educational documents
        css_style = """
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: 'Georgia', 'Times New Roman', serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #333;
            }
            h1 {
                font-size: 20pt;
                color: #1a1a1a;
                border-bottom: 2px solid #333;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            h2 {
                font-size: 16pt;
                color: #2a2a2a;
                margin-top: 20px;
                margin-bottom: 10px;
            }
            h3 {
                font-size: 13pt;
                color: #3a3a3a;
            }
            strong {
                font-weight: bold;
            }
            ul, ol {
                margin-left: 20px;
            }
            code {
                background-color: #f4f4f4;
                padding: 2px 4px;
                font-family: 'Courier New', monospace;
            }
            pre {
                background-color: #f4f4f4;
                padding: 10px;
                border-left: 3px solid #ccc;
            }
        </style>
        """

        # Combine HTML with styling
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            {css_style}
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Generate PDF
        HTML(string=full_html).write_pdf(pdf_path)
        logger.info(f"Generated PDF: {pdf_path}")

    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        raise


# ============================================================================
# HELPER TOOLS FOR SUB-AGENTS
# ============================================================================

@tool
def get_session_state() -> str:
    """
    Get the current state of all document sessions from AgentCore Memory.

    Returns:
        JSON string with all session information
    """
    try:
        if SESSION_STORAGE is None:
            return json.dumps({"error": "Session storage not initialized"})

        # Retrieve all sessions from AgentCore Memory
        sessions_dict = SESSION_STORAGE.get_all_sessions()

        if not sessions_dict:
            return json.dumps({"sessions": {}, "count": 0, "latest": None})

        # Find latest session
        latest_session = max(
            sessions_dict.values(),
            key=lambda s: s.get("last_updated", ""),
            default=None
        )

        return json.dumps({
            "sessions": sessions_dict,
            "count": len(sessions_dict),
            "latest_session_id": latest_session.get("session_id") if latest_session else None
        })
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        return json.dumps({"error": str(e)})


@tool
def create_new_session(doc_type: str, course_code: str, title: str) -> str:
    """
    Create a new document session in AgentCore Memory.

    Args:
        doc_type: Document type (syllabus, exam, assignment, lecture, class_content, lab)
        course_code: Course code
        title: Document title

    Returns:
        JSON string with new session information
    """
    try:
        if SESSION_STORAGE is None:
            return json.dumps({"error": "Session storage not initialized"})

        template = get_template(doc_type)
        if not template:
            return json.dumps({"error": f"Unknown document type: {doc_type}"})

        session_id = f"{course_code}_{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Generate filename
        docs_dir = Path("documents")
        docs_dir.mkdir(exist_ok=True)
        filename = generate_filename(course_code, doc_type, title)
        file_path = docs_dir / filename

        # Create session data dictionary
        session_data = {
            "session_id": session_id,
            "doc_type": doc_type,
            "course_code": course_code,
            "title": title,
            "fields": {},
            "template_name": template.get("name", ""),
            "required_fields": template.get("required_fields", []),
            "optional_fields": template.get("optional_fields", []),
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "document_path": str(file_path),
            "pdf_path": None
        }

        # Store in AgentCore Memory
        success = SESSION_STORAGE.create_session(session_data)

        if not success:
            return json.dumps({"error": "Failed to store session in memory"})

        return json.dumps({
            "success": True,
            "session_id": session_id,
            "file_path": str(file_path),
            "template": template,
            "required_fields": template.get("required_fields", []),
            "optional_fields": template.get("optional_fields", [])
        })
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        return json.dumps({"error": str(e)})


@tool
def update_session_field(session_id: str, field_name: str, field_value: str) -> str:
    """
    Update a field in a session (stored in AgentCore Memory) and regenerate the document file.

    Args:
        session_id: Session ID (or "latest")
        field_name: Field name
        field_value: Field value

    Returns:
        JSON string with update status
    """
    try:
        if SESSION_STORAGE is None:
            return json.dumps({"error": "Session storage not initialized"})

        # Get session data
        if session_id == "latest":
            session_data = SESSION_STORAGE.get_latest_session()
            if not session_data:
                return json.dumps({"error": "No sessions available"})
        else:
            session_data = SESSION_STORAGE.get_session(session_id)
            if not session_data:
                return json.dumps({"error": f"Session {session_id} not found"})

        # Validate field name
        all_fields = session_data.get("required_fields", []) + session_data.get("optional_fields", [])
        if field_name not in all_fields:
            return json.dumps({
                "error": f"Field {field_name} not valid",
                "available_fields": all_fields
            })

        # Update session field
        if "fields" not in session_data:
            session_data["fields"] = {}
        session_data["fields"][field_name] = field_value
        session_data["last_updated"] = datetime.now().isoformat()

        # Save updated session to AgentCore Memory
        SESSION_STORAGE.update_session(session_data["session_id"], session_data)

        # Regenerate document file with updated fields
        _regenerate_document_file_from_data(session_data)

        return json.dumps({
            "success": True,
            "session_id": session_data["session_id"],
            "field_name": field_name,
            "field_value": field_value,
            "file_path": session_data.get("document_path"),
            "completion_status": _get_completion_status(session_data)
        })
    except Exception as e:
        logger.error(f"Error updating field: {e}")
        return json.dumps({"error": str(e)})


@tool
def finalize_session(session_id: str = "latest") -> str:
    """
    Finalize a document session (stored in AgentCore Memory).

    Args:
        session_id: Session ID (or "latest")

    Returns:
        JSON string with finalization status
    """
    try:
        if SESSION_STORAGE is None:
            return json.dumps({"error": "Session storage not initialized"})

        # Get session data
        if session_id == "latest":
            session_data = SESSION_STORAGE.get_latest_session()
            if not session_data:
                return json.dumps({"error": "No sessions available"})
        else:
            session_data = SESSION_STORAGE.get_session(session_id)
            if not session_data:
                return json.dumps({"error": f"Session {session_id} not found"})

        # Check completion status
        status = _get_completion_status(session_data)
        if not status['required_complete']:
            return json.dumps({
                "error": "Cannot finalize - missing required fields",
                "missing_fields": status['missing_required']
            })

        # Get template and populate
        doc_type = session_data.get("doc_type")
        template = get_template(doc_type)
        final_content = populate_template(
            template,
            session_data.get("fields", {}),
            session_data.get("course_code"),
            session_data.get("title")
        )

        # Generate final filenames
        final_filename = generate_filename(
            session_data.get("course_code"),
            doc_type,
            session_data.get("title")
        ).replace("_DRAFT", "_FINAL")
        docs_dir = Path("documents")
        final_md_path = docs_dir / final_filename
        final_pdf_path = docs_dir / final_filename.replace(".md", ".pdf")

        # Write the final markdown file
        with open(final_md_path, 'w', encoding='utf-8') as f:
            f.write(final_content)

        # Generate PDF from the markdown file
        _generate_pdf_from_markdown(str(final_md_path), str(final_pdf_path))

        # Update session paths in AgentCore Memory
        session_data["document_path"] = str(final_md_path)
        session_data["pdf_path"] = str(final_pdf_path)
        SESSION_STORAGE.update_session(session_data["session_id"], session_data)

        result = {
            "success": True,
            "session_id": session_data["session_id"],
            "final_content": final_content,
            "md_file_path": str(final_md_path),
            "pdf_file_path": str(final_pdf_path),
            "title": session_data.get("title")
        }

        return json.dumps(result)
    except Exception as e:
        logger.error(f"Error finalizing session: {e}")
        return json.dumps({"error": str(e)})


@tool
def regenerate_document(session_id: str = "latest") -> str:
    """
    Regenerate the document file from current session state (stored in AgentCore Memory).
    Use this to update the file with all current field values.

    Args:
        session_id: Session ID (or "latest")

    Returns:
        JSON string with status
    """
    try:
        if SESSION_STORAGE is None:
            return json.dumps({"error": "Session storage not initialized"})

        # Get session data
        if session_id == "latest":
            session_data = SESSION_STORAGE.get_latest_session()
            if not session_data:
                return json.dumps({"error": "No sessions available"})
        else:
            session_data = SESSION_STORAGE.get_session(session_id)
            if not session_data:
                return json.dumps({"error": f"Session {session_id} not found"})

        _regenerate_document_file_from_data(session_data)

        return json.dumps({
            "success": True,
            "message": "Document file regenerated successfully",
            "file_path": session_data.get("document_path"),
            "fields_updated": len(session_data.get("fields", {}))
        })
    except Exception as e:
        logger.error(f"Error regenerating document: {e}")
        return json.dumps({"error": str(e)})


@tool
def get_template_info() -> str:
    """
    Get information about available templates.

    Returns:
        JSON string with template information
    """
    try:
        types = list_template_types()
        templates_info = {}
        for doc_type in types:
            template = get_template(doc_type)
            if template:
                templates_info[doc_type] = {
                    "name": template.get("name", ""),
                    "required_fields": template.get("required_fields", []),
                    "optional_fields": template.get("optional_fields", [])
                }

        return json.dumps({
            "document_types": list(templates_info.keys()),
            "templates": templates_info
        })
    except Exception as e:
        logger.error(f"Error getting template info: {e}")
        return json.dumps({"error": str(e)})


@tool
def delete_session(session_id: str, delete_files: bool = True) -> str:
    """
    Delete a document session (from AgentCore Memory) and optionally its files.

    Args:
        session_id: Session ID (or "latest")
        delete_files: Whether to delete the document files (default True)

    Returns:
        JSON string with deletion status
    """
    try:
        if SESSION_STORAGE is None:
            return json.dumps({"error": "Session storage not initialized"})

        # Get session data
        if session_id == "latest":
            session_data = SESSION_STORAGE.get_latest_session()
            if not session_data:
                return json.dumps({"error": "No sessions available"})
            session_id = session_data["session_id"]
        else:
            session_data = SESSION_STORAGE.get_session(session_id)
            if not session_data:
                return json.dumps({"error": f"Session {session_id} not found"})

        deleted_files = []
        if delete_files:
            # Delete document file if it exists
            document_path = session_data.get("document_path")
            if document_path:
                result = delete_document(document_path)
                if "Success" in result:
                    deleted_files.append(document_path)
                    # Check if PDF was also deleted
                    if ".pdf" in result:
                        deleted_files.append(document_path.replace(".md", ".pdf"))

        # Delete session from AgentCore Memory
        SESSION_STORAGE.delete_session(session_id)

        return json.dumps({
            "success": True,
            "session_id": session_id,
            "deleted_files": deleted_files,
            "message": f"Session {session_id} deleted successfully"
        })
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return json.dumps({"error": str(e)})


# ============================================================================
# SUB-AGENT TOOLS (AI-Powered with Strands Tools)
# ============================================================================

@tool
def document_creator_agent(user_request: str) -> str:
    """
    AI-powered agent for creating documents from natural language.

    Args:
        user_request: Natural language request

    Returns:
        Response with creation status
    """
    try:
        creator_agent = Agent(
            model=BedrockModel(model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
            tools=[create_new_session, get_template_info, get_session_state, write_document],
            system_prompt="""You are a specialized document creation assistant.

Your workflow:
1. Use get_template_info() to see available document types
2. Parse the user's request to extract: document type, course code, and title
3. Use create_new_session() to create the session - this returns the template and file_path
4. Use write_document(path, content) to create the initial document file
   - Build the initial content using the template structure from the response
   - Fill placeholders like: [Instructor Name - TO BE COMPLETED]
5. Provide friendly feedback with clear next steps

Available document types: syllabus, exam, assignment, lecture, class_content, lab

Be encouraging and concise!"""
        )

        response = creator_agent(user_request)
        return str(response)

    except Exception as e:
        logger.error(f"Error in document creator: {e}")
        return f"❌ Error: {str(e)}"


@tool
def field_editor_agent(field_instruction: str) -> str:
    """
    AI-powered agent for editing document fields.

    Args:
        field_instruction: Natural language field update instruction

    Returns:
        Response with update status
    """
    try:
        editor_agent = Agent(
            model=BedrockModel(model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
            tools=[update_session_field, get_session_state, regenerate_document, read_document],
            system_prompt="""You are a specialized field editing assistant.

Your workflow:
1. Use get_session_state() to see the latest session and its fields
2. Parse the user's instruction to identify field name and value
   Example: "The instructor is Dr. Johnson" → field: instructor_name, value: "Dr. Johnson"
3. Use update_session_field("latest", field_name, value) for EACH field
   - This automatically updates both session state AND the document file
4. For verification, you can use read_document(path) to confirm changes
5. Show concise progress updates

IMPORTANT: update_session_field() automatically regenerates the document file!
Be intelligent about matching phrases to field names!
Keep responses brief and focused."""
        )

        response = editor_agent(field_instruction)
        return str(response)

    except Exception as e:
        logger.error(f"Error in field editor: {e}")
        return f"❌ Error: {str(e)}"


@tool
def document_previewer_agent(preview_request: str) -> str:
    """
    AI-powered agent for previewing documents.

    Args:
        preview_request: Preview request

    Returns:
        Document preview
    """
    try:
        previewer_agent = Agent(
            model=BedrockModel(model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
            tools=[get_session_state, read_document],
            system_prompt="""You are a specialized document preview assistant.

Your workflow:
1. Use get_session_state() to get the latest session
2. Use read_document(path) to read the current document content
3. Show completion status with ✅/❌ icons
4. Display what's complete and what's needed

Be clear, concise and helpful!"""
        )

        response = previewer_agent(preview_request)
        return str(response)

    except Exception as e:
        logger.error(f"Error in previewer: {e}")
        return f"❌ Error: {str(e)}"


@tool
def document_finalizer_agent(finalize_request: str) -> str:
    """
    AI-powered agent for finalizing documents.

    Args:
        finalize_request: Finalization request

    Returns:
        Finalization status
    """
    try:
        finalizer_agent = Agent(
            model=BedrockModel(model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
            tools=[finalize_session, get_session_state],
            system_prompt="""You are a specialized document finalization assistant.

Your workflow:
1. Use get_session_state() to check if all required fields are complete
2. Use finalize_session() - this automatically:
   - Creates the final markdown file
   - Generates a professional PDF with styling
   - Returns both file paths
3. Celebrate with the user!

If not ready:
- Tell them what's missing concisely

If ready:
- Call finalize_session() to generate both MD and PDF
- Show both file paths (markdown and PDF)
- Give a brief congratulations!

IMPORTANT: finalize_session() automatically generates BOTH files - no need to call write_document!
Keep responses concise!"""
        )

        response = finalizer_agent(finalize_request)
        return str(response)

    except Exception as e:
        logger.error(f"Error in finalizer: {e}")
        return f"❌ Error: {str(e)}"


@tool
def session_manager_agent(management_request: str) -> str:
    """
    AI-powered agent for managing sessions.

    Args:
        management_request: Session management request

    Returns:
        Session information
    """
    try:
        manager_agent = Agent(
            model=BedrockModel(model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
            tools=[get_session_state, delete_session],
            system_prompt="""You are a specialized session management assistant.

Your workflow:
1. Use get_session_state() to get all sessions
2. Parse the user's request (list all, search, delete, etc.)
3. Present information clearly

When listing:
- Show progress percentages
- Highlight ready-to-finalize sessions
- Be organized and helpful!

When deleting:
- Use delete_session(session_id, delete_files=True) to delete a session
- Confirm which session was deleted and which files were removed
- "latest" refers to the most recently updated session

Be concise and clear in responses!"""
        )

        response = manager_agent(management_request)
        return str(response)

    except Exception as e:
        logger.error(f"Error in session manager: {e}")
        return f"❌ Error: {str(e)}"
