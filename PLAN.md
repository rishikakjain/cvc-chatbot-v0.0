# CVC Chatbot v0.0 — Implementation Plan

## Context

CVC.edu is a California Community College course marketplace operated by Parchment (third-party vendor). Students at one CCC (their "home college") can enroll in online courses offered by another CCC (a "teaching college") through CVC. The platform serves 2.2 million students annually across 116 colleges and 100k+ courses. The current search UI requires students to navigate a 3-step dropdown with jargon-heavy fields (Cal-Breadth, IGETC, Cal-GETC area codes) and returns up to 700+ results with no guidance.

This is a **dual-track project**: Cal Poly DxHub is building a near-production solution over 6 weeks; the summer camp cohort builds a learning-exercise version in a 5-day sprint. This plan covers the DxHub track (the production-focused build).

The goal is a chatbot that replaces the 3-step jargon UI with a plain-language conversation while keeping the same logical flow:
1. Who are you? (home college)
2. What do you need? (plain English → GE area codes internally)
3. Here are your best options (top 3–5 ranked matches)

v0.0 scope: two teaching colleges (Victor Valley College + Cuesta College), Fall 2026, static CSV data.
v0.1 (future): ASSIST API keys → crosswalk showing which specific requirement a course satisfies at the student's home college. Also: live seat count API, full 116-college dataset.

---

## Assumptions (state explicitly)

1. We do NOT have API access to Parchment's backend. We work from the static CSV exports only.
2. The chatbot is a standalone near-production app (not yet embedded in cvc.edu; deployment strategy TBD — CVC owns domain, Parchment owns UI/UX).
3. No PII is stored — the student's home college selection is session-only.
4. Seat counts in the CSV are a snapshot; live seat count API integration is deferred to v0.1.
5. We cannot do the ASSIST crosswalk in v0.0 (no API keys yet) — we show GE area tags and explain them in plain language.
6. The chatbot covers course discovery only; the existing enrollment flow (SSO → 2 confirmation screens) is untouched.
7. The student's home college is captured to (a) exclude their own college from results and (b) set up the personalization hook for v0.1.
8. The summer camp cohort will build in parallel using the same design; this plan is for the DxHub production track.
9. v0.0 is demo-quality (end-to-end working, showable to stakeholders). Auth hardening, IaC, and monitoring are deferred to a hardening pass once the design is validated.

---

## Minimum Capabilities Required

| # | Capability | Why |
|---|-----------|-----|
| 1 | Collect home college upfront | Exclude student's own college; personalization hook for v0.1 |
| 2 | Translate plain English to GE area codes | Core problem — students don't know "B2" means "Life Science" |
| 3 | Filter courses by GE area + delivery method + seats | Structured query against CSV data |
| 4 | Return top 3–5 ranked results in plain language | Prevent result overload |
| 5 | Explain GE jargon on demand | Replace FAQ — "what is IGETC?", "what's Cal-GETC?" |
| 6 | Support course comparison | "Which of these has more seats?" / "Does this one have prerequisites?" |
| 7 | Guardrails against transfer guarantees | Mike Vogt explicitly flagged this risk — chatbot must not promise articulation |

---

## Architecture Comparison

### Option 1 — Single Model Call
All course data pasted into Claude's system prompt. Lambda calls Bedrock, Claude answers.
- **Pro:** Zero infrastructure, fastest to build.
- **Con:** ~857 course sections × 22 fields each → exceeds practical context window. Can't do structured filtering. Will hallucinate specific seat counts or dates.
- **Verdict: Not viable** for even the 2-college dataset.

### Option 2 — Deterministic Workflow
Lambda classifies intent, runs a hardcoded query, Bedrock formats the response.
- **Pro:** Predictable, fast, cheap.
- **Con:** Brittle. Any query outside the coded decision tree fails. Natural language is unpredictable enough that this breaks constantly.
- **Verdict: Partial use** — use deterministic logic *inside* the tools, but not as the orchestrator.

### Option 3 — RAG Workflow
Course data chunked into vectors, stored in OpenSearch, retrieved by semantic similarity.
- **Pro:** Handles unstructured documents well.
- **Con:** The course data is already structured (22-column CSV). Semantic retrieval adds complexity and cost with no benefit over a simple filter. Requires a vector DB (violates constraints).
- **Verdict: Not needed.** The data is tabular, not unstructured.

### Option 4 — Tool-Using Agent ✓ RECOMMENDED
Bedrock Agents orchestrates the conversation. Lambda functions are registered as tools. Claude decides which tools to call based on the student's message.

