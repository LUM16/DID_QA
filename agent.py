"""Natural-language Neo4j Q&A agent (RSC edition)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from neo4j_client import get_schema, load_env, run_cypher
from vox_client import add_usage, chat as _chat, empty_usage

CYPHER_BLOCK = re.compile(r"```(?:cypher)?\s*([\s\S]*?)```", re.IGNORECASE)
APP_ROOT = Path(__file__).resolve().parent
DOCS_ROOT = APP_ROOT / "docs"
EXAMPLES_ROOT = DOCS_ROOT / "examples"

EXAMPLE_KEYWORDS = {
    "person_productivity.md": ("person", "productivity", "hands-on", "hour", "workload", "ntid", "员工", "工时"),
    "workload_planning.md": ("capacity", "plan", "planned", "ongoing", "workload", "resource", "规划", "负载"),
    "study_delivery.md": ("study", "delivery", "did", "status", "里程碑", "交付"),
    "lot_tlf_sdtm_adam.md": ("lot", "tlf", "sdtm", "adam", "submission", "产出物"),
    "team_manager.md": ("manager", "group lead", "ta lead", "team", "reports to", "经理", "团队"),
    "reporting_dashboard.md": ("dashboard", "kpi", "trend", "monthly", "reporting", "看板", "报表"),
}
DEFAULT_EXAMPLES = ("query_index.md", "study_delivery.md", "workload_planning.md")
SKILL_MAX_CHARS = 6000
SCHEMA_MAX_CHARS = 12000
EXAMPLE_MAX_CHARS = 5000

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


@lru_cache(maxsize=64)
def _read_doc(relative_path: str) -> str:
    p = DOCS_ROOT / relative_path
    if not p.exists():
        raise FileNotFoundError(f"Missing prompt doc: {p}")
    return p.read_text(encoding="utf-8")


def _select_examples(question: str, limit: int = 3) -> list[str]:
    q = question.lower()
    scored: list[tuple[int, str]] = []
    for filename, keywords in EXAMPLE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in q)
        if score > 0:
            scored.append((score, filename))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [name for _, name in scored[:limit]]
    if len(selected) < limit:
        for fallback in DEFAULT_EXAMPLES:
            if fallback not in selected:
                selected.append(fallback)
            if len(selected) >= limit:
                break
    return selected[:limit]


def _build_domain_context(question: str) -> str:
    skill_text = _read_doc("skill.md")[:SKILL_MAX_CHARS]
    schema_text = _read_doc("schema.md")[:SCHEMA_MAX_CHARS]
    parts = [
        "Domain guidance from docs/skill.md:",
        skill_text,
        "",
        "Domain schema reference from docs/schema.md:",
        schema_text,
    ]

    for filename in _select_examples(question):
        example_path = EXAMPLES_ROOT / filename
        example_text = _read_doc(f"examples/{filename}")[:EXAMPLE_MAX_CHARS]
        parts.extend(
            [
                "",
                f"Few-shot reference from {example_path.as_posix()}:",
                example_text,
            ]
        )
    return "\n".join(parts)


def generate_cypher(question: str, schema: dict[str, Any], history: list[dict[str, str]] | None = None) -> tuple[str, dict[str, int]]:
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    domain_context = _build_domain_context(question)
    history_text = ""
    if history:
        recent = history[-6:]
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    system = """You are a DID Neo4j Cypher expert. Rewrite the user's question into one read-only Cypher query based on the given schema and domain examples.
Rules:
1. Output exactly one Cypher statement inside a ```cypher code block.
2. Never use CREATE/MERGE/DELETE/SET/REMOVE/DROP or other write operations.
3. Add LIMIT for result sets (default 50) unless the user asks for a count only.
4. Study identifiers often use IPort_Study or Name (e.g. C1071007). Do not invent property names.
5. Common pattern: (:Study)-[:HAS_DELIVERY]->(:Delivery).
6. Use only property keys that appear in schema.propertyKeys.
7. Cypher keywords stay in English; do not translate labels/properties.
8. Follow rules and safe patterns from docs/skill.md and docs/examples/*.md.
9. Do not generate employee ranking/performance-scoring queries."""

    user = f"""Schema:
{schema_text}

Domain context:
{domain_context}

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
