"""Natural-language Neo4j Q&A agent (RSC edition)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from effort_prediction import predict_effort
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
DEFAULT_EXAMPLES = (
    "query_index.md",
    "study_delivery.md",
    "workload_planning.md",
    "person_productivity.md",
    "lot_tlf_sdtm_adam.md",
    "team_manager.md",
    "reporting_dashboard.md",
    "uncategorized.md",
)
SAFE_EXAMPLE_FILES = tuple(
    name for name in DEFAULT_EXAMPLES if name != "sensitive_excluded.md"
)
SKILL_MAX_CHARS = 6000
SCHEMA_MAX_CHARS = 12000
EXAMPLE_MAX_CHARS = 5000

LANGUAGE_RULE = (
    "Language policy: Match the user's question language. "
    "If the question is primarily Chinese, respond in Chinese. "
    "If the question is primarily English (or mixed with English as the main language), "
    "respond in English. Do not switch languages mid-answer unless quoting data labels."
)

EFFORT_PREDICTION_PATTERNS = (
    r"预测",
    r"预计",
    r"预估",
    r"估算.*(?:工时|时间|小时)",
    r"需要多久",
    r"还需要多少.*(?:工时|时间|小时)",
    r"\bforecast\b",
    r"\bpredict(?:ion)?\b",
    r"\bestimat(?:e|ed|ion)\b.*\b(?:effort|hours?|time)\b",
    r"\bhow long will\b",
    r"\bexpected (?:effort|hours?|time)\b",
)
DID_PATTERN = re.compile(r"\b[A-Za-z][A-Za-z0-9-]*_\d+\b")
ISO_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _extract_cypher(text: str) -> str:
    match = CYPHER_BLOCK.search(text)
    if match:
        return match.group(1).strip().rstrip(";")
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith(("MATCH", "CALL", "WITH", "RETURN", "OPTIONAL", "UNWIND")):
            return s.rstrip(";")
    raise ValueError(f"Could not parse Cypher from model output:\n{text}")


def _is_effort_prediction_question(question: str) -> bool:
    return any(
        re.search(pattern, question, re.IGNORECASE)
        for pattern in EFFORT_PREDICTION_PATTERNS
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", stripped, re.IGNORECASE)
    if fenced:
        stripped = fenced.group(1).strip()
    else:
        match = re.search(r"\{[\s\S]*\}", stripped)
        if match:
            stripped = match.group(0)
    payload = json.loads(stripped)
    if not isinstance(payload, dict):
        raise ValueError("Prediction parameter response must be a JSON object.")
    return payload


def _extract_effort_parameters_locally(
    question: str,
) -> dict[str, str | None] | None:
    did_match = DID_PATTERN.search(question)
    if not did_match:
        return None

    prefix = question[: did_match.start()].strip(" ,，:：")
    prefix = re.sub(
        r"^(?:请|请帮我|帮我)?\s*(?:预测|预计|预估|估算)\s*",
        "",
        prefix,
        flags=re.IGNORECASE,
    )
    prefix = re.sub(
        r"^(?:please\s+)?(?:predict|forecast|estimate)\s+",
        "",
        prefix,
        flags=re.IGNORECASE,
    )
    person = re.sub(
        r"(?:的)?\s*(?:完成|做|负责|对于|对)\s*$",
        "",
        prefix,
        flags=re.IGNORECASE,
    )
    person = re.sub(
        r"(?:'s|’s)?\s*(?:total\s+)?(?:effort|hours?|time)?\s*(?:for|on)\s*$",
        "",
        person,
        flags=re.IGNORECASE,
    ).strip(" ,，:：'\"")
    if not person:
        return None
    date_match = ISO_DATE_PATTERN.search(question)
    return {
        "person": person,
        "did": did_match.group(0),
        "as_of_date": date_match.group(0) if date_match else None,
    }


def extract_effort_prediction_parameters(
    question: str, history: list[dict[str, str]] | None = None
) -> tuple[dict[str, str | None], dict[str, int]]:
    local_parameters = _extract_effort_parameters_locally(question)
    if local_parameters:
        return local_parameters, empty_usage()

    history_text = ""
    if history:
        history_text = "\n".join(
            f"{message['role']}: {message['content']}" for message in history[-6:]
        )
    system = """Extract parameters for a DID effort prediction request.