**Why this wins:**
- Student queries are unpredictable in phrasing but map to a small set of operations
- The LLM handles the language layer; deterministic Lambda tools handle the data layer
- No vector DB required — structured filtering in Python
- Naturally handles multi-turn ("show me more", "which is easier?", "what does IGETC mean?")
- Clean separation: swap CSV → live API in v0.1 without touching the agent logic

---

## Recommended Design

```
Student (browser) 
    ↕ HTTP (session_id cookie)
API Gateway
    ↕ invoke
Lambda (session handler)
    ↕ read/write          ↕ InvokeAgent
DynamoDB (sessions)    Bedrock Agent (Claude Sonnet)
                           ↕ tool calls
                       Lambda Tools:
                         - filter_courses(ge_areas[], delivery, start_after, exclude_college)
                         - explain_ge_area(query)
                         - get_faq_answer(topic)

Data: S3 JSON (converted from CSV) — loaded cold by Lambda tools
```

### Conversation Flow (kept inside chatbot, plain language)

```
Bot: "Hi! I'm here to help you find classes at other California colleges. 
      What's your home college?"
Student: "I go to Pasadena City College"
Bot: "Got it. What are you looking for — a specific subject, or a requirement 
      you need to fulfill for transfer?"
Student: "I need a science class with a lab for CSU transfer"
Bot: [calls filter_courses(ge_areas=["B1","B3"], exclude_college="Pasadena City College")]
Bot: "Here are 3 good options:
      1. Intro to Biology with Lab — Victor Valley, async, 4 units, 31 seats left
      2. Physical Geology with Lab — Cuesta, async, 4 units, 22 seats left
      3. ..."
```

---

## Data Pipeline

1. Convert both XLSX files to a single `courses.json` (list of dicts, camelCase keys)
2. Upload to S3 bucket (single file, ~200KB)
3. Lambda tools load it at cold start; cached in memory for warm invocations

## Session Storage (DynamoDB)

Bedrock Agent sessions expire and don't survive browser refreshes. DynamoDB provides lightweight session persistence without storing PII long-term.

**Table: `cvc_sessions`**

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | String (PK) | UUID set as a cookie in browser |
| `home_college` | String | Captured in turn 1 |
| `last_query` | String | Student's most recent plain-language query |
| `courses_shown` | List\<String\> | CRNs of courses returned in last recommendation |
| `turn_count` | Number | For analytics — how many turns to a recommendation |
| `bedrock_session_id` | String | Links back to Bedrock Agent session |
| `created_at` | String (ISO) | Timestamp |
| `ttl` | Number | Unix epoch 24h from creation — DynamoDB auto-deletes |

**Why 24h TTL:** Students shouldn't need longer than a day to find and enroll in a course. Auto-expiry keeps the table clean and ensures no long-term session data accumulates.

**Resume flow:** On page load, if a `session_id` cookie exists and the DynamoDB record hasn't expired, the chatbot greets with context: *"Welcome back — still looking for that science lab course at Victor Valley?"*

### GE Area Code Taxonomy (baked into system prompt)

The system prompt includes a mapping table:

| Plain Language | CSU Breadth | IGETC | Cal-GETC |
|----------------|-------------|-------|----------|
| Written Communication / English Comp | A2 | 1A | 1A |
| Critical Thinking | A3 | 1B | 1B |
| Math / Quantitative Reasoning | B4 | 2A | 2A |
| Physical Science | B1 | 5A | 5A |
| Life Science / Biology | B2 | 5B | 5B |
| Science Lab | B3 | 5C | 5C |
| Arts | C1 | 3A | 3A |
| Humanities | C2 | 3B | 3B |
| Social Science | D (various) | 4 (various) | 4 (various) |
| Oral Communication / Speech | A1 | 1C | 1C |
| Ethnic Studies | F | — | — |

The LLM maps plain language to these codes before calling `filter_courses`.

---

## Cost Drivers

| Component | v0.0 (demo) | Scale estimate |
|-----------|-------------|----------------|
| Bedrock (Claude Sonnet 3.5) | ~$0.003/conversation (3 turns × ~1k tokens) | $3/1000 conversations |
| Lambda invocations | ~$0.00 (free tier) | negligible |
| S3 reads | ~$0.00 | negligible |
| API Gateway | ~$0.00 (free tier) | $3.50/million calls |
| DynamoDB (on-demand) | ~$0.00 (free tier; ~1 read + 2 writes per conversation) | ~$0.25/1000 conversations |
| **Total** | **Near-zero for demo** | **~$3–6 per 1000 conversations** |

No vector DB = no OpenSearch/Kendra cost.

---

## Security, Privacy, and Reliability Risks

