"""
Provision the CVC chatbot Bedrock Agent.

Run once (or re-run to update) from your local machine:
    python agent/setup_agent.py

Requires:
    pip install boto3
    AWS credentials with bedrock:* and iam:* permissions in your environment

The script creates (or updates):
    1. An IAM role the Bedrock Agent uses to invoke Lambda
    2. A Lambda function from agent/lambda_handler.py + tools/
    3. A Bedrock Agent with the system prompt
    4. An action group wiring the three tools to the Lambda function

Outputs IDs to .env.agent (do NOT commit this file).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import boto3

# ── Configuration ────────────────────────────────────────────────────────────

AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
AGENT_NAME = "cvc-chatbot-v0"
LAMBDA_FUNCTION_NAME = "cvc-chatbot-tools"
IAM_ROLE_NAME = "cvc-chatbot-bedrock-role"

PROJECT_ROOT = Path(__file__).parent.parent
SYSTEM_PROMPT_PATH = PROJECT_ROOT / "agent" / "system_prompt.txt"
LAMBDA_HANDLER_PATH = PROJECT_ROOT / "agent" / "lambda_handler.py"
TOOLS_DIR = PROJECT_ROOT / "tools"
DATA_DIR = PROJECT_ROOT / "data"

# Bedrock requires a foundation model ID for the agent
# Claude Haiku 4.5 for the agent orchestration; tool calls are cheap
FOUNDATION_MODEL = "anthropic.claude-haiku-4-5-20251001"

# ── Action group schema ───────────────────────────────────────────────────────

ACTION_GROUP_SCHEMA = {
    "openapi": "3.0.0",
    "info": {"title": "CVC Course Tools", "version": "1.0"},
    "paths": {
        "/filter_courses": {
            "post": {
                "operationId": "filter_courses",
                "summary": "Search for CVC online courses matching GE area and delivery preferences",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "ge_areas": {
                                        "type": "string",
                                        "description": "Comma-separated GE area codes to match (e.g. 'B2,5B'). Leave empty to return all subjects.",
                                    },
                                    "delivery_method": {
                                        "type": "string",
                                        "enum": ["async", "sync"],
                                        "description": "Filter by delivery: 'async' (no meeting times) or 'sync' (live sessions). Omit for no filter.",
                                    },
                                    "exclude_college": {
                                        "type": "string",
                                        "description": "Exact name of the student's home college to exclude from results.",
                                    },
                                    "start_after": {
                                        "type": "string",
                                        "description": "ISO date (YYYY-MM-DD). Exclude courses starting before this date.",
                                    },
                                    "has_seats": {
                                        "type": "boolean",
                                        "description": "If true (default), only return courses with available seats.",
                                        "default": True,
                                    },
                                    "top_n": {
                                        "type": "integer",
                                        "description": "Maximum number of results to return (default 10).",
                                        "default": 10,
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "List of matching courses",
                        "content": {
                            "application/json": {
                                "schema": {"type": "array", "items": {"type": "object"}}
                            }
                        },
                    }
                },
            }
        },
        "/explain_ge_area": {
            "post": {
                "operationId": "explain_ge_area",
                "summary": "Explain a GE area code or plain-language subject (e.g. 'B2', '5B', 'science lab', 'what is IGETC')",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["query"],
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "A GE area code (e.g. 'B2'), plain-language phrase ('science lab'), or framework name ('IGETC').",
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "GE area explanation",
                        "content": {
                            "application/json": {"schema": {"type": "object"}}
                        },
                    }
                },
            }
        },
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────


def build_lambda_zip() -> bytes:
    """Package lambda_handler.py + tools/ + data/ into a ZIP for Lambda deployment."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # agent/lambda_handler.py → lambda_handler.py (at root of package)
        zf.write(LAMBDA_HANDLER_PATH, "lambda_handler.py")

        # tools/*.py
        for py_file in TOOLS_DIR.glob("*.py"):
            zf.write(py_file, f"tools/{py_file.name}")

        # data/courses.json
        courses_json = DATA_DIR / "courses.json"
        if courses_json.exists():
            zf.write(courses_json, "data/courses.json")

    with open(tmp_path, "rb") as f:
        data = f.read()

    os.unlink(tmp_path)
    return data


