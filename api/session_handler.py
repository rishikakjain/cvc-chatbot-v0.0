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
                            "ztc": {
                                "type": "boolean",
                                "description": "If true, only return Zero Textbook Cost (ZTC) courses. Only set when student explicitly asks for free-textbook or ZTC courses.",
                            },
                            "top_n": {
                                "type": "integer",
                                "description": "Max results to return (default 5).",
                            },
                            "region": {
                                "type": "string",
                                "enum": [
                                    "Bay Area", "Los Angeles Metro", "San Diego",
                                    "Central Valley", "Central Coast", "Inland Empire",
                                    "Sacramento/Sierra", "North State"
                                ],
                                "description": "Geographic region of California to filter teaching colleges. Use instead of or alongside max_distance_miles.",
                            },
                            "max_duration_weeks": {
                                "type": "integer",
                                "description": "Maximum course duration in weeks (e.g. 8, 10, 16). Omit for no limit.",
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

def _run_tool(name: str, tool_input: dict, context: dict | None = None) -> str:
    ctx = context or {}
    if name == "filter_courses":
        ge_raw = tool_input.get("ge_areas")
        ge_areas = [c.strip() for c in ge_raw.split(",")] if ge_raw else None
        has_seats = tool_input.get("has_seats", True)
        if isinstance(has_seats, str):
            has_seats = has_seats.lower() not in ("false", "0", "no")
        ztc = tool_input.get("ztc", False)
        if isinstance(ztc, str):
            ztc = ztc.lower() in ("true", "1", "yes")
        # OR in the frontend ZTC chip — either signal enables the filter
        ztc = ztc or bool(ctx.get("ztc_filter", False))
        top_n = int(tool_input.get("top_n", 5))
        tool_duration = tool_input.get("max_duration_weeks")
        ctx_duration = ctx.get("max_duration_weeks")
        effective_duration = tool_duration if tool_duration is not None else (int(ctx_duration) if ctx_duration is not None else None)

        courses = filter_courses(
            ge_areas=ge_areas,
            subject_keyword=tool_input.get("subject_keyword"),
            delivery_method=tool_input.get("delivery_method"),
            exclude_college=tool_input.get("exclude_college"),
            start_after=tool_input.get("start_after"),
            has_seats=has_seats,
            ztc=ztc,
            top_n=top_n,
            max_distance_miles=ctx.get("max_distance_miles"),
            home_college_name=ctx.get("home_college"),
            condensed_only=bool(ctx.get("condensed_only", False)),
            max_duration_weeks=effective_duration,
            region=tool_input.get("region") or ctx.get("region"),
        )
        return json.dumps([summarize_course(c) for c in courses])

    if name == "explain_ge_area":
        return json.dumps(explain_ge_area(tool_input.get("query", "")))

    if name == "get_faq_answer":
        return json.dumps(get_faq_answer(tool_input.get("topic", "")))

    return json.dumps({"error": f"Unknown tool: {name}"})


# ── Converse API loop ─────────────────────────────────────────────────────────

def _strip_course_prose(text: str, has_courses: bool = True) -> str:
    """
    Normalise the model reply after filter_courses was called.

    With courses (has_courses=True): keep only the first intro sentence +
    action-verb numbered follow-ups. Everything else is on the cards.

    Without courses (has_courses=False): keep plain prose sentences but
    strip markdown tables (| lines) and bullet lists (- / * lines), which
    the model uses to describe why nothing was found. Numbered follow-ups
    are always kept.
    """
    import re
    followup_action = re.compile(
        r'^\d+\.\s+\*{0,2}(search|show|filter|find|explain|tell|compare|narrow|look|get|see|ask|check|help|what|how|which|can you|display)',
        re.I
    )

    if has_courses:
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
                first_sentence = re.split(r':\s*$', t)[0]
                intro = first_sentence
        parts = []
        if intro:
            parts.append(intro.rstrip('.') + '.')
        if numbered:
            parts.extend(numbered)
        return '\n'.join(parts).strip()
    else:
        # Zero-results path: strip bullets/tables but keep prose + numbered options
        kept = []
        for line in text.splitlines():
            t = line.strip()
            if not t:
                kept.append('')
                continue
            # Drop markdown table rows and bullet lines
            if t.startswith('|') or re.match(r'^[-*•]{1,2}\s', t) or re.match(r'^---', t):
                continue
            # Strip bold headers like "**No courses found**" on their own line
            if re.match(r'^\*{2}[^*]+\*{2}$', t):
                continue
            # Keep numbered options and plain prose
            kept.append(line)
        # Collapse multiple blank lines
        result = re.sub(r'\n{3,}', '\n\n', '\n'.join(kept))
        return result.strip()


def _strip_bullets_only(text: str) -> str:
    """
    For replies that didn't call filter_courses: strip markdown tables and
    bullet lines (- / * / •), keeping prose and numbered options intact.
    Only applies when the reply contains numbered options (1. ...) — leaves
    purely-prose replies like GE explanations and FAQs untouched.
    """
    import re
    if not re.search(r'^\d+\.', text, re.MULTILINE):
        return text  # no numbered options → leave as-is (GE explanation, FAQ, etc.)
    kept = []
    for line in text.splitlines():
        t = line.strip()
        if not t:
            kept.append('')
            continue
        if t.startswith('|') or re.match(r'^[-*•]{1,2}\s', t) or re.match(r'^---', t):
            continue
        if re.match(r'^\*{2}[^*]+\*{2}$', t):
            continue
        kept.append(line)
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(kept)).strip()


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
    except Exception as e:
        # Log so CloudWatch shows the real error; fail closed to block the request
        print(f"[guardrail] apply_guardrail failed (GUARDRAIL_ID={GUARDRAIL_ID}): {e}")
        return True


