"""
Session Storage using AWS Bedrock AgentCore Memory
Replaces in-memory DOCUMENT_SESSIONS dictionary with persistent storage
"""
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from bedrock_agentcore.memory import MemoryClient

logger = logging.getLogger(__name__)


class AgentCoreSessionStorage:
    """Manages document sessions using AgentCore Memory for persistence"""

    def __init__(self, memory_id: str, memory_client: MemoryClient, actor_id: str):
        self.memory_id = memory_id
        self.client = memory_client
        self.actor_id = actor_id
        self.namespace = f"/document-sessions/{actor_id}"

    def create_session(self, session_data: Dict) -> bool:
        """
        Create a new document session in AgentCore memory.

        Args:
            session_data: Dictionary containing session information

        Returns:
            True if successful, False otherwise
        """
        try:
            session_id = session_data.get("session_id")

            # Store session as a memory event with session metadata
            # Using create_event with a special format for session data
            result = self.client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=session_id,
                messages=[
                    (
                        f"SESSION_DATA: {json.dumps(session_data)}",
                        "SYSTEM"
                    )
                ],
            )

            logger.info(f"✅ Created session {session_id} in AgentCore memory")
            return True

        except Exception as e:
            logger.error(f"Failed to create session in AgentCore memory: {e}")
            return False

    def get_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve a specific session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            Session data dictionary or None if not found
        """
        try:
            # Retrieve session data using the session_id
            # Get recent turns for this specific session
            turns = self.client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=session_id,
                k=100,  # Get enough turns to find the session data
            )

            # Search through turns for SESSION_DATA messages
            for turn in turns:
                for message in turn:
                    if message.get("role") == "SYSTEM":
                        content = message.get("content", {}).get("text", "")
                        if content.startswith("SESSION_DATA: "):
                            session_json = content.replace("SESSION_DATA: ", "")
                            return json.loads(session_json)

            logger.warning(f"Session {session_id} not found in AgentCore memory")
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve session from AgentCore memory: {e}")
            return None

    def get_all_sessions(self) -> Dict[str, Dict]:
        """
        Retrieve all sessions for the current actor.

        Returns:
            Dictionary mapping session_id to session data
        """
        try:
            # Retrieve all memories from the document-sessions namespace
            memories = self.client.retrieve_memories(
                memory_id=self.memory_id,
                namespace=self.namespace,
                query="document session",  # Broad query to get all sessions
                top_k=100,  # Retrieve up to 100 sessions
            )

            sessions = {}
            for memory in memories:
                content = memory.get("content", {})
                if isinstance(content, dict):
                    text = content.get("text", "")
                elif isinstance(content, str):
                    text = content
                else:
                    continue

                # Parse session data from memory content
                if "SESSION_DATA: " in text:
                    try:
                        session_json = text.split("SESSION_DATA: ", 1)[1]
                        session_data = json.loads(session_json)
                        session_id = session_data.get("session_id")
                        if session_id:
                            sessions[session_id] = session_data
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse session data from memory")
                        continue

            logger.info(f"Retrieved {len(sessions)} sessions from AgentCore memory")
            return sessions

        except Exception as e:
            logger.error(f"Failed to retrieve all sessions: {e}")
            return {}

    def update_session(self, session_id: str, session_data: Dict) -> bool:
        """
        Update an existing session (creates a new version).

        Args:
            session_id: Session ID to update
            session_data: Updated session data

        Returns:
            True if successful, False otherwise
        """
        try:
            # AgentCore memory is append-only, so we create a new event
            # with updated data. When retrieving, we'll get the latest version.
            session_data["last_updated"] = datetime.now().isoformat()

            result = self.client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=session_id,
                messages=[
                    (
                        f"SESSION_DATA: {json.dumps(session_data)}",
                        "SYSTEM"
                    )
                ],
            )

            logger.info(f"✅ Updated session {session_id} in AgentCore memory")
            return True

        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        Mark a session as deleted (soft delete).

        Args:
            session_id: Session ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # AgentCore memory doesn't support hard deletes
            # We'll mark it as deleted by storing a deletion marker
            deletion_marker = {
                "session_id": session_id,
                "deleted": True,
                "deleted_at": datetime.now().isoformat()
            }

            result = self.client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=session_id,
                messages=[
                    (
                        f"SESSION_DELETED: {json.dumps(deletion_marker)}",
                        "SYSTEM"
                    )
                ],
            )

            logger.info(f"✅ Marked session {session_id} as deleted in AgentCore memory")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False

    def get_latest_session(self) -> Optional[Dict]:
        """
        Get the most recently updated session.

        Returns:
            Latest session data or None
        """
        sessions = self.get_all_sessions()
        if not sessions:
            return None

        # Find session with most recent last_updated timestamp
        latest_session = max(
            sessions.values(),
            key=lambda s: s.get("last_updated", ""),
            default=None
        )

        return latest_session
