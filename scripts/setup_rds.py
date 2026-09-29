"""
Provision Aurora Serverless v2 PostgreSQL for the CVC chatbot.

What this script creates:
  1. VPC (10.0.0.0/16) with DNS resolution enabled
  2. Internet Gateway attached to VPC
  3. 1 public subnet (10.0.0.0/24, us-west-2a) for NAT Gateway
  4. 2 private subnets (10.0.1.0/24 us-west-2a, 10.0.2.0/24 us-west-2b) for Aurora + Lambda
  5. NAT Gateway in the public subnet (Lambda → Bedrock/DynamoDB/Secrets Manager)
  6. Route tables (public: IGW, private: NAT GW)
  7. Security group for Lambda (outbound 443 + 5432)
  8. Security group for Aurora (inbound 5432 from Lambda SG)
  9. DB Subnet Group (private subnets)
 10. Aurora Serverless v2 cluster (PostgreSQL 15, min 0.5 ACU, max 4 ACU)
 11. Secrets Manager secret with DB credentials
 12. IAM: attach VPC execution + Secrets Manager + RDS permissions to Lambda role
 13. Update Lambda VPC config (private subnets + Lambda SG)
 14. Update Lambda env vars (SECRET_ARN, DB_NAME, DB_HOST)

Writes outputs to .env.agent.

Prerequisites:
  - AWS credentials configured (aws configure or IAM role)
  - .env.agent must exist (run api/setup_api.py first)
  - psycopg2-binary installed (pip install psycopg2-binary)

Usage:
    python scripts/setup_rds.py

After this script completes, run:
    SECRET_ARN=<value> DB_HOST=<value> python data/migrate_to_postgres.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import boto3

AWS_REGION   = os.environ.get("AWS_REGION", "us-west-2")
PROJECT_ROOT = Path(__file__).parent.parent
ENV_AGENT    = PROJECT_ROOT / ".env.agent"

LAMBDA_NAME    = "cvc-chatbot-session-handler"
IAM_ROLE_NAME  = "cvc-chatbot-bedrock-role"
DB_NAME        = "cvcdb"
DB_MASTER_USER = "cvcadmin"
CLUSTER_ID     = "cvc-chatbot-aurora"
SECRET_NAME    = "cvc-chatbot/db-credentials"
VPC_CIDR       = "10.0.0.0/16"

AZS = [f"{AWS_REGION}a", f"{AWS_REGION}b"]
PUBLIC_CIDR   = "10.0.0.0/24"
PRIVATE_CIDRS = ["10.0.1.0/24", "10.0.2.0/24"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def read_env() -> dict:
    if not ENV_AGENT.exists():
        print("ERROR: .env.agent not found. Run api/setup_api.py first.")
        sys.exit(1)
    env: dict = {}
    for line in ENV_AGENT.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def append_env(**kwargs) -> None:
    existing = ENV_AGENT.read_text() if ENV_AGENT.exists() else ""
    lines = existing.rstrip("\n") + "\n"
    for k, v in kwargs.items():
        lines += f"{k}={v}\n"
    ENV_AGENT.write_text(lines)


def tag(name: str) -> list[dict]:
    return [{"Key": "Project", "Value": "cvc-chatbot"}, {"Key": "Name", "Value": name}]


def wait(msg: str, fn, *args, interval=10, max_attempts=60, **kw):
    """Poll fn(*args, **kw) until it doesn't raise, returning its result."""
    print(f"  Waiting: {msg}", end="", flush=True)
    for _ in range(max_attempts):
        try:
            result = fn(*args, **kw)
            print(" ✓")
            return result
        except Exception:
            print(".", end="", flush=True)
            time.sleep(interval)
    print(" TIMEOUT")
    raise TimeoutError(f"Timed out waiting for: {msg}")


# ── Step 1–6: VPC, subnets, routing ──────────────────────────────────────────

