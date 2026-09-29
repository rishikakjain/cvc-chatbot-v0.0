# CVC Chatbot — Detailed System Architecture

> **Scope:** This is an implementation-grounded architecture diagram for the CVC conversational course-discovery application. Solid lines show the primary request path implemented by the serverless API. Dashed lines show provisioning, deployment, or the optional production data path. The diagram uses an explicit light palette for legibility in GitHub, VS Code, and Mermaid-compatible renderers.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'background': '#FFFFFF',
    'primaryColor': '#E8F1FF',
    'primaryTextColor': '#14213D',
    'primaryBorderColor': '#2563EB',
    'lineColor': '#475569',
    'secondaryColor': '#ECFDF5',
    'tertiaryColor': '#FFF7ED',
    'clusterBkg': '#F8FAFC',
    'clusterBorder': '#CBD5E1',
    'fontFamily': 'Inter, Arial, sans-serif'
  }
}}%%
flowchart TB
  classDef user fill:#F5F3FF,stroke:#7C3AED,color:#2E1065,stroke-width:2px;
  classDef edge fill:#E8F1FF,stroke:#2563EB,color:#14213D,stroke-width:2px;
  classDef compute fill:#ECFDF5,stroke:#059669,color:#064E3B,stroke-width:2px;
  classDef ai fill:#FFF7ED,stroke:#EA580C,color:#7C2D12,stroke-width:2px;
  classDef data fill:#FFF1F2,stroke:#E11D48,color:#881337,stroke-width:2px;
  classDef security fill:#FEFCE8,stroke:#CA8A04,color:#713F12,stroke-width:2px;
  classDef dev fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:2px;

  subgraph Client[1 · Student browser]
    direction TB
    Student([Student]):::user
    SPA[React 18 + Vite single-page application<br/>App · i18n · theme · accessible components]:::edge
    UIState[Browser state<br/>message, selected filters, returned cards]:::edge
    BrowserSession[sessionStorage<br/><code>cvc_session_id</code>]:::edge
    Student --> SPA
    SPA <--> UIState
    SPA <--> BrowserSession
  end

  subgraph Delivery[2 · Static application delivery]
    direction LR
    CDN[Amazon CloudFront<br/>HTTPS redirect · compression<br/>GET/HEAD cache behavior<br/>SPA 403/404 → index.html]:::edge
    OAC[Origin Access Control<br/>SigV4 service-to-service access]:::security
    Assets[(Amazon S3 frontend bucket<br/>compiled <code>dist/</code> assets)]:::data
    CDN --> OAC --> Assets
  end

  subgraph PublicAPI[3 · Public API boundary]
    direction TB
    APIGW[Amazon API Gateway HTTP API<br/><code>POST /chat</code><br/>CORS: Content-Type, X-Session-Id]:::edge
    Request[Request JSON<br/><code>message</code> + optional filter context<br/>Header: <code>X-Session-Id</code>]:::edge
    Response[Response JSON<br/><code>reply</code> · <code>courses</code> · <code>session_id</code>]:::edge
    APIGW --- Request
    APIGW --- Response
  end

  subgraph Runtime[4 · AWS Lambda — cvc-chatbot-session-handler (Python 3.12)]
    direction TB
    Handler[HTTP handler<br/>validates method/body · CORS response<br/>creates UUID when session absent]:::compute
    SessionMgr[Session manager<br/>loads/saves turn history + preferences<br/>refreshes TTL to 24 hours]:::compute
    GuardCheck{Guardrail ID configured?}:::security
    Blocked[Scoped blocked reply<br/>CVC course-advising only]:::security
    ConverseLoop[Converse orchestration loop<br/>max 10 rounds · retains messages<br/>dedupes course cards across tool calls]:::compute
    Formatter[Response shaping<br/>normalizes model prose<br/>returns concise text + structured cards]:::compute
    Handler --> SessionMgr --> GuardCheck
    GuardCheck -- blocked / unavailable --> Blocked --> Formatter
    GuardCheck -- permitted --> ConverseLoop --> Formatter
  end

  subgraph State[5 · Short-lived conversation state]
    direction TB
    DDB[(Amazon DynamoDB<br/><code>cvc_sessions</code><br/>PK: session_id<br/>messages serialized · home_college<br/>turn_count · created_at · ttl)]:::data
    TTL[DynamoDB TTL expiry<br/>24-hour session retention target]:::security
    DDB --- TTL
  end

  subgraph AI[6 · Amazon Bedrock runtime]
    direction TB
    Guardrails[Bedrock Guardrails<br/>input policy check via ApplyGuardrail<br/>off-topic requests denied]:::security
    Converse[Bedrock Converse API<br/>Claude Haiku model ID from environment<br/>system prompt + conversation + tool schema]:::ai
    ToolDecision{Model stop reason}:::ai
    FinalText[<code>end_turn</code><br/>final natural-language reply]:::ai
    ToolUse[<code>tool_use</code><br/>name + JSON arguments]:::ai
    Guardrails --> Converse --> ToolDecision
    ToolDecision -- end_turn --> FinalText
    ToolDecision -- tool_use --> ToolUse
  end

  subgraph Tools[7 · Deterministic application tools in the Lambda package]
    direction TB
    Dispatch[Tool dispatcher<br/>executes only declared tool names<br/>serializes JSON tool results]:::compute
    Filter[<code>filter_courses</code><br/>eligibility + deterministic ranking]:::compute
    Explain[<code>explain_ge_area</code><br/>GE-area / framework explanation]:::compute
    FAQ[<code>get_faq_answer</code><br/>enrollment, transfer, fee, deadline FAQ]:::compute
    Rules[Course filtering and ranking rules<br/>GE expansion · subject · delivery · seats<br/>ZTC · date · duration · region · distance<br/>in-person note detection · composite score]:::compute
    Dispatch --> Filter --> Rules
    Dispatch --> Explain
    Dispatch --> FAQ
  end

  subgraph CourseData[8 · Course data boundary]
    direction TB
    DataAdapter[Portable data access layer<br/><code>data/db.py</code> · camelCase row mapping<br/>cached resources in warm runtime]:::compute
    Local[(Local development / tests<br/>SQLite <code>courses.db</code><br/>schema.sql)]:::data
    Bundle[(Packaged seed/reference data<br/><code>courses.json</code><br/>college locations + regions)]:::data
    Secret[Amazon Secrets Manager<br/><code>SECRET_ARN</code> supplies DB credentials<br/>cached per Lambda container]:::security
    Aurora[(Production target<br/>Aurora Serverless v2 PostgreSQL<br/>courses + colleges)]:::data
    DataAdapter --> Local
    DataAdapter -. <code>SECRET_ARN</code> .-> Secret
    Secret -. TLS credentials .-> Aurora
    DataAdapter -. PostgreSQL query .-> Aurora
    Bundle --- Rules
  end

  subgraph Security[9 · Security, identity, and network controls]
    direction TB
    IAM[IAM execution role<br/>least-privilege intent:<br/>Lambda invoke · Bedrock runtime<br/>DynamoDB session-item access]:::security
    VPC[Production database isolation<br/>VPC + security groups<br/>Aurora private access]:::security
    HTTPS[Transport boundaries<br/>browser → CloudFront/API Gateway over HTTPS<br/>CloudFront redirects viewers to HTTPS]:::security
    Source[Secret-free source control<br/>environment-local <code>.env.agent</code> excluded]:::security
    IAM --- VPC
  end

  subgraph DeliveryOps[10 · Build, release, and validation]
    direction TB
    Dev[Developer workstation / CI]:::dev
    ReactBuild[<code>npm run build</code><br/>Vite compiles frontend]:::dev
    DeployFE[<code>scripts/deploy_frontend.sh</code><br/>S3 sync + CloudFront invalidation]:::dev
    Provision[<code>api/setup_api.py</code><br/>provisions/updates API, Lambda, DDB<br/>S3, CloudFront, guardrail configuration]:::dev
    DataLoad[Data tools<br/>schema · course conversion/build<br/>migration to PostgreSQL]:::dev
    Tests[pytest unit / integration tests<br/>Vite production build · Gitleaks scan]:::dev
    Dev --> ReactBuild --> DeployFE
    Dev --> Provision
    Dev --> DataLoad
    Dev --> Tests
  end

  %% Browser content and chat traffic
  SPA -- "GET static HTML / JS / CSS" --> CDN
  CDN -- "cached static application" --> SPA
  SPA -- "HTTPS POST /chat\nmessage + filters + X-Session-Id" --> APIGW
  APIGW -- "AWS proxy invoke" --> Handler
  Formatter -- "200 response: reply + courses + session_id" --> APIGW
  APIGW --> SPA

  %% State and AI interactions
  SessionMgr -- "GetItem / PutItem" --> DDB
  GuardCheck -- "ApplyGuardrail (when enabled)" --> Guardrails
  ConverseLoop -- "Converse: prompt, history, toolConfig" --> Converse
  FinalText -- "text output" --> ConverseLoop
  ToolUse -- "tool name + input" --> Dispatch
  Dispatch -- "toolResult JSON" --> ConverseLoop
  ConverseLoop -- "final reply + course set" --> Formatter
  Filter -- "read courses / college metadata" --> DataAdapter

  %% Control plane and delivery interactions
  IAM -. grants runtime permissions .-> Handler
  IAM -. grants runtime permissions .-> DDB
  IAM -. grants runtime permissions .-> Guardrails
  IAM -. grants runtime permissions .-> Converse
  VPC -. isolates .-> Aurora
  HTTPS -. protects .-> CDN
  HTTPS -. protects .-> APIGW
  Source -. keeps out of Git .-> Dev
  DeployFE -. uploads / invalidates .-> Assets
  Provision -. deploys .-> Handler
  Provision -. creates .-> APIGW
  Provision -. creates .-> DDB
  Provision -. configures .-> CDN
  Provision -. configures .-> Guardrails
  DataLoad -. creates / migrates .-> Local
  DataLoad -. migrates .-> Aurora

  class Student user
  class SPA,UIState,BrowserSession,CDN,APIGW,Request,Response edge
  class Handler,SessionMgr,ConverseLoop,Formatter,Dispatch,Filter,Explain,FAQ,Rules,DataAdapter compute
  class Converse,ToolDecision,FinalText,ToolUse ai
  class Assets,DDB,Local,Bundle,Aurora data
  class OAC,GuardCheck,Blocked,TTL,Guardrails,Secret,IAM,VPC,HTTPS,Source security
  class Dev,ReactBuild,DeployFE,Provision,DataLoad,Tests dev
