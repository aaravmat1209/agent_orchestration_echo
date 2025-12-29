"""
Document manipulation tools for Echo Ink Agent
S3-based persistent storage with session isolation
"""
import logging
from typing import Optional
from strands import tool
from document_storage import DocumentStorageManager

logger = logging.getLogger(__name__)

# Global session_id - will be set when agent is initialized
_current_session_id: Optional[str] = None


def set_session_id(session_id: str):
    """Set the current session ID for document operations"""
    global _current_session_id
    _current_session_id = session_id
    logger.info(f"Document tools session ID set to: {session_id}")


def get_storage_manager() -> DocumentStorageManager:
    """Get the document storage manager for the current session"""
    if not _current_session_id:
        raise ValueError("Session ID not set. Call set_session_id() first.")
    return DocumentStorageManager(_current_session_id)


@tool
def read_document(doc_id: str) -> str:
    """
    Read a document from S3 storage.

    Args:
        doc_id: Document identifier (e.g., "quiz_CSE401", "lesson_plan_001")

    Returns:
        Document content as markdown string, or error message
    """
    try:
        storage = get_storage_manager()
        doc_data = storage.load_document(doc_id)

        if not doc_data:
            return f"Error: Document '{doc_id}' not found in session storage"

        content = doc_data['content']
        metadata = doc_data.get('metadata', {})

        logger.info(f"Loaded document {doc_id} (type: {metadata.get('doc_type', 'unknown')})")
        return content

    except Exception as e:
        logger.error(f"Error reading document {doc_id}: {e}")
        return f"Error reading document: {str(e)}"


@tool
def write_document(doc_id: str, content: str, doc_type: str = "document") -> str:
    """
    Write a document to S3 storage.

    Args:
        doc_id: Document identifier
        content: Document content in markdown format
        doc_type: Type of document (quiz, lesson_plan, syllabus, etc.)

    Returns:
        Success message or error
    """
    try:
        storage = get_storage_manager()
        success = storage.save_document(
            doc_id=doc_id,
            content=content,
            doc_type=doc_type
        )

        if success:
            logger.info(f"Saved document {doc_id} to S3")
            return f"✅ Success: Document '{doc_id}' saved to persistent storage"
        else:
            return f"Error: Failed to save document '{doc_id}'"

    except Exception as e:
        logger.error(f"Error writing document {doc_id}: {e}")
        return f"Error writing document: {str(e)}"


@tool
def update_document(doc_id: str, old_text: str, new_text: str) -> str:
    """
    Update a document by replacing text.

    Args:
        doc_id: Document identifier
        old_text: Text to find and replace
        new_text: New text to insert

    Returns:
        Success message or error
    """
    try:
        storage = get_storage_manager()

        # Load current document
        doc_data = storage.load_document(doc_id)
        if not doc_data:
            return f"Error: Document '{doc_id}' not found"

        content = doc_data['content']

        # Check if old_text exists
        if old_text not in content:
            return f"Error: Could not find text to replace in '{doc_id}'"

        # Replace text
        updated_content = content.replace(old_text, new_text)

        # Save updated document
        success = storage.update_document(doc_id, updated_content)

        if success:
            logger.info(f"Updated document {doc_id}")
            return f"✅ Success: Updated document '{doc_id}'"
        else:
            return f"Error: Failed to update document '{doc_id}'"

    except Exception as e:
        logger.error(f"Error updating document {doc_id}: {e}")
        return f"Error updating document: {str(e)}"


