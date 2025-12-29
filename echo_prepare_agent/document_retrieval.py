"""
Document Retrieval Tools for EchoPrepare Agent
Read-only access to instructor-created study materials from S3
"""
import boto3
import json
import os
import logging
from typing import Optional, Dict, Any, List
from strands import tool

logger = logging.getLogger(__name__)

# Get AWS configuration
ACCOUNT_ID = boto3.client('sts').get_caller_identity()['Account']
BUCKET_NAME = f"echo-docs-{ACCOUNT_ID}"
REGION = os.getenv("AWS_REGION", "us-west-2")

# Global session_id - will be set when agent is initialized
_current_session_id: Optional[str] = None
_s3_client = None


def set_session_id(session_id: str):
    """Set the current session ID for document retrieval"""
    global _current_session_id, _s3_client
    _current_session_id = session_id
    _s3_client = boto3.client('s3', region_name=REGION)
    logger.info(f"Document retrieval session ID set to: {session_id}")


def _load_document(doc_id: str) -> Optional[Dict[str, Any]]:
    """Load a document from S3 (internal helper)"""
    if not _current_session_id or not _s3_client:
        raise ValueError("Session ID not set. Call set_session_id() first.")

    try:
        session_prefix = f"sessions/{_current_session_id}"
        md_key = f"{session_prefix}/documents/{doc_id}.md"

        # Load markdown content
        response = _s3_client.get_object(Bucket=BUCKET_NAME, Key=md_key)
        content = response['Body'].read().decode('utf-8')

        # Load metadata
        metadata_key = f"{session_prefix}/documents/{doc_id}_metadata.json"
        try:
            metadata_response = _s3_client.get_object(Bucket=BUCKET_NAME, Key=metadata_key)
            metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
        except:
            metadata = {}

        return {'content': content, 'metadata': metadata}
    except _s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logger.error(f"Error loading document {doc_id}: {e}")
        return None


def _list_documents() -> List[Dict[str, Any]]:
    """List all documents in the current session (internal helper)"""
    if not _current_session_id or not _s3_client:
        raise ValueError("Session ID not set. Call set_session_id() first.")

    try:
        session_prefix = f"sessions/{_current_session_id}"
        prefix = f"{session_prefix}/documents/"

        response = _s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)

        documents = []
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'].endswith('_metadata.json'):
                    try:
                        metadata_response = _s3_client.get_object(Bucket=BUCKET_NAME, Key=obj['Key'])
                        metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
                        documents.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata from {obj['Key']}: {e}")

        return documents
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []


@tool
def list_study_materials(doc_type: Optional[str] = None) -> str:
    """
    List all available study materials (quizzes, tests, syllabi, lesson plans).
    Students can see all materials created by instructors in their course.

    Args:
        doc_type: Filter by document type (quiz, syllabus, lesson_plan, test).
                 Leave empty to see all materials.

    Returns:
        Formatted list of available study materials with titles and types

    Example:
        list_study_materials("quiz") - Show only quizzes
        list_study_materials() - Show all materials
    """
    try:
        documents = _list_documents()

        if not documents:
            return "📚 No study materials available yet. Check back after your instructor creates course content!"

        # Filter by type if specified
        if doc_type:
            documents = [d for d in documents if d.get('doc_type', '').lower() == doc_type.lower()]
            if not documents:
                return f"📚 No {doc_type} materials found. Available types: quiz, syllabus, lesson_plan, test"

        # Format document list for students
        doc_list = ["📚 **Available Study Materials:**\n"]

        # Group by type for better organization
        by_type = {}
        for doc in documents:
            dtype = doc.get('doc_type', 'other')
            if dtype not in by_type:
                by_type[dtype] = []
            by_type[dtype].append(doc)

        # Display grouped by type
        for dtype, docs in sorted(by_type.items()):
            doc_list.append(f"\n**{dtype.upper()}:**")
            for i, doc in enumerate(docs, 1):
                doc_id = doc.get('doc_id', 'unknown')
                title = doc.get('title', doc_id)
                created = doc.get('created_at', 'unknown')

                # Emoji based on type
                emoji = "📝" if dtype == "quiz" else "📄" if dtype == "test" else "📋"
                doc_list.append(f"  {emoji} {i}. **{title}** (ID: `{doc_id}`) - created {created[:10]}")

        doc_list.append(f"\n💡 **Tip:** Use `view_study_material('doc_id')` to read the full content!")

        return "\n".join(doc_list)

    except Exception as e:
        logger.error(f"Error listing study materials: {e}")
        return f"❌ Error accessing study materials: {str(e)}"