def converse(messages: list[dict], context: dict | None = None) -> tuple[str, list[dict]]:
    """
    Run the Bedrock Converse API tool-use loop.
    Returns (final_text_reply, courses) where courses is a list of course dicts
    collected from any filter_courses tool calls made during this turn.
    context: optional dict with keys like 'home_college' and 'max_distance_miles'
             injected into every filter_courses call.
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
    filter_was_called = False  # True even if filter returned 0 results

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
                    if filter_was_called:
                        text = _strip_course_prose(text, has_courses=bool(courses_seen))
                    else:
                        text = _strip_bullets_only(text)
                    return text, list(courses_seen.values())
            return "", list(courses_seen.values())

        if stop_reason == "tool_use":
            tool_results = []
            for block in output_message.get("content", []):
                if "toolUse" in block:
                    tool_use = block["toolUse"]
                    result_content = _run_tool(tool_use["name"], tool_use["input"], context)

                    # Collect courses returned by filter_courses
                    if tool_use["name"] == "filter_courses":
                        filter_was_called = True
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
        from tools.filter_courses import load_courses
        courses = load_courses()
        return list({c["teachingCollege"] for c in courses if c.get("teachingCollege")})
    except Exception:
        return []


def _all_ca_colleges() -> list[str]:
    """
    Return all California Community College names as the candidate list for matching.
    Uses the full static location list (115 colleges) so home college resolution
    works for any CCC student, not just the colleges currently in the course data.
    """
    from data.college_locations import COLLEGE_LOCATIONS
    # Title-case the keys (they're stored lowercase in the dict)
    # Deduplicate canada/cañada variants
    seen = set()
    result = []
    for key in COLLEGE_LOCATIONS:
        title = key.title()
        if title not in seen:
            seen.add(title)
            result.append(title)
    return result


def _resolve_college(raw: str) -> str:
    """
    Match a user-typed college name (possibly abbreviated or misspelled) to the
    full canonical California Community College name.
    Matching order: exact → substring → fuzzy (difflib) → title-cased raw input.
    """
    import difflib
    if not raw:
        return raw
    known = _all_ca_colleges()
    raw_lower = raw.strip().lower()
    known_lower = [c.lower() for c in known]

    # 1. Exact match (case-insensitive)
    for i, cl in enumerate(known_lower):
        if cl == raw_lower:
            return known[i]

    # 2. User input is a substring of a known name, or vice versa
    matches = [known[i] for i, cl in enumerate(known_lower) if raw_lower in cl]
    if len(matches) == 1:
        return matches[0]
    matches = [known[i] for i, cl in enumerate(known_lower) if cl in raw_lower]
    if len(matches) == 1:
        return matches[0]

    # 3. Fuzzy match — handles typos like "Victore Valley", "Questa College", "De Ansa"
    # Also compare against name-only forms (strip "college"/"community college" suffix)
    # so short queries like "de ansa" aren't penalized by the length of "de anza college"
    _SUFFIXES = (" community college", " junior college", " college", " cc")

    def _name_only(s: str) -> str:
        for suffix in _SUFFIXES:
            if s.endswith(suffix):
                return s[: -len(suffix)].strip()
        return s

    raw_name = _name_only(raw_lower)
    best_idx, best_ratio = -1, 0.0
    for i, cl in enumerate(known_lower):
        r1 = difflib.SequenceMatcher(None, raw_lower, cl).ratio()
        r2 = difflib.SequenceMatcher(None, raw_name, _name_only(cl)).ratio()
        r = max(r1, r2)
        if r > best_ratio:
            best_ratio, best_idx = r, i

    if best_ratio >= 0.72 and best_idx >= 0:
        return known[best_idx]

    # 4. No match — return title-cased input as-is
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
    """Create (or update) the cvc-scope-guard guardrail using Lambda's own credentials."""
    bedrock_cp = boto3.client("bedrock", region_name=REGION)
    guardrail_name = "cvc-scope-guard"

    blocked_msg = (
        "I'm only able to help with CVC course advising — "
        "finding online courses, explaining GE requirements, or answering enrollment questions. "
        "Try asking me to search for a course or explain an area like CSU B2!"
    )

    topic_policy = {
        "topicsConfig": [
            {
                "name": "off_topic",
                "definition": (
                    "Any request unrelated to CVC courses, GE requirements, or "
                    "CC enrollment. Includes trivia, creative writing, coding, "
                    "and personal advice."
                ),
                "examples": [
                    "What is 7 times 8?",
                    "What is the capital of France?",
                    "Help me write a cover letter.",
                    "Debug my Python code.",
                    "Tell me a joke.",
                ],
                "type": "DENY",
            },
        ]
    }

    # Check if already exists — update it, otherwise create
    existing = bedrock_cp.list_guardrails()
    for g in existing.get("guardrails", []):
        if g["name"] == guardrail_name:
            gid = g["id"]
            bedrock_cp.update_guardrail(
                guardrailIdentifier=gid,
                name=guardrail_name,
                description="Restricts CVC chatbot to course advising topics only",
                topicPolicyConfig=topic_policy,
                blockedInputMessaging=blocked_msg,
                blockedOutputsMessaging=blocked_msg,
            )
            return {"guardrailId": gid, "created": False, "updated": True}

    resp = bedrock_cp.create_guardrail(
        name=guardrail_name,
        description="Restricts CVC chatbot to course advising topics only",
        topicPolicyConfig=topic_policy,
        blockedInputMessaging=blocked_msg,
        blockedOutputsMessaging=blocked_msg,
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

    # Persist frontend filters across turns; use current session value as fallback
    max_distance = body.get("max_distance_miles", session.get("max_distance_miles"))
    ztc_filter = body.get("ztc_filter", session.get("ztc_filter", False))
    condensed_only = body.get("condensed_only", session.get("condensed_only", False))
    max_duration_weeks = body.get("max_duration_weeks", session.get("max_duration_weeks"))
    region = body.get("region", session.get("region"))
    session["max_distance_miles"] = max_distance
    session["ztc_filter"] = ztc_filter
    session["condensed_only"] = condensed_only
    session["max_duration_weeks"] = max_duration_weeks
    session["region"] = region

    # Append user message to history
    messages = session.get("messages", [])
    messages.append({"role": "user", "content": [{"text": message}]})

    context = {
        "home_college": session.get("home_college"),
        "max_distance_miles": session.get("max_distance_miles"),
        "ztc_filter": session.get("ztc_filter", False),
        "condensed_only": session.get("condensed_only", False),
        "max_duration_weeks": session.get("max_duration_weeks"),
        "region": session.get("region"),
    }

    try:
        reply, courses = converse(messages, context)
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