```

## Request lifecycle

1. CloudFront serves the React single-page app from the S3 origin through Origin Access Control. The frontend retains only the opaque session ID in browser `sessionStorage`.
2. The app submits the student's message, optional UI filters, and existing `X-Session-Id` to API Gateway's `POST /chat` route. API Gateway invokes the session-handler Lambda through an AWS proxy integration.
3. Lambda reads or initializes the DynamoDB session record. It refreshes the `ttl` value on every save, preserving only short-lived conversation context and selected preferences.
4. When a Bedrock guardrail ID is configured, Lambda applies the input guardrail before model generation. A blocked request receives a scoped, deterministic CVC response.
5. For permitted input, Lambda calls Bedrock Converse with the system prompt, stored conversation, and the schema of the three application tools. The model chooses whether to answer or request a tool.
6. Lambda executes requested tools locally. Course search is deterministic: it queries the portable data layer, applies eligibility filters and ranking rules, and returns compact JSON rather than model-invented records.
7. Lambda returns each tool result to Bedrock and repeats until the model ends the turn (up to ten tool-use rounds). It deduplicates course cards and trims overly verbose course prose before responding.
8. API Gateway returns the final reply, structured course cards, and session ID. React renders the text and cards; the browser retains the returned ID for the next turn.

## Data-mode interpretation

| Environment / mode | Course source | Intended use |
| --- | --- | --- |
| Local development and test | SQLite `courses.db` and JSON test/reference data | Fast, credential-free local workflow |
| Serverless package today | `courses.json` and deterministic Python tools are bundled by the deployment utility | Portable reference-data packaging |
| Production target | Aurora Serverless v2 PostgreSQL, with credentials resolved from Secrets Manager when `SECRET_ARN` is configured | Managed relational storage and production-scale data operations |

The optional Aurora path is deliberately dashed in the diagram: the repository contains its adapter and migration tooling, while the exact activated data source is environment configuration and deployment-package dependent.

## Diagram legend

- **Solid arrows**: runtime request or response flow.
- **Dashed arrows**: deployment, provisioning, permissions, security boundaries, or optional production paths.
- **Blue**: client/edge/API; **green**: deterministic application code; **orange**: generative-AI orchestration; **rose**: persistence; **yellow**: security; **gray**: development and operations.
