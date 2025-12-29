"""
Document Storage Manager for EchoInk Agent
Handles S3 operations for document persistence and retrieval
"""

import boto3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Get AWS configuration
ACCOUNT_ID = boto3.client('sts').get_caller_identity()['Account']
BUCKET_NAME = f"echo-docs-{ACCOUNT_ID}"
REGION = os.getenv("AWS_REGION", "us-west-2")

class DocumentStorageManager:
    """Manages document storage and retrieval in S3"""

    def __init__(self, session_id: str):
        """
        Initialize document storage manager

        Args:
            session_id: Unique session identifier for document isolation
        """
        self.session_id = session_id
        self.s3_client = boto3.client('s3', region_name=REGION)
        self.bucket_name = BUCKET_NAME
        self.session_prefix = f"sessions/{session_id}"

    def _get_document_key(self, doc_id: str, extension: str) -> str:
        """Generate S3 key for a document"""
        return f"{self.session_prefix}/documents/{doc_id}.{extension}"

    def _get_metadata_key(self, doc_id: str) -> str:
        """Generate S3 key for document metadata"""
        return f"{self.session_prefix}/documents/{doc_id}_metadata.json"

    def save_document(self, doc_id: str, content: str, doc_type: str,
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a document to S3

        Args:
            doc_id: Unique document identifier
            content: Document content (markdown)
            doc_type: Type of document (quiz, lesson_plan, syllabus, etc.)
            metadata: Additional document metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Save markdown content
            md_key = self._get_document_key(doc_id, "md")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=md_key,
                Body=content.encode('utf-8'),
                ContentType='text/markdown',
                Metadata={
                    'session-id': self.session_id,
                    'doc-type': doc_type,
                    'created-at': datetime.utcnow().isoformat()
                }
            )

            # Save metadata
            if metadata is None:
                metadata = {}

            metadata.update({
                'doc_id': doc_id,
                'doc_type': doc_type,
                'session_id': self.session_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })

            metadata_key = self._get_metadata_key(doc_id)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2).encode('utf-8'),
                ContentType='application/json'
            )

            logger.info(f"Saved document {doc_id} to S3: {md_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to save document {doc_id}: {e}")
            return False

    def load_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a document from S3

        Args:
            doc_id: Document identifier

        Returns:
            Dict with 'content' and 'metadata' keys, or None if not found
        """
        try:
            # Load markdown content
            md_key = self._get_document_key(doc_id, "md")
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=md_key
            )
            content = response['Body'].read().decode('utf-8')

            # Load metadata
            metadata_key = self._get_metadata_key(doc_id)
            try:
                metadata_response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=metadata_key
                )
                metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
            except:
                metadata = {}

            logger.info(f"Loaded document {doc_id} from S3")
            return {
                'content': content,
                'metadata': metadata
            }

        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"Document {doc_id} not found in S3")
            return None
        except Exception as e:
            logger.error(f"Failed to load document {doc_id}: {e}")
            return None

    def update_document(self, doc_id: str, content: str,
                       metadata_updates: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing document

        Args:
            doc_id: Document identifier
            content: Updated content
            metadata_updates: Metadata fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing metadata
            existing = self.load_document(doc_id)
            if not existing:
                logger.error(f"Cannot update non-existent document {doc_id}")
                return False

            metadata = existing['metadata']
            if metadata_updates:
                metadata.update(metadata_updates)
            metadata['updated_at'] = datetime.utcnow().isoformat()

            # Save updated document
            return self.save_document(
                doc_id=doc_id,
                content=content,
                doc_type=metadata.get('doc_type', 'unknown'),
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document from S3

        Args:
            doc_id: Document identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete markdown file
            md_key = self._get_document_key(doc_id, "md")
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=md_key
            )

            # Delete PDF if exists
            pdf_key = self._get_document_key(doc_id, "pdf")
            try:
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=pdf_key
                )
            except:
                pass

            # Delete metadata
            metadata_key = self._get_metadata_key(doc_id)
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=metadata_key
            )

            logger.info(f"Deleted document {doc_id} from S3")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in the current session

        Returns:
            List of document metadata dictionaries
        """
        try:
            prefix = f"{self.session_prefix}/documents/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            documents = []
            if 'Contents' in response:
                # Get only metadata files
                for obj in response['Contents']:
                    if obj['Key'].endswith('_metadata.json'):
                        try:
                            metadata_response = self.s3_client.get_object(
                                Bucket=self.bucket_name,
                                Key=obj['Key']
                            )
                            metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
                            documents.append(metadata)
                        except Exception as e:
                            logger.warning(f"Failed to load metadata from {obj['Key']}: {e}")

            logger.info(f"Found {len(documents)} documents in session {self.session_id}")
            return documents

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            return []

    def save_pdf(self, doc_id: str, pdf_content: bytes) -> bool:
        """
        Save PDF version of a document

        Args:
            doc_id: Document identifier
            pdf_content: PDF binary content

        Returns:
            True if successful, False otherwise
        """
        try:
            pdf_key = self._get_document_key(doc_id, "pdf")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=pdf_key,
                Body=pdf_content,
                ContentType='application/pdf',
                Metadata={
                    'session-id': self.session_id,
                    'doc-id': doc_id
                }
            )

            logger.info(f"Saved PDF for document {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save PDF for {doc_id}: {e}")
            return False

    def get_pdf_url(self, doc_id: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for PDF download

        Args:
            doc_id: Document identifier
            expiration: URL expiration time in seconds (default 1 hour)

        Returns:
            Presigned URL or None if PDF doesn't exist
        """
        try:
            pdf_key = self._get_document_key(doc_id, "pdf")

            # Check if PDF exists
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=pdf_key
            )

            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': pdf_key
                },
                ExpiresIn=expiration
            )

            logger.info(f"Generated presigned URL for {doc_id} PDF")
            return url

        except self.s3_client.exceptions.ClientError:
            logger.warning(f"PDF not found for document {doc_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {doc_id}: {e}")
            return None