def get_or_create_iam_role(iam, account_id: str) -> str:
    """Return ARN of the IAM role, creating it if needed."""
    try:
        resp = iam.get_role(RoleName=IAM_ROLE_NAME)
        print(f"  IAM role already exists: {IAM_ROLE_NAME}")
        return resp["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        pass

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": ["bedrock.amazonaws.com", "lambda.amazonaws.com"]
                },
                "Action": "sts:AssumeRole",
            }
        ],
    }

    resp = iam.create_role(
        RoleName=IAM_ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="CVC chatbot Bedrock Agent + Lambda execution role",
    )
    role_arn = resp["Role"]["Arn"]
    print(f"  Created IAM role: {IAM_ROLE_NAME} ({role_arn})")

    # Attach managed policies
    for policy_arn in [
        "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        "arn:aws:iam::aws:policy/AmazonBedrockFullAccess",
    ]:
        iam.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn=policy_arn)

    # Inline policy: Lambda invoke permission for Bedrock
    iam.put_role_policy(
        RoleName=IAM_ROLE_NAME,
        PolicyName="cvc-bedrock-lambda-invoke",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "lambda:InvokeFunction",
                    "Resource": f"arn:aws:lambda:{AWS_REGION}:{account_id}:function:{LAMBDA_FUNCTION_NAME}",
                }
            ],
        }),
    )

    import time
    print("  Waiting 10s for IAM role propagation...")
    time.sleep(10)
    return role_arn


def deploy_lambda(lambda_client, role_arn: str) -> str:
    """Deploy or update the Lambda function. Returns the function ARN."""
    zip_bytes = build_lambda_zip()
    print(f"  Built Lambda package: {len(zip_bytes):,} bytes")

    try:
        resp = lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
        print(f"  Updating existing Lambda: {LAMBDA_FUNCTION_NAME}")
        lambda_client.update_function_code(
            FunctionName=LAMBDA_FUNCTION_NAME,
            ZipFile=zip_bytes,
        )
        return resp["Configuration"]["FunctionArn"]
    except lambda_client.exceptions.ResourceNotFoundException:
        pass

    resp = lambda_client.create_function(
        FunctionName=LAMBDA_FUNCTION_NAME,
        Runtime="python3.12",
        Role=role_arn,
        Handler="lambda_handler.lambda_handler",
        Code={"ZipFile": zip_bytes},
        Description="CVC chatbot tool handler for Bedrock Agent",
        Timeout=30,
        MemorySize=256,
    )
    fn_arn = resp["FunctionArn"]
    print(f"  Created Lambda: {LAMBDA_FUNCTION_NAME} ({fn_arn})")
    return fn_arn


def add_bedrock_permission(lambda_client, fn_arn: str, account_id: str) -> None:
    """Allow Bedrock to invoke the Lambda function."""
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_FUNCTION_NAME,
            StatementId="bedrock-agent-invoke",
            Action="lambda:InvokeFunction",
            Principal="bedrock.amazonaws.com",
            SourceArn=f"arn:aws:bedrock:{AWS_REGION}:{account_id}:agent/*",
        )
        print("  Added Bedrock invoke permission to Lambda")
    except lambda_client.exceptions.ResourceConflictException:
        print("  Bedrock invoke permission already exists")


def get_or_create_agent(bedrock_agent, role_arn: str) -> str:
    """Return agent ID, creating if needed."""
    system_prompt = SYSTEM_PROMPT_PATH.read_text()

    # Check if agent already exists by listing and matching name
    paginator = bedrock_agent.get_paginator("list_agents")
    for page in paginator.paginate():
        for agent in page.get("agentSummaries", []):
            if agent["agentName"] == AGENT_NAME:
                agent_id = agent["agentId"]
                print(f"  Updating existing agent: {AGENT_NAME} ({agent_id})")
                bedrock_agent.update_agent(
                    agentId=agent_id,
                    agentName=AGENT_NAME,
                    agentResourceRoleArn=role_arn,
                    foundationModel=FOUNDATION_MODEL,
                    instruction=system_prompt,
                )
                return agent_id

    resp = bedrock_agent.create_agent(
        agentName=AGENT_NAME,
        agentResourceRoleArn=role_arn,
        foundationModel=FOUNDATION_MODEL,
        instruction=system_prompt,
        description="CVC online course finder and transfer advisor",
    )
    agent_id = resp["agent"]["agentId"]
    print(f"  Created agent: {AGENT_NAME} ({agent_id})")
    return agent_id