@tool
def view_study_material(doc_id: str) -> str:
    """
    View the full content of a study material (quiz, test, syllabus, etc.).
    This gives you the complete document to study from.

    Args:
        doc_id: Document identifier from the materials list
                (e.g., "quiz_CSE401", "syllabus_MAT343")

    Returns:
        Full document content in markdown format

    Example:
        view_study_material("quiz_CSE401") - Read the CSE401 quiz
    """
    try:
        doc_data = _load_document(doc_id)

        if not doc_data:
            return f"❌ Document '{doc_id}' not found. Use `list_study_materials()` to see available materials."

        content = doc_data['content']
        metadata = doc_data.get('metadata', {})
        doc_type = metadata.get('doc_type', 'document')

        # Add helpful header
        header = f"# 📖 Study Material: {doc_id}\n"
        header += f"**Type:** {doc_type.title()}\n"
        header += f"**Created:** {metadata.get('created_at', 'N/A')[:10]}\n"
        header += f"\n---\n\n"

        logger.info(f"Student viewed study material: {doc_id} (type: {doc_type})")
        return header + content

    except Exception as e:
        logger.error(f"Error viewing study material {doc_id}: {e}")
        return f"❌ Error accessing document: {str(e)}"


@tool
def search_study_materials(query: str) -> str:
    """
    Search study materials by keyword (searches titles and content).
    Helpful for finding specific topics or subjects across all materials.

    Args:
        query: Search keyword (e.g., "photosynthesis", "Civil War", "recursion")

    Returns:
        List of matching study materials with relevance

    Example:
        search_study_materials("photosynthesis") - Find all materials about photosynthesis
    """
    try:
        documents = _list_documents()

        if not documents:
            return "📚 No study materials available to search."

        query_lower = query.lower()
        matches = []

        # Search in titles and metadata
        for doc in documents:
            doc_id = doc.get('doc_id', '')
            title = doc.get('title', '')
            doc_type = doc.get('doc_type', '')

            # Check if query matches
            if (query_lower in doc_id.lower() or
                query_lower in title.lower() or
                query_lower in doc_type.lower()):
                matches.append(doc)

        if not matches:
            return f"🔍 No materials found matching '{query}'. Try different keywords or use `list_study_materials()` to see all materials."

        # Format results
        result = [f"🔍 **Found {len(matches)} material(s) matching '{query}':**\n"]

        for i, doc in enumerate(matches, 1):
            doc_id = doc.get('doc_id', 'unknown')
            title = doc.get('title', doc_id)
            doc_type = doc.get('doc_type', 'other')

            emoji = "📝" if doc_type == "quiz" else "📄" if doc_type == "test" else "📋"
            result.append(f"{emoji} {i}. **{title}** ({doc_type}) - ID: `{doc_id}`")

        result.append(f"\n💡 Use `view_study_material('doc_id')` to read the full content!")

        logger.info(f"Search for '{query}' returned {len(matches)} results")
        return "\n".join(result)

    except Exception as e:
        logger.error(f"Error searching study materials: {e}")
        return f"❌ Error searching: {str(e)}"


@tool
def get_material_summary(doc_id: str) -> str:
    """
    Get a quick summary of a study material without viewing the full content.
    Shows key info like type, topics covered, and when it was created.

    Args:
        doc_id: Document identifier

    Returns:
        Summary with metadata and key information

    Example:
        get_material_summary("quiz_CSE401") - Get quick info about the quiz
    """
    try:
        doc_data = _load_document(doc_id)

        if not doc_data:
            return f"❌ Document '{doc_id}' not found."

        metadata = doc_data.get('metadata', {})
        content = doc_data['content']

        # Extract summary info
        doc_type = metadata.get('doc_type', 'document')
        created = metadata.get('created_at', 'N/A')[:10]
        updated = metadata.get('updated_at', 'N/A')[:10]

        # Count questions/sections (rough estimate)
        num_lines = len(content.split('\n'))
        num_sections = content.count('##')

        summary = f"📋 **Summary: {doc_id}**\n\n"
        summary += f"**Type:** {doc_type.title()}\n"
        summary += f"**Created:** {created}\n"
        summary += f"**Last Updated:** {updated}\n"
        summary += f"**Sections:** ~{num_sections}\n"
        summary += f"**Length:** {num_lines} lines\n\n"
        summary += f"💡 Use `view_study_material('{doc_id}')` to see the full content."

        logger.info(f"Generated summary for {doc_id}")
        return summary

    except Exception as e:
        logger.error(f"Error getting material summary {doc_id}: {e}")
        return f"❌ Error: {str(e)}"


def get_document_retrieval_tools():
    """
    Get all document retrieval tools for EchoPrepare agent.
    These are READ-ONLY tools for viewing instructor-created materials.
    """
    return [
        list_study_materials,
        view_study_material,
        search_study_materials,
        get_material_summary,
    ]
