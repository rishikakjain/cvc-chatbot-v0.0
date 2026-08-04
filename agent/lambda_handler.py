"""
Lambda handler for the CVC chatbot Bedrock Agent action group.

Bedrock Agent sends a POST with an event structured as an action group invocation.
This handler routes to the three Phase 1 tools and returns a response in the
format Bedrock Agent expects.

Event shape (simplified):
    {
        "actionGroup": "cvc-tools",
        "function": "filter_courses" | "explain_ge_area" | "get_faq_answer",
        "parameters": [{"name": "...", "type": "...", "value": "..."}]
    }

Response shape:
    {
        "actionGroup": "cvc-tools",
        "function": "...",
        "functionResponse": {
            "responseBody": {
                "TEXT": {"body": "<json string of result>"}
            }
        }
    }
"""

from __future__ import annotations

import json
import os
import sys

# Allow imports from project root when deployed as a Lambda package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.filter_courses import filter_courses, summarize_course
from tools.explain_ge_area import explain_ge_area
from tools.get_faq_answer import get_faq_answer


def _params_to_dict(parameters: list[dict]) -> dict:
    """Convert Bedrock's parameter list to a plain dict."""
    return {p["name"]: p["value"] for p in (parameters or [])}


def _handle_filter_courses(params: dict) -> list[dict]:
    ge_raw = params.get("ge_areas")
    ge_areas = [c.strip() for c in ge_raw.split(",")] if ge_raw else None

    has_seats_raw = params.get("has_seats", "true")
    has_seats = str(has_seats_raw).lower() not in ("false", "0", "no")

    top_n_raw = params.get("top_n", "5")
    try:
        top_n = int(top_n_raw)
    except (ValueError, TypeError):
        top_n = 5

    courses = filter_courses(
        ge_areas=ge_areas,
        delivery_method=params.get("delivery_method"),
        exclude_college=params.get("exclude_college"),
        start_after=params.get("start_after"),
        has_seats=has_seats,
        top_n=top_n,
    )
    return [summarize_course(c) for c in courses]


def _handle_explain_ge_area(params: dict) -> dict:
    query = params.get("query", "")
    return explain_ge_area(query)


def _handle_get_faq_answer(params: dict) -> dict:
    topic = params.get("topic", "")
    return get_faq_answer(topic)


_DISPATCH = {
    "filter_courses": _handle_filter_courses,
    "explain_ge_area": _handle_explain_ge_area,
    "get_faq_answer": _handle_get_faq_answer,
}


def lambda_handler(event: dict, context) -> dict:
    action_group = event.get("actionGroup", "cvc-tools")
    function_name = event.get("function", "")
    parameters = event.get("parameters", [])

    params = _params_to_dict(parameters)

    handler = _DISPATCH.get(function_name)
    if handler is None:
        result = {"error": f"Unknown function: {function_name}"}
    else:
        try:
            result = handler(params)
        except Exception as exc:  # noqa: BLE001
            result = {"error": str(exc)}

    return {
        "actionGroup": action_group,
        "function": function_name,
        "functionResponse": {
            "responseBody": {
                "TEXT": {"body": json.dumps(result)}
            }
        },
    }
