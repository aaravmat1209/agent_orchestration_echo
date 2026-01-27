#!/usr/bin/env python3
"""Get M2M token for the Video Agent."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from shared_utils import get_m2m_token_for_agent

if __name__ == "__main__":
    get_m2m_token_for_agent(
        ssm_runtime_id_param="/videoagent/agentcore/runtime-id",
        agent_name="Video Agent",
    )
