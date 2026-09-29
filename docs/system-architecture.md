# CVC Chatbot — System Architecture

This is the high-level request path for the CVC conversational course-discovery application. The model understands the student's request; application code performs the course lookup and returns structured results.

```mermaid
%%{init: {
  'theme': 'base',
  'flowchart': { 'curve': 'stepBefore', 'nodeSpacing': 45, 'rankSpacing': 70 },
  'themeVariables': {
    'background': '#FFFFFF',
    'primaryTextColor': '#14213D',
    'lineColor': '#64748B',
    'fontFamily': 'Inter, Arial, sans-serif'
  }
}}%%
flowchart LR
  classDef client fill:#E8F1FF,stroke:#2563EB,color:#14213D,stroke-width:2px;
  classDef edge fill:#EEF2FF,stroke:#4F46E5,color:#1E1B4B,stroke-width:2px;
  classDef compute fill:#ECFDF5,stroke:#059669,color:#064E3B,stroke-width:2px;
  classDef ai fill:#FFF7ED,stroke:#EA580C,color:#7C2D12,stroke-width:2px;
  classDef data fill:#FFF1F2,stroke:#E11D48,color:#881337,stroke-width:2px;

  Student([Student]):::client

  subgraph Web["Web application"]
    direction TB
    UI[React chat interface<br/>messages, filters, course cards]:::client
    CDN[CloudFront + S3<br/>hosts and delivers the web app]:::edge
    UI --> CDN
  end

  API[API Gateway<br/><code>POST /chat</code>]:::edge

  subgraph App["AWS Lambda · application logic"]
    direction TB
    Handler[Session handler<br/>coordinates each chat request]:::compute
    Tools[Deterministic course tools<br/>filter · rank · explain FAQ]:::compute
    Handler --> Tools
  end

  Bedrock[Amazon Bedrock<br/>Claude + Guardrails<br/>interprets intent and writes the reply]:::ai

  Sessions[(DynamoDB<br/>short-lived chat session)]:::data
  Courses[(Course catalog<br/>SQLite locally · Aurora in production)]:::data

  Student --> UI
  UI -->|send message| API
  API --> Handler
  Handler <-->|conversation + tool calls| Bedrock
  Handler <-->|read / save context| Sessions
  Tools <-->|search structured courses| Courses
  Handler -->|reply + course cards| API
  API --> UI

  class Student,UI client
  class CDN,API edge
  class Handler,Tools compute
  class Bedrock ai
  class Sessions,Courses data
```

## What each part does

| Key player | Responsibility |
| --- | --- |
| **React + CloudFront/S3** | Displays the chat and course cards, and serves the static web application. |
| **API Gateway** | Public HTTPS entry point for chat requests. |
| **Lambda** | Restores session context, calls Bedrock, runs the approved tools, and shapes the response. |
| **Amazon Bedrock** | Understands natural-language requests, applies guardrails, and decides when a tool is needed. |
| **Course tools + catalog** | Keep filtering, ranking, and course facts deterministic rather than model-generated. |
| **DynamoDB** | Holds short-lived conversation context behind a session ID. |

## Request in five steps

1. A student sends a question through the React chat interface.
2. API Gateway forwards it to the Lambda session handler.
3. Lambda loads the short-lived session and asks Bedrock to interpret the request.
4. If course information is needed, Lambda runs deterministic tools against the course catalog and returns those results to Bedrock.
5. Lambda returns Bedrock's concise reply and the structured course cards to the browser.

The orthogonal connector setting (`stepBefore`) keeps request paths square and easy to follow in Mermaid-compatible renderers.