Return exactly one JSON object with these keys:
{"person": string|null, "did": string|null, "as_of_date": "YYYY-MM-DD"|null}
Rules:
1. Copy the person name or nickname exactly as the user supplied it.
2. Copy the DID exactly as supplied.
3. Do not invent missing values.
4. Use conversation history only to resolve an explicitly referenced prior person or DID.
5. Do not add markdown or explanation."""
    user = f"""Conversation history:
{history_text or '(none)'}

Current request:
{question}"""
    raw, usage = _chat(system, user, temperature=0)
    payload = _extract_json_object(raw)
    person = payload.get("person")
    did = payload.get("did")
    as_of_date = payload.get("as_of_date")
    if not isinstance(person, str) or not person.strip():
        raise ValueError("The prediction request is missing a person name.")
    if not isinstance(did, str) or not did.strip():
        raise ValueError("The prediction request is missing a DID.")
    if as_of_date is not None and not isinstance(as_of_date, str):
        raise ValueError("as_of_date must be YYYY-MM-DD or null.")
    return {
        "person": person.strip(),
        "did": did.strip(),
        "as_of_date": as_of_date,
    }, usage


def _format_effort_prediction(
    prediction: dict[str, Any], question: str
) -> str:
    chinese = bool(re.search(r"[\u4e00-\u9fff]", question))
    similar = prediction.get("similar_historical_dids") or []
    warnings = prediction.get("warnings") or []
    if chinese:
        lines = [
            (
                f"预计 **{prediction['person']}** 完成 **{prediction['did']}** 的总工时："
                f"**P50 {prediction['p50_hours']} 小时**、"
                f"**P80 {prediction['p80_hours']} 小时**、"
                f"**P90 {prediction['p90_hours']} 小时**。"
            ),
            "",
            "日常资源规划建议参考 P80；P90 适合更保守的高风险规划。",
            f"该人员在预测日期前有 {prediction['person_completed_did_count']} 个可用历史 DID。",
        ]
        if similar:
            lines.extend(["", "最相似的历史案例："])
            lines.extend(
                (
                    f"- {item['did']}：实际 {item['actual_hours']} 小时，"
                    f"精确总体相似度 {item['overall_similarity']:.1%}，"
                    f"TLF标题近似度 {item['tlf_semantic_similarity']:.1%}"
                )
                for item in similar[:3]
            )
        if warnings:
            lines.extend(["", "注意：", *[f"- {warning}" for warning in warnings]])
        lines.extend(["", f"模型版本：`{prediction['model_version']}`"])
        return "\n".join(lines)

    lines = [
        (
            f"Estimated total effort for **{prediction['person']}** on "
            f"**{prediction['did']}**: **P50 {prediction['p50_hours']} hours**, "
            f"**P80 {prediction['p80_hours']} hours**, and "
            f"**P90 {prediction['p90_hours']} hours**."
        ),
        "",
        "Use P80 for routine capacity planning and P90 for more conservative, high-risk planning.",
        (
            f"The person has {prediction['person_completed_did_count']} eligible "
            "historical DIDs before the prediction date."
        ),
    ]
    if similar:
        lines.extend(["", "Most similar historical cases:"])
        lines.extend(
            (
                f"- {item['did']}: {item['actual_hours']} actual hours, "
                f"{item['overall_similarity']:.1%} exact overall similarity, "
                f"{item['tlf_semantic_similarity']:.1%} TLF title similarity"
            )
            for item in similar[:3]
        )
    if warnings:
        lines.extend(["", "Warnings:", *[f"- {warning}" for warning in warnings]])
    lines.extend(["", f"Model version: `{prediction['model_version']}`"])
    return "\n".join(lines)


def answer_effort_prediction(
    question: str, history: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    parameters, usage = extract_effort_prediction_parameters(question, history)
    prediction = predict_effort(
        person=str(parameters["person"]),
        did=str(parameters["did"]),
        as_of_date=parameters["as_of_date"],
    )
    return {
        "answer": _format_effort_prediction(prediction, question),
        "cypher": "",
        "rows": [prediction],
        "schema": None,
        "error": None,
        "usage": usage,
        "prediction": prediction,
    }


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

    selected = _select_examples(question)
    for filename in (*selected, *[name for name in SAFE_EXAMPLE_FILES if name not in selected]):
        example_path = EXAMPLES_ROOT / filename
        if not example_path.exists():
            continue
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
8. Follow rules and safe patterns from docs/skill.md, docs/schema.md, and docs/examples/*.md (ignore sensitive_excluded.md).
9. Prefer business query patterns from person_productivity.md, workload_planning.md, study_delivery.md, lot_tlf_sdtm_adam.md, team_manager.md, reporting_dashboard.md, and query_index.md.
10. Do not generate employee ranking/performance-scoring queries."""

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


