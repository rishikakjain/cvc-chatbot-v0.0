# California Virtual Campus — AWS Serverless AI Application

An AWS-first reference implementation for a conversational course-discovery experience. The project pairs a React single-page application with a serverless Python API, Amazon Bedrock tool use, and a portable course-data layer.

The application is designed around an important engineering boundary: the model interprets natural-language intent, while deterministic application code retrieves, filters, ranks, and formats structured results. That keeps responses grounded in data and makes the cloud architecture easier to operate and evolve.

## Architecture

```text
Browser
  │
  ├── Static application ──────────> Amazon S3 + Amazon CloudFront
  │
  └── HTTPS requests ──────────────> Amazon API Gateway
                                      │
                                      ▼
                                AWS Lambda (Python)
                                  ├── Amazon Bedrock Runtime
                                  │     ├── Converse API
                                  │     └── Guardrails
                                  ├── Amazon DynamoDB (session state)
                                  └── Course data access layer
                                        ├── SQLite for local development
                                        └── Aurora PostgreSQL for production
                                              └── AWS Secrets Manager
```

## AWS services

| Service | Role in the application |
| --- | --- |
| **Amazon Bedrock** | Runs the conversational model through the Converse API and coordinates application tool calls. Bedrock Guardrails provide a policy check before generation. |
| **AWS Lambda** | Hosts the stateless HTTP/session handler and the tool-oriented application logic. The handler caches SDK clients and data access resources for warm invocations. |
| **Amazon API Gateway** | Provides the public HTTPS boundary for the browser client and routes requests to Lambda. |
| **Amazon DynamoDB** | Stores short-lived conversation state behind a session identifier. The design supports TTL-based expiry. |
| **Amazon S3** | Hosts the compiled frontend assets. |
| **Amazon CloudFront** | Delivers the frontend globally and supports cache invalidation during releases. |
| **Amazon Aurora Serverless v2 (PostgreSQL)** | Provides a managed relational path for production course data. |
| **AWS Secrets Manager** | Supplies database credentials to the runtime instead of embedding them in source or configuration files. |
| **Amazon VPC, security groups, and IAM** | Isolate database traffic and apply service-to-service permissions. |

## Technology stack

- **Frontend:** React 18, Vite, plain CSS, React Markdown
- **Backend:** Python 3, boto3, AWS Lambda
- **AI integration:** Amazon Bedrock Converse API with tool use and Guardrails
- **Data:** SQLite for local development; PostgreSQL-compatible Aurora Serverless v2 for production
- **Persistence:** DynamoDB session records
- **Delivery:** Amazon S3 and CloudFront
- **Testing:** pytest and Vite production builds
- **Security tooling:** Gitleaks and environment-file exclusions

## Repository layout

```text
agent/       Bedrock-oriented tool handler and provisioning utility
api/         API Gateway/Lambda session handler and setup utility
data/        Schemas, data access layer, migrations, and local seed data
frontend/    React + Vite web application
scripts/     Operational helpers for database and frontend deployment
tests/       Unit, integration, and contract-style test coverage
tools/       Deterministic filtering and response-support functions
```

## How the request path works

1. The React client sends a message and any selected filters to API Gateway.
2. Lambda restores or creates session context in DynamoDB.
3. Bedrock interprets the request and can invoke declared application tools.
4. Python tools query structured course data, apply deterministic eligibility and ranking rules, and return compact results.
5. Bedrock turns only those tool results into a helpful response; Lambda returns the response and cards to the client.

This design avoids treating a language model as a database. Structured retrieval remains testable, observable, and independent of the model provider.

## Local development

Prerequisites: Python 3.11+ and Node.js 18+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cd frontend
npm ci
npm run dev
```

The frontend supports a local mock mode for UI work without cloud credentials. Runtime configuration belongs in local environment files and must never be committed.

## Validation

```bash
.venv/bin/python -m pytest -q tests/test_filter_courses.py tests/test_in_person_detection.py tests/test_sqlite_backend.py
cd frontend && npm run build
gitleaks detect --source . --redact
```

Some integration tests intentionally call a deployed endpoint. Run them only from an environment with approved access to the relevant AWS resources.

## Deployment notes

The repository includes operational utilities for provisioning/updating the Lambda API, preparing Bedrock integration, moving data to Aurora PostgreSQL, and publishing frontend assets to S3/CloudFront. Review IAM policies, network settings, cost controls, and environment configuration before executing any provisioning utility in an AWS account.

## Security posture

- Keep credentials, endpoints, and environment-local configuration out of Git.
- Use IAM roles and least-privilege policies for runtime access.
- Retrieve production database credentials through Secrets Manager.
- Keep Aurora access private and permit it only from approved workloads.
- Use Bedrock Guardrails and deterministic tools to reduce unsupported or off-policy responses.
- Run secret scanning before publishing changes.

## License

This repository does not currently declare a license. Add one before distributing or reusing the code outside its intended organization.
