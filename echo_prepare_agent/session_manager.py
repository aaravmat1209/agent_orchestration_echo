"""
Session Manager for EchoInk Agent
Handles session state persistence and retrieval
"""

import boto3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Get AWS configuration
ACCOUNT_ID = boto3.client('sts').get_caller_identity()['Account']
BUCKET_NAME = f"echo-docs-{ACCOUNT_ID}"
REGION = os.getenv("AWS_REGION", "us-west-2")


class SessionManager:
    """Manages session state in S3"""

    def __init__(self, session_id: str):
        """
        Initialize session manager

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.s3_client = boto3.client('s3', region_name=REGION)
        self.bucket_name = BUCKET_NAME
        self.state_key = f"sessions/{session_id}/state.json"

    def save_state(self, state: Dict[str, Any]) -> bool:
        """
        Save session state to S3

        Args:
            state: Session state dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add metadata
            state['session_id'] = self.session_id
            state['updated_at'] = datetime.utcnow().isoformat()

            if 'created_at' not in state:
                state['created_at'] = datetime.utcnow().isoformat()

            # Save to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=self.state_key,
                Body=json.dumps(state, indent=2).encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'session-id': self.session_id,
                    'updated-at': state['updated_at']
                }
            )

            logger.info(f"Saved session state for {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save session state: {e}")
            return False

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load session state from S3

        Returns:
            Session state dictionary or None if not found
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=self.state_key
            )
            state = json.loads(response['Body'].read().decode('utf-8'))

            logger.info(f"Loaded session state for {self.session_id}")
            return state

        except self.s3_client.exceptions.NoSuchKey:
            logger.info(f"No existing session state for {self.session_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to load session state: {e}")
            return None

    def update_state(self, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in session state

        Args:
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing state or create new one
            state = self.load_state() or {}

            # Update fields
            state.update(updates)

            # Save updated state
            return self.save_state(state)

        except Exception as e:
            logger.error(f"Failed to update session state: {e}")
            return False

    def delete_state(self) -> bool:
        """
        Delete session state from S3

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=self.state_key
            )

            logger.info(f"Deleted session state for {self.session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session state: {e}")
            return False

    def get_current_document(self) -> Optional[str]:
        """
        Get the current document ID from session state

        Returns:
            Document ID or None
        """
        state = self.load_state()
        if state:
            return state.get('current_document')
        return None

    def set_current_document(self, doc_id: str) -> bool:
        """
        Set the current document in session state

        Args:
            doc_id: Document identifier

        Returns:
            True if successful, False otherwise
        """
        return self.update_state({'current_document': doc_id})

    def add_document_to_history(self, doc_id: str, doc_type: str, title: str) -> bool:
        """
        Add a document to the session's document history

        Args:
            doc_id: Document identifier
            doc_type: Type of document
            title: Document title

        Returns:
            True if successful, False otherwise
        """
        try:
            state = self.load_state() or {}

            if 'documents' not in state:
                state['documents'] = []

            # Check if document already exists
            existing = [d for d in state['documents'] if d.get('id') == doc_id]
            if existing:
                # Update existing entry
                for doc in state['documents']:
                    if doc.get('id') == doc_id:
                        doc['title'] = title
                        doc['updated_at'] = datetime.utcnow().isoformat()
            else:
                # Add new entry
                state['documents'].append({
                    'id': doc_id,
                    'type': doc_type,
                    'title': title,
                    'created_at': datetime.utcnow().isoformat()
                })

            return self.save_state(state)

        except Exception as e:
            logger.error(f"Failed to add document to history: {e}")
            return False

    def get_document_history(self) -> list:
        """
        Get list of all documents in session

        Returns:
            List of document metadata dictionaries
        """
        state = self.load_state()
        if state and 'documents' in state:
            return state['documents']
        return []

    def set_user_preferences(self, preferences: Dict[str, Any]) -> bool:
        """
        Save user preferences to session state

        Args:
            preferences: Dictionary of user preferences

        Returns:
            True if successful, False otherwise
        """
        return self.update_state({'preferences': preferences})

    def get_user_preferences(self) -> Dict[str, Any]:
        """
        Get user preferences from session state

        Returns:
            Dictionary of user preferences
        """
        state = self.load_state()
        if state and 'preferences' in state:
            return state['preferences']
        return {}
