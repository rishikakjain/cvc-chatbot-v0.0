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
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-haiku-4-5-20251001-v1:0")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "cvc_sessions")
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

def converse(messages: list[dict]) -> str:
    """
    Run the Bedrock Converse API tool-use loop.
    Returns the final text reply from Claude.
    """
    client = _get_bedrock()
    system_prompt = _load_system_prompt()

    current_messages = list(messages)

    for _ in range(10):  # max 10 tool-use rounds
        response = client.converse(
            modelId=MODEL_ID,
            system=[{"text": system_prompt}],
            messages=current_messages,
            toolConfig=TOOL_CONFIG,
        )

        stop_reason = response["stopReason"]
        output_message = response["output"]["message"]
        current_messages.append(output_message)

        if stop_reason == "end_turn":
            # Extract text from the response
            for block in output_message.get("content", []):
                if "text" in block:
                    return block["text"]
            return ""

        if stop_reason == "tool_use":
            tool_results = []
            for block in output_message.get("content", []):
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    result_content = _run_tool(tool_use["name"], tool_use["input"])
                    tool_results.append({
                        "toolResult": {
                            "toolUseId": tool_use["toolUseId"],
                            "content": [{"text": result_content}],
                        }
                    })

            current_messages.append({"role": "user", "content": tool_results})

    return "I'm having trouble processing that request. Please try again."


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


def extract_home_college(message: str, current: str | None) -> str | None:
    if current:
        return current
    msg_lower = message.lower()
    for trigger in ["i go to", "i'm at", "i am at", "my college is", "i attend", "home college is"]:
        idx = msg_lower.find(trigger)
        if idx != -1:
            college = message[idx + len(trigger):].strip().rstrip(".,!?")
            if college:
                return college.title()
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


def lambda_handler(event: dict, context) -> dict:
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
        reply = converse(messages)
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
    })
