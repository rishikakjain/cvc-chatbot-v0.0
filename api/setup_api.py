"""
Provision Phase 3 AWS infrastructure:
  - DynamoDB table: cvc_sessions
  - Lambda function: cvc-chatbot-session-handler
  - API Gateway HTTP API: cvc-chatbot-api
  - S3 bucket for frontend hosting

Run after setup_agent.py (reads .env.agent for agent IDs).

    python api/setup_api.py

Appends to .env.agent with the API Gateway URL and S3 bucket name.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import boto3

AWS_REGION = os.environ.get("AWS_REGION", "us-west-2")
PROJECT_ROOT = Path(__file__).parent.parent
ENV_AGENT_PATH = PROJECT_ROOT / ".env.agent"

DYNAMO_TABLE = "cvc_sessions"
LAMBDA_NAME = "cvc-chatbot-session-handler"
API_NAME = "cvc-chatbot-api"
IAM_ROLE_NAME = "cvc-chatbot-bedrock-role"  # reuse role from setup_agent.py


def read_env_agent() -> dict:
    if not ENV_AGENT_PATH.exists():
        print("ERROR: .env.agent not found. Run agent/setup_agent.py first.")
        sys.exit(1)
    env = {}
    for line in ENV_AGENT_PATH.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def append_env_agent(**kwargs) -> None:
    existing = ENV_AGENT_PATH.read_text() if ENV_AGENT_PATH.exists() else ""
    lines = existing.rstrip("\n") + "\n"
    for k, v in kwargs.items():
        lines += f"{k}={v}\n"
    ENV_AGENT_PATH.write_text(lines)


def ensure_dynamo_table(dynamo) -> None:
    try:
        dynamo.describe_table(TableName=DYNAMO_TABLE)
        print(f"  DynamoDB table already exists: {DYNAMO_TABLE}")
        return
    except dynamo.exceptions.ResourceNotFoundException:
        pass

    dynamo.create_table(
        TableName=DYNAMO_TABLE,
        AttributeDefinitions=[{"AttributeName": "session_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "session_id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )
    print(f"  Created DynamoDB table: {DYNAMO_TABLE}")

    # Wait for table to become ACTIVE before enabling TTL
    import time
    for _ in range(12):
        resp = dynamo.describe_table(TableName=DYNAMO_TABLE)
        if resp["Table"]["TableStatus"] == "ACTIVE":
            break
        print("  Waiting for table to become ACTIVE...")
        time.sleep(5)

    # Enable TTL
    dynamo.update_time_to_live(
        TableName=DYNAMO_TABLE,
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
    )
    print("  Enabled TTL on 'ttl' attribute")


def build_session_lambda_zip() -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name

    with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(PROJECT_ROOT / "api" / "session_handler.py", "session_handler.py")
        # Bundle tools + data — session handler runs the tool loop directly
        for py_file in (PROJECT_ROOT / "tools").glob("*.py"):
            zf.write(py_file, f"tools/{py_file.name}")
        courses_json = PROJECT_ROOT / "data" / "courses.json"
        if courses_json.exists():
            zf.write(courses_json, "data/courses.json")
        # Bundle system prompt
        system_prompt = PROJECT_ROOT / "agent" / "system_prompt.txt"
        if system_prompt.exists():
            zf.write(system_prompt, "agent/system_prompt.txt")

    with open(tmp_path, "rb") as f:
        data = f.read()
    os.unlink(tmp_path)
    return data


def deploy_session_lambda(lambda_client, role_arn: str, env_vars: dict) -> str:
    zip_bytes = build_session_lambda_zip()

    env = {
        "BEDROCK_MODEL_ID": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
        "DYNAMODB_TABLE": DYNAMO_TABLE,
        "APP_REGION": AWS_REGION,
    }
    guardrail_id = os.environ.get("BEDROCK_GUARDRAIL_ID")
    if guardrail_id:
        env["BEDROCK_GUARDRAIL_ID"] = guardrail_id

    try:
        resp = lambda_client.get_function(FunctionName=LAMBDA_NAME)
        print(f"  Updating existing Lambda: {LAMBDA_NAME}")
        lambda_client.update_function_code(FunctionName=LAMBDA_NAME, ZipFile=zip_bytes)
        waiter = lambda_client.get_waiter("function_updated_v2")
        waiter.wait(FunctionName=LAMBDA_NAME)
        lambda_client.update_function_configuration(
            FunctionName=LAMBDA_NAME,
            Environment={"Variables": env},
        )
        waiter.wait(FunctionName=LAMBDA_NAME)
        return resp["Configuration"]["FunctionArn"]
    except lambda_client.exceptions.ResourceNotFoundException:
        pass

    resp = lambda_client.create_function(
        FunctionName=LAMBDA_NAME,
        Runtime="python3.12",
        Role=role_arn,
        Handler="session_handler.lambda_handler",
        Code={"ZipFile": zip_bytes},
        Description="CVC chatbot session handler — bridges API Gateway to Bedrock Agent",
        Timeout=60,
        MemorySize=256,
        Environment={"Variables": env},
    )
    fn_arn = resp["FunctionArn"]
    print(f"  Created Lambda: {LAMBDA_NAME} ({fn_arn})")
    return fn_arn


def allow_apigw_invoke(lambda_client, fn_arn: str, api_id: str, account_id: str) -> None:
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_NAME,
            StatementId="apigw-invoke",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com",
            SourceArn=f"arn:aws:execute-api:{AWS_REGION}:{account_id}:{api_id}/*/*/chat",
        )
        print("  Added API Gateway invoke permission to session Lambda")
    except lambda_client.exceptions.ResourceConflictException:
        print("  API Gateway invoke permission already exists")


def deploy_api_gateway(apigw, fn_arn: str) -> str:
    """Create or update an HTTP API with a POST /chat route."""
    # Check if API already exists
    resp = apigw.get_apis()
    for api in resp.get("Items", []):
        if api["Name"] == API_NAME:
            api_id = api["ApiId"]
            api_url = api["ApiEndpoint"]
            print(f"  Using existing API Gateway: {API_NAME} ({api_id})")
            return api_id, api_url

    # Create the HTTP API
    resp = apigw.create_api(
        Name=API_NAME,
        ProtocolType="HTTP",
        CorsConfiguration={
            "AllowOrigins": ["*"],
            "AllowMethods": ["POST", "OPTIONS"],
            "AllowHeaders": ["Content-Type", "X-Session-Id"],
            "MaxAge": 300,
        },
    )
    api_id = resp["ApiId"]
    api_url = resp["ApiEndpoint"]
    print(f"  Created HTTP API: {API_NAME} ({api_id})")

    # Integration → Lambda
    integration_resp = apigw.create_integration(
        ApiId=api_id,
        IntegrationType="AWS_PROXY",
        IntegrationUri=fn_arn,
        PayloadFormatVersion="2.0",
    )
    integration_id = integration_resp["IntegrationId"]

    # Route: POST /chat
    apigw.create_route(
        ApiId=api_id,
        RouteKey="POST /chat",
        Target=f"integrations/{integration_id}",
    )

    # Default stage with auto-deploy
    apigw.create_stage(
        ApiId=api_id,
        StageName="$default",
        AutoDeploy=True,
    )
    print(f"  Created POST /chat route → {api_url}/chat")

    return api_id, api_url


def ensure_s3_bucket(s3, account_id: str) -> str:
    bucket_name = f"cvc-chatbot-frontend-{account_id}"

    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"  S3 bucket already exists: {bucket_name}")
        return bucket_name
    except Exception:
        pass

    if AWS_REGION == "us-east-1":
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )
    print(f"  Created S3 bucket: {bucket_name}")

    # Must remove public access block BEFORE setting a public bucket policy
    s3.delete_public_access_block(Bucket=bucket_name)

    # Enable static website hosting
    s3.put_bucket_website(
        Bucket=bucket_name,
        WebsiteConfiguration={
            "IndexDocument": {"Suffix": "index.html"},
            "ErrorDocument": {"Key": "index.html"},
        },
    )

    # Public read policy
    s3.put_bucket_policy(
        Bucket=bucket_name,
        Policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
            }],
        }),
    )
    print(f"  Configured static website hosting on {bucket_name}")
    return bucket_name


def main() -> None:
    env_vars = read_env_agent()

    session = boto3.Session(region_name=AWS_REGION)
    sts = session.client("sts")
    dynamo = session.client("dynamodb")
    lambda_client = session.client("lambda")
    apigw = session.client("apigatewayv2")
    s3 = session.client("s3")
    iam = session.client("iam")

    account_id = sts.get_caller_identity()["Account"]
    print(f"\nAWS account: {account_id} | region: {AWS_REGION}\n")

    role_arn = iam.get_role(RoleName=IAM_ROLE_NAME)["Role"]["Arn"]

    # Add DynamoDB permissions to the existing role
    iam.put_role_policy(
        RoleName=IAM_ROLE_NAME,
        PolicyName="cvc-dynamo-sessions",
        PolicyDocument=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                ],
                "Resource": f"arn:aws:dynamodb:{AWS_REGION}:{account_id}:table/{DYNAMO_TABLE}",
            }],
        }),
    )

    print("1. DynamoDB")
    ensure_dynamo_table(dynamo)

    print("\n2. Session Lambda")
    fn_arn = deploy_session_lambda(lambda_client, role_arn, env_vars)

    print("\n3. API Gateway")
    api_id, api_url = deploy_api_gateway(apigw, fn_arn)
    allow_apigw_invoke(lambda_client, fn_arn, api_id, account_id)

    print("\n4. S3 frontend bucket")
    bucket_name = ensure_s3_bucket(s3, account_id)

    append_env_agent(
        API_URL=api_url,
        S3_BUCKET=bucket_name,
        DYNAMODB_TABLE=DYNAMO_TABLE,
    )

    print(f"""
Setup complete!

  API endpoint:  {api_url}/chat
  S3 bucket:     {bucket_name}
  DynamoDB:      {DYNAMO_TABLE}

Next: build and deploy the frontend
  cd frontend
  npm install
  npm run build
  aws s3 sync dist/ s3://{bucket_name}/

Frontend URL (S3 static site):
  http://{bucket_name}.s3-website-{AWS_REGION}.amazonaws.com
""")


if __name__ == "__main__":
    main()
