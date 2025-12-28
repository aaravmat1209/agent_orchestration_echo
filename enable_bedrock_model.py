#!/usr/bin/env python3
"""
Simple script to invoke Bedrock model once to enable it for the account.
This triggers the auto-enablement for serverless foundation models.
"""

import json
import boto3
from botocore.exceptions import ClientError

def enable_bedrock_model():
    """Invoke the Bedrock model to enable it for the account."""

    model_id = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
    region = "us-west-2"

    print(f"Attempting to invoke model: {model_id}")
    print(f"Region: {region}")

    # Create Bedrock Runtime client
    bedrock_runtime = boto3.client(
        service_name="bedrock-runtime",
        region_name=region
    )

    # Prepare minimal request payload
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10,
        "messages": [
            {
                "role": "user",
                "content": "Hi"
            }
        ]
    }

    try:
        # Invoke the model
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )

        # Read the response
        response_body = json.loads(response['body'].read())

        print("\n✓ Success! Model invoked successfully.")
        print(f"Response: {json.dumps(response_body, indent=2)}")
        print("\nThe model is now enabled for your account.")
        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        print(f"\n✗ Error invoking model:")
        print(f"Error Code: {error_code}")
        print(f"Error Message: {error_message}")

        if "AccessDeniedException" in error_code:
            print("\nThis might require first-time user approval from AWS.")
            print("You may need to visit the Bedrock console or contact AWS support.")

        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    enable_bedrock_model()
