# Engineering Roadmap

This document is intentionally high level. It records the direction of the project without describing customer workflows, proprietary data, operational identifiers, detailed deployment topology, or internal security controls.

## Product direction

Build a reliable conversational discovery application backed by structured data. The experience should translate natural-language requests into deterministic retrieval and ranking operations, then present results through a modern web interface.

## Technical direction

- Keep the frontend independently deployable as static assets.
- Use a serverless API boundary for web requests.
- Use Amazon Bedrock for language understanding and response generation, with application tools for structured operations.
- Maintain a portable data layer: lightweight local storage for development and managed PostgreSQL for production-scale workloads.
- Persist only the minimum session state necessary for a useful multi-turn experience.
- Make security, observability, testability, and operational simplicity first-class requirements.

## Delivery phases

1. **Foundation** — establish the data model, deterministic application tools, and unit tests.
2. **Experience** — deliver the React interface, request lifecycle, accessible components, and mock-mode development workflow.
3. **Cloud integration** — connect the serverless API, Bedrock runtime, session store, and static delivery path.
4. **Hardening** — review IAM boundaries, secret handling, network controls, logging, error handling, and automated validation.
5. **Scale and operate** — introduce managed relational storage, data refresh workflows, monitoring, cost controls, and release automation as demand requires.

## Engineering principles

- Treat models as language interfaces, not authoritative data stores.
- Keep business rules deterministic, testable, and version-controlled.
- Design for least privilege and secret-free source control.
- Favor managed AWS services and small operational surfaces.
- Document public architecture at a conceptual level; store environment-specific runbooks in approved internal locations.