@tool
def update_document_field(doc_id: str, field_name: str, new_value: str) -> str:
    """
    Update a specific field in a structured document.

    This searches for a field marker (e.g., "**Field Name:**") and replaces its value.

    Args:
        doc_id: Document identifier
        field_name: Name of the field to update (case-insensitive)
        new_value: New value for the field

    Returns:
        Success message or error
    """
    try:
        storage = get_storage_manager()

        # Load current document
        doc_data = storage.load_document(doc_id)
        if not doc_data:
            return f"Error: Document '{doc_id}' not found"

        content = doc_data['content']

        # Try different field formats
        patterns = [
            f"**{field_name}:**",
            f"**{field_name.title()}:**",
            f"## {field_name}",
            f"### {field_name}",
        ]

        updated = False
        for pattern in patterns:
            if pattern in content:
                # Find the field and replace the value after it
                lines = content.split('\n')
                new_lines = []

                for i, line in enumerate(lines):
                    if pattern in line:
                        # Replace the value on this line or the next line
                        if ':' in line:
                            # Value on same line: "**Field:** old_value"
                            new_lines.append(f"{pattern} {new_value}")
                        else:
                            # Value on next line
                            new_lines.append(line)
                            if i + 1 < len(lines):
                                new_lines.append(new_value)
                                lines.pop(i + 1)  # Skip the old value line
                        updated = True
                    else:
                        new_lines.append(line)

                if updated:
                    updated_content = '\n'.join(new_lines)
                    success = storage.update_document(doc_id, updated_content)

                    if success:
                        logger.info(f"Updated field '{field_name}' in document {doc_id}")
                        return f"✅ Success: Updated field '{field_name}' in '{doc_id}'"
                    else:
                        return f"Error: Failed to save updated document"

        if not updated:
            return f"Error: Field '{field_name}' not found in document '{doc_id}'"

    except Exception as e:
        logger.error(f"Error updating field in {doc_id}: {e}")
        return f"Error updating field: {str(e)}"


@tool
def delete_document(doc_id: str) -> str:
    """
    Delete a document from S3 storage.

    Args:
        doc_id: Document identifier

    Returns:
        Success message or error
    """
    try:
        storage = get_storage_manager()
        success = storage.delete_document(doc_id)

        if success:
            logger.info(f"Deleted document {doc_id}")
            return f"✅ Success: Deleted document '{doc_id}'"
        else:
            return f"Error: Failed to delete document '{doc_id}'"

    except Exception as e:
        logger.error(f"Error deleting document {doc_id}: {e}")
        return f"Error deleting document: {str(e)}"


@tool
def list_documents() -> str:
    """
    List all documents in the current session.

    Returns:
        Formatted list of documents with metadata
    """
    try:
        storage = get_storage_manager()
        documents = storage.list_documents()

        if not documents:
            return "📄 No documents found in this session yet."

        # Format document list
        doc_list = ["📚 **Documents in this session:**\n"]
        for i, doc in enumerate(documents, 1):
            doc_id = doc.get('doc_id', 'unknown')
            doc_type = doc.get('doc_type', 'unknown')
            created = doc.get('created_at', 'unknown')

            doc_list.append(f"{i}. **{doc_id}** ({doc_type}) - created {created}")

        return "\n".join(doc_list)

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return f"Error listing documents: {str(e)}"


@tool
def save_document_pdf(doc_id: str, pdf_content: bytes) -> str:
    """
    Save a PDF version of a document.

    Args:
        doc_id: Document identifier
        pdf_content: PDF binary content

    Returns:
        Success message with download URL or error
    """
    try:
        storage = get_storage_manager()
        success = storage.save_pdf(doc_id, pdf_content)

        if success:
            # Get presigned URL for PDF
            pdf_url = storage.get_pdf_url(doc_id)

            if pdf_url:
                logger.info(f"Saved PDF for {doc_id}")
                return f"✅ Success: PDF saved. Download: {pdf_url}"
            else:
                return f"✅ Success: PDF saved (URL generation failed)"
        else:
            return f"Error: Failed to save PDF for '{doc_id}'"

    except Exception as e:
        logger.error(f"Error saving PDF for {doc_id}: {e}")
        return f"Error saving PDF: {str(e)}"


@tool
def get_document_pdf_url(doc_id: str) -> str:
    """
    Get a download URL for a document's PDF.

    Args:
        doc_id: Document identifier

    Returns:
        Presigned URL or error message
    """
    try:
        storage = get_storage_manager()
        pdf_url = storage.get_pdf_url(doc_id)

        if pdf_url:
            return f"📥 PDF download URL (valid for 1 hour): {pdf_url}"
        else:
            return f"Error: PDF not found for document '{doc_id}'"

    except Exception as e:
        logger.error(f"Error getting PDF URL for {doc_id}: {e}")
        return f"Error getting PDF URL: {str(e)}"
