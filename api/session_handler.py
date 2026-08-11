"""
Session handler Lambda — HTTP bridge between the browser and Claude on Bedrock.

Uses the Bedrock Runtime Converse API (not Bedrock Agents) with tool use.
The tool-use loop runs here: Claude decides which tool to call, we execute it,
send the result back, and repeat until Claude produces a final text reply.

Environment variables:
    AWS_REGION          (default: us-west-2)
    BEDROCK_MODEL_ID    (default: anthropic.claude-haiku-4-5-20251001)
    DYNAMODB_TABLE      (default: cvc_sessions)
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

import boto3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.filter_courses import filter_courses, summarize_course
from tools.explain_ge_area import explain_ge_area
from tools.get_faq_answer import get_faq_answer

REGION = os.environ.get("APP_REGION", os.environ.get("AWS_REGION", "us-west-2"))
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "cvc_sessions")
GUARDRAIL_ID = os.environ.get("BEDROCK_GUARDRAIL_ID")
SESSION_TTL_SECONDS = 24 * 60 * 60

SYSTEM_PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "agent", "system_prompt.txt"
)

_bedrock = None
_dynamo_table = None


def _get_bedrock():
    global _bedrock
    if _bedrock is None:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock


def _get_table():
    global _dynamo_table
    if _dynamo_table is None:
        _dynamo_table = boto3.resource("dynamodb", region_name=REGION).Table(TABLE_NAME)
    return _dynamo_table


def _load_system_prompt() -> str:
    try:
        with open(SYSTEM_PROMPT_PATH) as f:
            return f.read()
    except FileNotFoundError:
        return "You are Alex, a friendly CVC course advisor helping California Community College students find online transfer courses."


# ── Tool definitions for the Converse API ────────────────────────────────────

TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "filter_courses",
                "description": "Search for available CVC online courses by subject, GE area, delivery method, college, and start date. Use subject_keyword when the student asks by subject name (e.g. 'math', 'biology'). Use ge_areas when they ask by GE requirement. Use both together for best results.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "subject_keyword": {
                                "type": "string",
                                "description": "Free-text keyword to match against course name (case-insensitive). Use when student asks for a subject like 'math', 'algebra', 'statistics', 'biology'. Can be combined with ge_areas.",
                            },
                            "ge_areas": {
                                "type": "string",
                                "description": "Comma-separated GE area codes (e.g. 'B2,5B'). Omit for no GE filter.",
                            },
                            "delivery_method": {
                                "type": "string",
                                "enum": ["async", "sync"],
                                "description": "Filter by delivery: 'async' or 'sync'. Omit for no filter.",
                            },
                            "exclude_college": {
                                "type": "string",
                                "description": "Student's home college name to exclude from results.",
                            },
                            "start_after": {
                                "type": "string",
                                "description": "ISO date YYYY-MM-DD — exclude courses starting before this.",
                            },
                            "has_seats": {
                                "type": "boolean",
                                "description": "Only return courses with available seats (default true).",
                            },
                            "top_n": {
                                "type": "integer",
                                "description": "Max results to return (default 5).",
                            },
                        },
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "explain_ge_area",
                "description": "Explain a GE area code or plain-language subject (e.g. 'B2', '5B', 'science lab', 'what is IGETC').",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "required": ["query"],
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "A GE area code, plain-language phrase, or framework name.",
                            }
                        },
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "get_faq_answer",
                "description": "Answer a common question about CVC enrollment, transfer credit, fees, or deadlines.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "required": ["topic"],
                        "properties": {
                            "topic": {
                                "type": "string",
                                "description": "The question or topic string.",
                            }
                        },
                    }
                },
            }
        },
    ]
}


# ── Tool execution ────────────────────────────────────────────────────────────

def _run_tool(name: str, tool_input: dict) -> str:
    if name == "filter_courses":
        ge_raw = tool_input.get("ge_areas")
        ge_areas = [c.strip() for c in ge_raw.split(",")] if ge_raw else None
        has_seats = tool_input.get("has_seats", True)
        if isinstance(has_seats, str):
            has_seats = has_seats.lower() not in ("false", "0", "no")
        top_n = int(tool_input.get("top_n", 5))
        courses = filter_courses(
            ge_areas=ge_areas,
            subject_keyword=tool_input.get("subject_keyword"),
            delivery_method=tool_input.get("delivery_method"),
            exclude_college=tool_input.get("exclude_college"),
            start_after=tool_input.get("start_after"),
            has_seats=has_seats,
            top_n=top_n,
        )
        return json.dumps([summarize_course(c) for c in courses])

    if name == "explain_ge_area":
        return json.dumps(explain_ge_area(tool_input.get("query", "")))

    if name == "get_faq_answer":
        return json.dumps(get_faq_answer(tool_input.get("topic", "")))

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── Converse API loop ─────────────────────────────────────────────────────────

def _strip_course_prose(text: str) -> str:
    """
    When filter_courses returned results, keep only:
    - The first plain-text intro sentence
    - Numbered follow-up options (1. ... 2. ...)
    Everything else is already rendered on the course cards.
    """
    import re
    # Follow-up options always start with an action verb — course listings never do
    followup_action = re.compile(
        r'^\d+\.\s+\*{0,2}(search|show|filter|find|explain|tell|compare|narrow|look|get|see|ask|check|help|what|how|which|can you|display)',
        re.I
    )
    intro = None
    numbered = []
    for line in text.splitlines():
        t = line.strip()
        if not t:
            continue
        if re.match(r'^\d+\.', t):
            if followup_action.match(t):
                numbered.append(line)
        elif intro is None and not t.startswith('|') and not re.match(r'^[-*•#]', t) and not re.match(r'^---', t):
            # Strip trailing colon/intro markers like "Here's what's available:"
            first_sentence = re.split(r':\s*$', t)[0]
            intro = first_sentence
    parts = []
    if intro:
        parts.append(intro.rstrip('.') + '.')
    if numbered:
        parts.extend(numbered)
    return '\n'.join(parts).strip()


_GUARDRAIL_BLOCKED_REPLY = (
    "I can only help with CVC course advising — "
    "try asking me to find a course or explain a GE requirement!\n\n"
    "1. Search for courses in a GE area\n"
    "2. Explain what IGETC or CSU GE Breadth means"
)


def _check_guardrail(text: str) -> bool:
    """Return True if the guardrail blocks this text (GUARDRAIL_INTERVENED)."""
    if not GUARDRAIL_ID:
        return False
    try:
        resp = _get_bedrock().apply_guardrail(
            guardrailIdentifier=GUARDRAIL_ID,
            guardrailVersion="DRAFT",
            source="INPUT",
            content=[{"text": {"text": text}}],
        )
        return resp.get("action") == "GUARDRAIL_INTERVENED"
    except Exception:
        return False


def converse(messages: list[dict]) -> tuple[str, list[dict]]:
    """
    Run the Bedrock Converse API tool-use loop.
    Returns (final_text_reply, courses) where courses is a list of course dicts
    collected from any filter_courses tool calls made during this turn.
    """
    # Pre-flight guardrail check on the latest user message
    if messages and GUARDRAIL_ID:
        last = messages[-1]
        if last.get("role") == "user":
            content = last.get("content", [])
            user_text = " ".join(
                b.get("text", "") for b in content if isinstance(b, dict) and "text" in b
            )
            if _check_guardrail(user_text):
                return _GUARDRAIL_BLOCKED_REPLY, []

    client = _get_bedrock()
    system_prompt = _load_system_prompt()

    current_messages = list(messages)
    # Accumulate unique courses (deduped by courseCode+teachingCollege) across
    # all filter_courses tool calls in this turn.
    courses_seen: dict[str, dict] = {}

    for _ in range(10):  # max 10 tool-use rounds
        converse_kwargs = dict(
            modelId=MODEL_ID,
            system=[{"text": system_prompt}],
            messages=current_messages,
            toolConfig=TOOL_CONFIG,
        )
        response = client.converse(**converse_kwargs)

        stop_reason = response["stopReason"]
        output_message = response["output"]["message"]
        current_messages.append(output_message)

        if stop_reason == "guardrail_intervened":
            return _GUARDRAIL_BLOCKED_REPLY, []

        if stop_reason == "end_turn":
            for block in output_message.get("content", []):
                if "text" in block:
                    text = block["text"]
                    if courses_seen:
                        text = _strip_course_prose(text)
                    return text, list(courses_seen.values())
            return "", list(courses_seen.values())

        if stop_reason == "tool_use":
            tool_results = []
            for block in output_message.get("content", []):
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    result_content = _run_tool(tool_use["name"], tool_use["input"])

                    # Collect courses returned by filter_courses
                    if tool_use["name"] == "filter_courses":
                        try:
                            returned_courses = json.loads(result_content)
                            if isinstance(returned_courses, list):
                                for c in returned_courses:
                                    dedup_key = f"{c.get('courseCode', '')}|{c.get('teachingCollege', '')}|{c.get('professors', '')}|{c.get('startDate', '')}"
                                    if dedup_key not in courses_seen:
                                        courses_seen[dedup_key] = c
                        except (json.JSONDecodeError, AttributeError):
                            pass

                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"text": result_content}],
                        }
                    })

            current_messages.append({"role": "user", "content": tool_results})

    return "I'm having trouble processing that request. Please try again.", list(courses_seen.values())


# ── Session management ────────────────────────────────────────────────────────

def get_session(session_id: str) -> dict:
    try:
        resp = _get_table().get_item(Key={"session_id": session_id})
        item = resp.get("Item")
        if item:
            # Deserialize stored messages
            if isinstance(item.get("messages"), str):
                item["messages"] = json.loads(item["messages"])
            return item
    except Exception:
        pass
    return {
        "session_id": session_id,
        "home_college": None,
        "messages": [],
        "turn_count": 0,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ttl": int(time.time()) + SESSION_TTL_SECONDS,
    }


def save_session(session: dict) -> None:
    try:
        item = dict(session)
        item["messages"] = json.dumps(item.get("messages", []))
        item["ttl"] = int(time.time()) + SESSION_TTL_SECONDS
        _get_table().put_item(Item=item)
    except Exception:
        pass


def _known_colleges() -> list[str]:
    """Return all unique teaching college names from the course dataset."""
    try:
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "courses.json"
        )
        with open(data_path) as f:
            courses = json.load(f)
        return list({c["teachingCollege"] for c in courses if c.get("teachingCollege")})
    except Exception:
        return []


def _resolve_college(raw: str) -> str:
    """
    Match a user-typed college name (possibly abbreviated) to the full canonical
    name from the dataset. Falls back to title-cased raw input if no match.
    """
    if not raw:
        return raw
    known = _known_colleges()
    raw_lower = raw.strip().lower()
    # Exact match (case-insensitive)
    for college in known:
        if college.lower() == raw_lower:
            return college
    # Substring: user typed a word that appears in a known college name
    matches = [c for c in known if raw_lower in c.lower()]
    if len(matches) == 1:
        return matches[0]
    # Known college name is a substring of what the user typed (e.g. "cuesta college ca")
    matches = [c for c in known if c.lower() in raw_lower]
    if len(matches) == 1:
        return matches[0]
    # No match — return title-cased input as-is
    return raw.strip().title()


def extract_home_college(message: str, current: str | None) -> str | None:
    if current:
        return current
    msg_lower = message.lower()
    for trigger in ["i go to", "i'm at", "i am at", "my college is", "i attend", "home college is"]:
        idx = msg_lower.find(trigger)
        if idx != -1:
            import re
            rest = message[idx + len(trigger):].strip()
            # Stop at clause conjunctions or sentence-ending punctuation
            m = re.split(r',|\band\b|\bbut\b|\bso\b|[!?;]', rest, maxsplit=1)
            college = m[0].strip().rstrip('.')
            if college:
                return _resolve_college(college)
    return None


# ── Lambda handler ────────────────────────────────────────────────────────────

def _cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Session-Id",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
        "Content-Type": "application/json",
    }


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": _cors_headers(),
        "body": json.dumps(body),
    }


def _setup_guardrail() -> dict:
    """Create or find the cvc-scope-guard guardrail using Lambda's own credentials."""
    bedrock_cp = boto3.client("bedrock", region_name=REGION)
    guardrail_name = "cvc-scope-guard"
    # Check if it already exists
    try:
        existing = bedrock_cp.list_guardrails()
        for g in existing.get("guardrails", []):
            if g["name"] == guardrail_name:
                return {"guardrailId": g["id"], "created": False}
    except Exception:
        pass
    # Create it
    resp = bedrock_cp.create_guardrail(
        name=guardrail_name,
        description="Restricts CVC chatbot to course advising topics only",
        topicPolicyConfig={
            "topicsConfig": [{
                "name": "off_topic",
                "definition": "Requests completely unrelated to courses, college enrollment, or academic advising. Includes creative writing, poems, general trivia, cooking, weather.",
                "examples": [
                    "Write me an essay about climate change",
                    "What is the capital of France?",
                    "Write a poem about flowers",
                ],
                "type": "DENY",
            }]
        },
        blockedInputMessaging=(
            "I can only help with CVC course advising — "
            "try asking me to find a course or explain a GE requirement!"
        ),
        blockedOutputsMessaging=(
            "I can only help with CVC course advising — "
            "try asking me to find a course or explain a GE requirement!"
        ),
    )
    return {"guardrailId": resp["guardrailId"], "guardrailArn": resp["guardrailArn"], "created": True}