| Risk | Mitigation |
|------|-----------|
| Chatbot promises transfer credit | System prompt guardrail with exact language: *"This course is tagged for [area]. Based on that tag it should count toward your requirements — but articulation agreements can vary by home college. Confirm with your counselor or check assist.org before registering."* |
| Student PII stored | No persistence in v0.0 — session context lives only in Bedrock Agent session, not in any database |
| Hallucinated course details | `filter_courses` tool returns exact data; LLM is instructed to only describe courses returned by the tool, never invent them |
| Data staleness (CSV snapshot) | Disclaimer in UI: "Course data is updated periodically; check cvc.edu for live seat counts" |
| Injection via student input | API Gateway + Lambda — no SQL queries, no shell commands; only structured JSON filtering |
| Tenant isolation | v0.0 is single-tenant (CVC demo); session IDs used to isolate conversation history in Bedrock Agent |

---

## Evaluation Suite

### Unit-level tests (mock the Bedrock call)

| Test | Input | Expected behavior |
|------|-------|-------------------|
| GE mapping | "science with a lab" | maps to B1+B3 (or 5A+5C) |
| GE mapping | "English writing class" | maps to A2 (or 1A) |
| Jargon explanation | "what is IGETC?" | plain-language answer, no hallucination |
| Home college exclusion | home = "Victor Valley College" | results only from Cuesta |
| Guardrail | "will this count for my transfer?" | hedged answer, counselor referral |
| No results | very narrow filter | graceful fallback, suggests broadening |

### Integration tests (live Bedrock, mock data)

- Full 3-turn conversation from greeting → course recommendation
- Comparison query ("which of these has more seats available?")
- FAQ question mid-conversation ("wait, what's Cal-GETC again?")

### Acceptance criteria

- [ ] Student can get 3 relevant course recommendations using only plain language (no jargon required)
- [ ] Chatbot correctly explains IGETC, Cal-GETC, CSU Breadth in plain English
- [ ] Chatbot never returns courses from the student's home college
- [ ] Chatbot never guarantees transfer credit without counselor caveat
- [ ] All responses grounded in `courses.json` data — no hallucinated courses
- [ ] Runnable locally using mock data with no AWS credentials

---

## Implementation Plan (Incremental)

### Phase 0 — Data Prep (½ day)
- [ ] Convert 2 XLSX files → single `courses.json`
- [ ] Validate all 22 fields, normalize GE area codes (split pipe-separated into arrays)
- [ ] Write a local `filter_courses(params)` Python function and test it against known queries

### Phase 1 — Lambda Tools (1 day)
- [ ] `filter_courses` — takes ge_areas[], delivery_method, exclude_college; returns top 10 matches sorted by seats_available desc
- [ ] `explain_ge_area` — takes plain text or code; returns plain-language description + area code
- [ ] `get_faq_answer` — takes topic string; returns FAQ content (hardcoded dict for v0.0)
- [ ] Each tool testable locally with `pytest` + mock data

### Phase 2 — Bedrock Agent (1 day)
- [ ] Write system prompt (persona, GE taxonomy table, guardrails, conversation flow instructions)
- [ ] Register 3 Lambda tools with Bedrock Agent action group
- [ ] Configure session management
- [ ] Test in Bedrock console with manual queries

### Phase 3 — API + UI (1 day)
- [ ] API Gateway → Lambda session handler → Bedrock Agent invoke
- [ ] Minimal chat UI (React or plain HTML) hosted on S3/Amplify
- [ ] Local dev mode using mocked responses (no AWS credentials needed)

### Phase 4 — Evaluation (½ day)
- [ ] Run evaluation suite
- [ ] Fix guardrail failures and GE mapping gaps
- [ ] Document gaps deferred to v0.1 (ASSIST crosswalk, live seat counts, full 116-college dataset)

---

## v0.1 Hook Points (do not implement — just leave the socket labeled)

Hook points are deliberate placeholders in v0.0 code where v0.1 features plug in without a rewrite:

- **`filter_courses` param `exclude_college`** — already there. In v0.1, this same param triggers an ASSIST API call to show "this course counts as [requirement] at your home college." No tool signature change needed.
- **System prompt placeholder** — a commented section `## Home college context (v0.1): {assist_crosswalk_data}` is injected as empty string in v0.0; in v0.1 it gets populated with ASSIST response data.
- **`get_seat_count(crn)` tool stub** — register a no-op Lambda tool in v0.0 that returns the CSV snapshot value. In v0.1, swap the Lambda body to call the live CVC seat count API. Agent behavior unchanged.
- **GE taxonomy as a config file** (`ge_areas.json`) — not hardcoded in the system prompt string. Easy to extend or correct without touching agent config.
- **`courses.json` data source abstraction** — Lambda tools load data via a `load_courses()` function. In v0.0 it reads from S3. In v0.1 it calls a live API. One function to change.
