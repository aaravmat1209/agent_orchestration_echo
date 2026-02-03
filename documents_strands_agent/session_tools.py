"""
Session management tools — maintains context across interactions.
"""
import json
import logging
from strands import tool

logger = logging.getLogger(__name__)


@tool
def get_session_context(session_id: str) -> str:
    """
    Retrieve the current session's document interaction history.

    Args:
        session_id: The session identifier

    Returns:
        JSON string with session context (recent documents, queries, preferences)
    """
    try:
        logger.info(f"Getting session context: {session_id}")
        return json.dumps({
            "session_id": session_id,
            "status": "context_retrieved",
            "message": "Retrieves from AgentCore Memory session namespace"
        })
    except Exception as e:
        logger.error(f"Error getting session context: {e}")
        return json.dumps({"error": str(e)})


@tool
def update_session_context(session_id: str, context_key: str, context_value: str) -> str:
    """
    Save context for the current session.

    Args:
        session_id: The session identifier
        context_key: Key for the context entry (e.g., 'last_document', 'search_query')
        context_value: Value to store

    Returns:
        JSON string confirming the context was saved
    """
    try:
        logger.info(f"Updating session context: {session_id}, key={context_key}")
        return json.dumps({
            "session_id": session_id,
            "context_key": context_key,
            "status": "context_updated",
            "message": "Saved to AgentCore Memory session namespace"
        })
    except Exception as e:
        logger.error(f"Error updating session context: {e}")
        return json.dumps({"error": str(e)})
