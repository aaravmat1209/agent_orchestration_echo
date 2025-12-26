"""
Document manipulation tools for Echo Ink Agent
Simple, autonomous file operations without confirmations
"""
import logging
from pathlib import Path
from strands import tool

logger = logging.getLogger(__name__)


@tool
def read_document(file_path: str) -> str:
    """
    Read a document file.

    Args:
        file_path: Path to the file to read

    Returns:
        File contents as string
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        return content
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return f"Error reading file: {str(e)}"


@tool
def write_document(file_path: str, content: str) -> str:
    """
    Write content to a document file.

    Args:
        file_path: Path to the file to write
        content: Content to write to the file

    Returns:
        Success message or error
    """
    try:
        path = Path(file_path)
        # Create parent directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        return f"Success: File written to {file_path}"
    except Exception as e:
        logger.error(f"Error writing file {file_path}: {e}")
        return f"Error writing file: {str(e)}"


@tool
def update_document(file_path: str, old_text: str, new_text: str) -> str:
    """
    Update a document by replacing old text with new text.

    Args:
        file_path: Path to the file to update
        old_text: Text to find and replace
        new_text: New text to insert

    Returns:
        Success message or error
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        # Read current content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if old_text exists
        if old_text not in content:
            return f"Error: Could not find text to replace in {file_path}"

        # Replace text
        updated_content = content.replace(old_text, new_text)

        # Write back
        with open(path, 'w', encoding='utf-8') as f:
            f.write(updated_content)

        return f"Success: Updated {file_path}"
    except Exception as e:
        logger.error(f"Error updating file {file_path}: {e}")
        return f"Error updating file: {str(e)}"


@tool
def delete_document(file_path: str) -> str:
    """
    Delete a document file.

    Args:
        file_path: Path to the file to delete

    Returns:
        Success message or error
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        # Delete the file
        path.unlink()

        # Also delete PDF if it exists
        pdf_path = path.with_suffix('.pdf')
        if pdf_path.exists():
            pdf_path.unlink()
            return f"Success: Deleted {file_path} and {pdf_path}"

        return f"Success: Deleted {file_path}"
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return f"Error deleting file: {str(e)}"