def setup_vpc(ec2) -> dict:
    """Create (or reuse) VPC with public and private subnets + NAT GW."""
    # Reuse if already tagged
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "tag:Project", "Values": ["cvc-chatbot"]}])["Vpcs"]
    if vpcs:
        vpc_id = vpcs[0]["VpcId"]
        print(f"  Reusing existing VPC: {vpc_id}")
        existing = _collect_existing_vpc_resources(ec2, vpc_id)
        return existing

    print("  Creating VPC …")
    vpc = ec2.create_vpc(CidrBlock=VPC_CIDR, TagSpecifications=[{
        "ResourceType": "vpc", "Tags": tag("cvc-chatbot-vpc")
    }])["Vpc"]
    vpc_id = vpc["VpcId"]
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsResolution={"Value": True})
    ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={"Value": True})
    print(f"  VPC: {vpc_id}")

    # Internet Gateway
    igw = ec2.create_internet_gateway(TagSpecifications=[{
        "ResourceType": "internet-gateway", "Tags": tag("cvc-chatbot-igw")
    }])["InternetGateway"]
    igw_id = igw["InternetGatewayId"]
    ec2.attach_internet_gateway(InternetGatewayId=igw_id, VpcId=vpc_id)
    print(f"  IGW: {igw_id}")

    # Public subnet (for NAT GW)
    pub_subnet = ec2.create_subnet(
        VpcId=vpc_id, CidrBlock=PUBLIC_CIDR, AvailabilityZone=AZS[0],
        TagSpecifications=[{"ResourceType": "subnet", "Tags": tag("cvc-chatbot-public")}]
    )["Subnet"]
    pub_subnet_id = pub_subnet["SubnetId"]
    ec2.modify_subnet_attribute(SubnetId=pub_subnet_id, MapPublicIpOnLaunch={"Value": True})

    # Public route table
    pub_rt = ec2.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[{"ResourceType": "route-table", "Tags": tag("cvc-chatbot-rt-public")}]
    )["RouteTable"]
    pub_rt_id = pub_rt["RouteTableId"]
    ec2.create_route(RouteTableId=pub_rt_id, DestinationCidrBlock="0.0.0.0/0", GatewayId=igw_id)
    ec2.associate_route_table(SubnetId=pub_subnet_id, RouteTableId=pub_rt_id)

    # Elastic IP + NAT Gateway
    eip = ec2.allocate_address(Domain="vpc")
    eip_alloc = eip["AllocationId"]
    nat_gw = ec2.create_nat_gateway(
        SubnetId=pub_subnet_id, AllocationId=eip_alloc,
        TagSpecifications=[{"ResourceType": "natgateway", "Tags": tag("cvc-chatbot-nat")}]
    )["NatGateway"]
    nat_gw_id = nat_gw["NatGatewayId"]

    # Wait for NAT GW
    def _nat_available():
        state = ec2.describe_nat_gateways(NatGatewayIds=[nat_gw_id])["NatGateways"][0]["State"]
        if state != "available":
            raise RuntimeError(state)
        return nat_gw_id
    wait("NAT Gateway available", _nat_available)

    # Private subnets
    priv_subnet_ids = []
    for i, cidr in enumerate(PRIVATE_CIDRS):
        sn = ec2.create_subnet(
            VpcId=vpc_id, CidrBlock=cidr, AvailabilityZone=AZS[i],
            TagSpecifications=[{"ResourceType": "subnet", "Tags": tag(f"cvc-chatbot-private-{i+1}")}]
        )["Subnet"]
        priv_subnet_ids.append(sn["SubnetId"])

    # Private route table (0.0.0.0/0 → NAT GW)
    priv_rt = ec2.create_route_table(
        VpcId=vpc_id,
        TagSpecifications=[{"ResourceType": "route-table", "Tags": tag("cvc-chatbot-rt-private")}]
    )["RouteTable"]
    priv_rt_id = priv_rt["RouteTableId"]
    ec2.create_route(RouteTableId=priv_rt_id, DestinationCidrBlock="0.0.0.0/0", NatGatewayId=nat_gw_id)
    for sn_id in priv_subnet_ids:
        ec2.associate_route_table(SubnetId=sn_id, RouteTableId=priv_rt_id)

    print(f"  Private subnets: {priv_subnet_ids}")
    return {
        "vpc_id": vpc_id,
        "private_subnet_ids": priv_subnet_ids,
        "public_subnet_id": pub_subnet_id,
    }