def setup_action_group(bedrock_agent, agent_id: str, lambda_arn: str) -> None:
    """Create or update the action group with the OpenAPI schema."""
    action_group_name = "cvc-tools"
    schema_json = json.dumps(ACTION_GROUP_SCHEMA)

    # Check if action group exists
    resp = bedrock_agent.list_agent_action_groups(agentId=agent_id, agentVersion="DRAFT")
    existing = {ag["actionGroupName"]: ag["actionGroupId"] for ag in resp.get("actionGroupSummaries", [])}

    if action_group_name in existing:
        print(f"  Updating action group: {action_group_name}")
        bedrock_agent.update_agent_action_group(
            agentId=agent_id,
            agentVersion="DRAFT",
            actionGroupId=existing[action_group_name],
            actionGroupName=action_group_name,
            actionGroupExecutor={"lambda": lambda_arn},
            apiSchema={"payload": schema_json},
            actionGroupState="ENABLED",
        )
    else:
        print(f"  Creating action group: {action_group_name}")
        bedrock_agent.create_agent_action_group(
            agentId=agent_id,
            agentVersion="DRAFT",
            actionGroupName=action_group_name,
            actionGroupExecutor={"lambda": lambda_arn},
            apiSchema={"payload": schema_json},
            actionGroupState="ENABLED",
        )


def prepare_agent(bedrock_agent, agent_id: str) -> str:
    """Prepare the agent (compile/validate) and return the agent version."""
    print("  Preparing agent (this takes ~15–30s)...")
    bedrock_agent.prepare_agent(agentId=agent_id)

    import time
    for _ in range(12):
        time.sleep(5)
        resp = bedrock_agent.get_agent(agentId=agent_id)
        status = resp["agent"]["agentStatus"]
        print(f"    Agent status: {status}")
        if status == "PREPARED":
            return "DRAFT"
        if status in ("FAILED", "CREATION_FAILED"):
            raise RuntimeError(f"Agent preparation failed: {resp['agent']}")

    raise TimeoutError("Agent did not reach PREPARED state within 60s")


def create_agent_alias(bedrock_agent, agent_id: str) -> str:
    """Create (or reuse) a 'live' alias pointing to DRAFT."""
    resp = bedrock_agent.list_agent_aliases(agentId=agent_id)
    for alias in resp.get("agentAliasSummaries", []):
        if alias["agentAliasName"] == "live":
            alias_id = alias["agentAliasId"]
            print(f"  Using existing alias 'live' ({alias_id})")
            return alias_id

    resp = bedrock_agent.create_agent_alias(
        agentId=agent_id,
        agentAliasName="live",
        description="Default alias for CVC chatbot",
    )
    alias_id = resp["agentAlias"]["agentAliasId"]
    print(f"  Created alias 'live' ({alias_id})")
    return alias_id


def write_env_agent(agent_id: str, alias_id: str, lambda_arn: str) -> None:
    """Write agent IDs to .env.agent so they can be used by a frontend."""
    env_path = PROJECT_ROOT / ".env.agent"
    env_path.write_text(
        f"BEDROCK_AGENT_ID={agent_id}\n"
        f"BEDROCK_AGENT_ALIAS_ID={alias_id}\n"
        f"LAMBDA_ARN={lambda_arn}\n"
        f"AWS_REGION={AWS_REGION}\n"
    )
    print(f"\n  Wrote agent config to {env_path.name} (do not commit this file)")


# ── Main ──────────────────────────────────────────────────────────────────────


def add_bedrock_runtime_permission(iam, account_id: str) -> None:
    """Allow Lambda to invoke Claude via Bedrock Runtime (Converse API)."""
    iam.put_role_policy(
        RoleName=IAM_ROLE_NAME,
        PolicyName="cvc-bedrock-runtime-invoke",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                ],
                "Resource": f"arn:aws:bedrock:{AWS_REGION}::foundation-model/*",
            }],
        }),
    )
    print("  Added Bedrock Runtime invoke permission to role")


def write_env_agent_simple(lambda_arn: str) -> None:
    env_path = PROJECT_ROOT / ".env.agent"
    env_path.write_text(
        f"LAMBDA_ARN={lambda_arn}\n"
        f"AWS_REGION={AWS_REGION}\n"
    )
    print(f"\n  Wrote config to {env_path.name}")


def main() -> None:
    session = boto3.Session(region_name=AWS_REGION)
    sts = session.client("sts")
    iam = session.client("iam")
    lambda_client = session.client("lambda")

    account_id = sts.get_caller_identity()["Account"]
    print(f"\nAWS account: {account_id} | region: {AWS_REGION}\n")

    print("1. IAM role")
    role_arn = get_or_create_iam_role(iam, account_id)
    add_bedrock_runtime_permission(iam, account_id)

    print("\n2. Lambda function (tools)")
    lambda_arn = deploy_lambda(lambda_client, role_arn)

    write_env_agent_simple(lambda_arn)

    print(f"""
Setup complete!

  Tools Lambda: {lambda_arn}

Next: run  python3 api/setup_api.py
""")


if __name__ == "__main__":
    main()