def lambda_handler(event: dict, context) -> dict:
    # Internal setup action — invoked directly by setup_api.py, not via API Gateway
    if event.get("__action__") == "setup_guardrail":
        try:
            return _setup_guardrail()
        except Exception as e:
            return {"error": str(e)}

    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _response(200, {})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Invalid JSON body"})

    message = (body.get("message") or "").strip()
    if not message:
        return _response(400, {"error": "message is required"})

    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    session_id = (
        headers.get("x-session-id")
        or body.get("session_id")
        or str(uuid.uuid4())
    )

    session = get_session(session_id)
    session["turn_count"] = int(session.get("turn_count", 0)) + 1
    session["home_college"] = extract_home_college(message, session.get("home_college"))

    # Append user message to history
    messages = session.get("messages", [])
    messages.append({"role": "user", "content": [{"text": message}]})

    try:
        reply, courses = converse(messages)
    except Exception as exc:
        return _response(502, {"error": f"Model invocation failed: {exc}"})

    # Append assistant reply to history
    messages.append({"role": "assistant", "content": [{"text": reply}]})
    session["messages"] = messages
    save_session(session)

    return _response(200, {
        "reply": reply,
        "session_id": session_id,
        "turn_count": session["turn_count"],
        "home_college": session.get("home_college"),
        "courses": courses,
    })