def _collect_existing_vpc_resources(ec2, vpc_id: str) -> dict:
    """Find private subnets and public subnet from an existing tagged VPC."""
    subnets = ec2.describe_subnets(Filters=[
        {"Name": "vpc-id", "Values": [vpc_id]},
        {"Name": "tag:Project", "Values": ["cvc-chatbot"]},
    ])["Subnets"]
    private_ids = [s["SubnetId"] for s in subnets if "private" in
                   " ".join(t["Value"] for t in s.get("Tags", []))]
    public_ids  = [s["SubnetId"] for s in subnets if "public" in
                   " ".join(t["Value"] for t in s.get("Tags", []))]
    return {
        "vpc_id": vpc_id,
        "private_subnet_ids": private_ids,
        "public_subnet_id": public_ids[0] if public_ids else None,
    }


# ── Step 7–8: Security Groups ─────────────────────────────────────────────────

def setup_security_groups(ec2, vpc_id: str) -> tuple[str, str]:
    """Returns (lambda_sg_id, rds_sg_id)."""
    # Lambda SG
    existing = ec2.describe_security_groups(Filters=[
        {"Name": "group-name", "Values": ["cvc-chatbot-lambda-sg"]},
        {"Name": "vpc-id", "Values": [vpc_id]},
    ])["SecurityGroups"]
    if existing:
        lambda_sg_id = existing[0]["GroupId"]
        print(f"  Reusing Lambda SG: {lambda_sg_id}")
    else:
        lambda_sg = ec2.create_security_group(
            GroupName="cvc-chatbot-lambda-sg",
            Description="Lambda function outbound",
            VpcId=vpc_id,
            TagSpecifications=[{"ResourceType": "security-group", "Tags": tag("cvc-chatbot-lambda-sg")}],
        )
        lambda_sg_id = lambda_sg["GroupId"]
        # Lambda needs outbound HTTPS (Bedrock, DynamoDB, Secrets Manager) + PostgreSQL
        ec2.authorize_security_group_egress(
            GroupId=lambda_sg_id,
            IpPermissions=[
                {"IpProtocol": "tcp", "FromPort": 443,  "ToPort": 443,  "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
                {"IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            ],
        )
        print(f"  Created Lambda SG: {lambda_sg_id}")

    # RDS SG
    existing = ec2.describe_security_groups(Filters=[
        {"Name": "group-name", "Values": ["cvc-chatbot-rds-sg"]},
        {"Name": "vpc-id", "Values": [vpc_id]},
    ])["SecurityGroups"]
    if existing:
        rds_sg_id = existing[0]["GroupId"]
        print(f"  Reusing RDS SG: {rds_sg_id}")
    else:
        rds_sg = ec2.create_security_group(
            GroupName="cvc-chatbot-rds-sg",
            Description="Aurora inbound from Lambda",
            VpcId=vpc_id,
            TagSpecifications=[{"ResourceType": "security-group", "Tags": tag("cvc-chatbot-rds-sg")}],
        )
        rds_sg_id = rds_sg["GroupId"]
        ec2.authorize_security_group_ingress(
            GroupId=rds_sg_id,
            IpPermissions=[{
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "UserIdGroupPairs": [{"GroupId": lambda_sg_id}],
            }],
        )
        print(f"  Created RDS SG: {rds_sg_id}")

    return lambda_sg_id, rds_sg_id


# ── Step 9–10: DB Subnet Group + Aurora Cluster ───────────────────────────────

def setup_aurora(rds, private_subnet_ids: list[str], rds_sg_id: str) -> dict:
    """Create Aurora Serverless v2 PostgreSQL cluster. Returns cluster info."""
    import secrets as _secrets
    subnet_group_name = "cvc-chatbot-db-subnet-group"

    # DB Subnet Group
    try:
        rds.describe_db_subnet_groups(DBSubnetGroupName=subnet_group_name)
        print(f"  Reusing DB subnet group: {subnet_group_name}")
    except rds.exceptions.DBSubnetGroupNotFoundFault:
        rds.create_db_subnet_group(
            DBSubnetGroupName=subnet_group_name,
            DBSubnetGroupDescription="CVC chatbot Aurora subnets",
            SubnetIds=private_subnet_ids,
            Tags=[{"Key": "Project", "Value": "cvc-chatbot"}],
        )
        print(f"  Created DB subnet group: {subnet_group_name}")

    # Check if cluster already exists
    try:
        existing = rds.describe_db_clusters(DBClusterIdentifier=CLUSTER_ID)["DBClusters"][0]
        endpoint = existing["Endpoint"]
        print(f"  Reusing Aurora cluster: {CLUSTER_ID}  endpoint: {endpoint}")
        return {"endpoint": endpoint, "master_password": None}
    except rds.exceptions.DBClusterNotFoundFault:
        pass

    # Generate master password
    master_password = _secrets.token_urlsafe(24)

    print(f"  Creating Aurora Serverless v2 cluster: {CLUSTER_ID} …")
    rds.create_db_cluster(
        DBClusterIdentifier=CLUSTER_ID,
        Engine="aurora-postgresql",
        EngineVersion="15.4",
        DatabaseName=DB_NAME,
        MasterUsername=DB_MASTER_USER,
        MasterUserPassword=master_password,
        DBSubnetGroupName=subnet_group_name,
        VpcSecurityGroupIds=[rds_sg_id],
        ServerlessV2ScalingConfiguration={"MinCapacity": 0.5, "MaxCapacity": 4},
        BackupRetentionPeriod=7,
        StorageEncrypted=True,
        DeletionProtection=False,
        Tags=[{"Key": "Project", "Value": "cvc-chatbot"}],
    )

    # Aurora Serverless v2 requires at least one DB instance
    rds.create_db_instance(
        DBInstanceIdentifier=f"{CLUSTER_ID}-instance-1",
        DBClusterIdentifier=CLUSTER_ID,
        DBInstanceClass="db.serverless",
        Engine="aurora-postgresql",
        Tags=[{"Key": "Project", "Value": "cvc-chatbot"}],
    )

    # Wait for cluster available
    def _cluster_available():
        status = rds.describe_db_clusters(DBClusterIdentifier=CLUSTER_ID)["DBClusters"][0]["Status"]
        if status != "available":
            raise RuntimeError(status)
        return rds.describe_db_clusters(DBClusterIdentifier=CLUSTER_ID)["DBClusters"][0]["Endpoint"]
    endpoint = wait("Aurora cluster available (may take 5–10 min)", _cluster_available,
                    interval=20, max_attempts=60)

    print(f"  Aurora endpoint: {endpoint}")
    return {"endpoint": endpoint, "master_password": master_password}


# ── Step 11: Secrets Manager ─────────────────────────────────────────────────

def setup_secret(sm, endpoint: str, master_password: str) -> str:
    """Store DB credentials in Secrets Manager. Returns secret ARN."""
    secret_value = json.dumps({
        "host":     endpoint,
        "port":     5432,
        "dbname":   DB_NAME,
        "username": DB_MASTER_USER,
        "password": master_password,
    })

    try:
        result = sm.describe_secret(SecretId=SECRET_NAME)
        secret_arn = result["ARN"]
        if master_password:  # Update password only when we just created the cluster
            sm.update_secret(SecretId=SECRET_NAME, SecretString=secret_value)
            print(f"  Updated secret: {SECRET_NAME}")
        else:
            print(f"  Reusing secret: {SECRET_NAME}")
        return secret_arn
    except sm.exceptions.ResourceNotFoundException:
        result = sm.create_secret(
            Name=SECRET_NAME,
            SecretString=secret_value,
            Tags=[{"Key": "Project", "Value": "cvc-chatbot"}],
        )
        print(f"  Created secret: {SECRET_NAME}")
        return result["ARN"]


# ── Step 12: IAM ──────────────────────────────────────────────────────────────

def setup_iam(iam, secret_arn: str) -> None:
    """Attach required policies to the Lambda execution role."""
    # VPC execution (create/delete network interfaces)
    try:
        iam.attach_role_policy(
            RoleName=IAM_ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
        )
        print("  Attached VPC execution policy")
    except iam.exceptions.NoSuchEntityException:
        print(f"  WARN: IAM role {IAM_ROLE_NAME} not found — attach policy manually")

    # Secrets Manager read (scoped to our secret)
    policy_doc = json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": ["secretsmanager:GetSecretValue"],
            "Resource": secret_arn,
        }],
    })
    policy_name = "cvc-chatbot-secrets-read"
    try:
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        iam.get_policy(PolicyArn=policy_arn)
        iam.create_policy_version(PolicyArn=policy_arn, PolicyDocument=policy_doc, SetAsDefault=True)
        print(f"  Updated Secrets Manager policy: {policy_name}")
    except iam.exceptions.NoSuchEntityException:
        result = iam.create_policy(PolicyName=policy_name, PolicyDocument=policy_doc)
        policy_arn = result["Policy"]["Arn"]
        iam.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn=policy_arn)
        print(f"  Created + attached Secrets Manager policy: {policy_name}")


