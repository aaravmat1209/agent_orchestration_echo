"""Utility functions for the Video Agent."""
import json
import logging
import boto3

logger = logging.getLogger(__name__)


def get_ssm_parameter(name: str) -> str:
    """Retrieve a parameter from AWS Systems Manager Parameter Store."""
    try:
        ssm = boto3.client("ssm")
        response = ssm.get_parameter(Name=name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception as e:
        logger.error(f"Failed to get SSM parameter {name}: {e}")
        raise


def get_aws_info():
    """Get AWS account ID and region."""
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
        region = boto3.session.Session().region_name or "us-west-2"
        return account_id, region
    except Exception as e:
        logger.error(f"Failed to get AWS info: {e}")
        raise