def repair_cypher(question: str, schema: dict[str, Any], previous_cypher: str, previous_rows: list[dict[str, Any]], history: list[dict[str, str]] | None = None) -> tuple[str, dict[str, int]]:
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)
    history_text = ""
    if history:
        recent = history[-6:]
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in recent)

    system = """You are a Neo4j query repair assistant. The previous Cypher query returned no data, but the user likely expects business results. Fix the query by keeping it read-only and using only valid property names from the schema.
Rules:
1. Output exactly one Cypher statement inside a ```cypher code block.
2. Do not invent property names; follow schema.propertyKeys exactly.
3. Correct common date bugs: use `Planned_Delivery_Date` / `Actual_Delivery_Date` and filter on the actual date field instead of a transformed or missing property.
4. Keep the business date filter in the WHERE clause or MATCH path, and do not hide it inside an OPTIONAL MATCH without a real predicate.
5. When the question mentions a month or year, apply the filter to the date field and keep it aligned with the user’s requested period.
6. Preserve the original business intent and return the relevant rows.
7. Prefer the safe patterns from docs/skill.md and docs/examples/*.md (skip sensitive_excluded.md).
8. Never use CREATE/MERGE/DELETE/SET/REMOVE/DROP or other write operations."""

    user = f"""Schema:
{schema_text}

Conversation history:
{history_text or '(none)'}

User question: {question}

Previous Cypher:
{previous_cypher}

Previous query returned zero rows.

Use the schema and business intent to repair the query so it returns the expected data for the asked period.

Generate a corrected read-only Cypher query."""

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


def _needs_repair(question: str, rows: list[dict[str, Any]], cypher: str) -> bool:
    if rows:
        return False
    q = question.lower()
    date_keywords = (
        "august",
        "september",
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "month",
        "year",
        "planned delivery",
        "actual delivery",
        "delivery date",
        "delivered",
        "delivery",
    )
    if any(keyword in q for keyword in date_keywords):
        return True
    return "optional match" in cypher.lower() and "where" in cypher.lower()


def ask(question: str, history: list[dict[str, str]] | None = None, schema: dict[str, Any] | None = None) -> dict[str, Any]:
    load_env()
    if _is_effort_prediction_question(question):
        try:
            result = answer_effort_prediction(question, history)
            result["schema"] = schema
            return result
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            return {
                "answer": f"Effort prediction failed: {error}",
                "cypher": "",
                "rows": [],
                "schema": schema,
                "error": error,
                "usage": empty_usage(),
            }

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

            if not rows and _needs_repair(question, rows, cypher):
                repaired, u_repair = repair_cypher(question, schema, cypher, rows, history)
                usage = add_usage(usage, u_repair)
                rows = run_cypher(repaired)
                cypher = repaired

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