# ── Step 13–14: Update Lambda ─────────────────────────────────────────────────

def update_lambda(lam, private_subnet_ids: list[str], lambda_sg_id: str,
                  secret_arn: str, endpoint: str) -> None:
    """Configure Lambda VPC + env vars."""
    print("  Updating Lambda VPC config …")
    lam.update_function_configuration(
        FunctionName=LAMBDA_NAME,
        VpcConfig={
            "SubnetIds": private_subnet_ids,
            "SecurityGroupIds": [lambda_sg_id],
        },
    )
    # Wait for update to complete
    waiter = lam.get_waiter("function_updated")
    waiter.wait(FunctionName=LAMBDA_NAME)

    # Fetch current env vars and merge
    current = lam.get_function_configuration(FunctionName=LAMBDA_NAME)
    env_vars = current.get("Environment", {}).get("Variables", {})
    env_vars["SECRET_ARN"] = secret_arn
    env_vars["DB_NAME"]    = DB_NAME
    env_vars["DB_HOST"]    = endpoint

    lam.update_function_configuration(
        FunctionName=LAMBDA_NAME,
        Environment={"Variables": env_vars},
    )
    waiter.wait(FunctionName=LAMBDA_NAME)
    print("  Lambda VPC + env vars updated")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"\nCVC Chatbot — Aurora Serverless v2 setup (region: {AWS_REGION})")
    print("=" * 60)

    ec2 = boto3.client("ec2",             region_name=AWS_REGION)
    rds = boto3.client("rds",             region_name=AWS_REGION)
    sm  = boto3.client("secretsmanager",  region_name=AWS_REGION)
    iam = boto3.client("iam")
    lam = boto3.client("lambda",          region_name=AWS_REGION)

    print("\n[1/6] VPC + networking")
    vpc_info = setup_vpc(ec2)
    vpc_id          = vpc_info["vpc_id"]
    private_subnets = vpc_info["private_subnet_ids"]

    print("\n[2/6] Security groups")
    lambda_sg_id, rds_sg_id = setup_security_groups(ec2, vpc_id)

    print("\n[3/6] Aurora Serverless v2 cluster")
    aurora_info     = setup_aurora(rds, private_subnets, rds_sg_id)
    endpoint        = aurora_info["endpoint"]
    master_password = aurora_info["master_password"]

    print("\n[4/6] Secrets Manager")
    if master_password is None:
        # Cluster already existed; try to get existing secret
        try:
            secret_arn = sm.describe_secret(SecretId=SECRET_NAME)["ARN"]
        except sm.exceptions.ResourceNotFoundException:
            print("  ERROR: Cluster exists but no secret found. Create manually:")
            print(f"  SECRET_NAME={SECRET_NAME}, endpoint={endpoint}")
            sys.exit(1)
    else:
        secret_arn = setup_secret(sm, endpoint, master_password)

    print("\n[5/6] IAM permissions")
    setup_iam(iam, secret_arn)

    print("\n[6/6] Lambda VPC + env vars")
    update_lambda(lam, private_subnets, lambda_sg_id, secret_arn, endpoint)

    # Save outputs
    append_env(
        RDS_CLUSTER_ENDPOINT=endpoint,
        SECRET_ARN=secret_arn,
        VPC_ID=vpc_id,
        LAMBDA_SG_ID=lambda_sg_id,
        RDS_SG_ID=rds_sg_id,
    )

    print("\n" + "=" * 60)
    print("Setup complete. Outputs saved to .env.agent")
    print()
    print("Next steps:")
    print(f"  1. Migrate data:  SECRET_ARN={secret_arn} python data/migrate_to_postgres.py")
    print(f"  2. Deploy Lambda: python api/setup_api.py  (picks up new env vars)")
    print()
    print(f"  Aurora endpoint: {endpoint}")
    print(f"  Secret ARN:      {secret_arn}")


if __name__ == "__main__":
    main()
