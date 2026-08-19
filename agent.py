"""Natural-language Neo4j Q&A agent (RSC edition)."""

from __future__ import annotations

import json
import re
from typing import Any

from neo4j_client import get_schema, load_env, run_cypher
from vox_client import add_usage, chat as _chat, empty_usage

CYPHER_BLOCK = re.compile(r"```(?:cypher)?\s*([\s\S]*?)```", re.IGNORECASE)

LANGUAGE_RULE = (
    "Language policy: Match the user's question language. "
    "If the question is primarily Chinese, respond in Chinese. "
    "If the question is primarily English (or mixed with English as the main language), "
    "respond in English. Do not switch languages mid-answer unless quoting data labels."
)


def _extract_cypher(text: str) -> str:
    match = CYPHER_BLOCK.search(text)
    if match:
        return match.group(1).strip().rstrip(";")
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith(("MATCH", "CALL", "WITH", "RETURN", "OPTIONAL", "UNWIND")):
            return s.rstrip(";")
    raise ValueError(f"Could not parse Cypher from model output:\n{text}")


def generate_cypher(question: str, schema: dict[str, Any], history: list[dict[str, str]] | None = None) -> tuple[str, dict[str, int]]:
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    history_text = ""
    if history:
        recent = history[-6:]
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    system = """You are a Neo4j Cypher expert. Rewrite the user's question into one read-only Cypher query based on the given schema.
Rules:
1. Output exactly one Cypher statement inside a ```cypher code block.
2. Never use CREATE/MERGE/DELETE/SET/REMOVE/DROP or other write operations.
3. Add LIMIT for result sets (default 50) unless the user asks for a count only.
4. Study identifiers often use IPort_Study or Name (e.g. C1071007). Do not invent property names.
5. Common pattern: (:Study)-[:HAS_DELIVERY]->(:Delivery).
6. Use only property keys that appear in schema.propertyKeys.
7. Cypher keywords stay in English; do not translate labels/properties."""

    user = f"""Schema:
{schema_text}

Conversation history:
{history_text or '(none)'}

User question: {question}

Generate a read-only Cypher query."""

    raw, usage = _chat(system, user)
    return _extract_cypher(raw), usage


def answer_from_rows(question: str, cypher: str, rows: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
    payload = json.dumps(rows[:80], ensure_ascii=False, default=str)
    system = f"""You are a Neo4j graph Q&A assistant. Answer from the query results in clear natural language.
Rules:
1. {LANGUAGE_RULE}
2. Lead with the direct answer, then add brief supporting detail if useful.
3. Never invent data that is not in the results.
4. If results are empty, explain likely reasons (wrong ID, property name, or no matching data).
5. For multiple rows, use a concise list or table-style markdown.
6. Keep property/field names from the database as-is when citing them."""

    user = f"""User question: {question}

Cypher executed:
{cypher}

Query results (JSON):
{payload}

Write the answer now."""
    return _chat(system, user)


def ask(question: str, history: list[dict[str, str]] | None = None, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    load_env()
    schema = schema or get_schema()
    last_error = None
    cypher = ""
    usage = empty_usage()

    for _attempt in range(3):
        try:
            hint = f"\nPrevious Cypher failed: {last_error}" if last_error else ""
            cypher, u1 = generate_cypher(question + hint, schema, history)
            usage = add_usage(usage, u1)
            rows = run_cypher(cypher)
            answer, u2 = answer_from_rows(question, cypher, rows)
            usage = add_usage(usage, u2)
            return {
                "answer": answer,
                "cypher": cypher,
                "rows": rows,
                "schema": schema,
                "error": None,
                "usage": usage,
            }
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

    return {
        "answer": f"Query failed after 3 attempts: {last_error}",
        "cypher": cypher,
        "rows": [],
        "schema": schema,
        "error": last_error,
        "usage": usage,
    }
