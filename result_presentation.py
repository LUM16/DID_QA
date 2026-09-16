"""Validate a constrained, post-query presentation choice for Neo4j results."""

from __future__ import annotations

import json
import math
import re
from numbers import Number
from typing import Any, Callable

import requests
from openai import OpenAIError

Usage = dict[str, int]
Chat = Callable[[str, str], tuple[str, Usage]]

DISPLAY_TYPES = {
    "table",
    "kpi_table",
    "bar",
    "horizontal_bar",
    "line",
    "stacked_bar",
    "grouped_bar",
}
CHART_TYPES = DISPLAY_TYPES - {"table", "kpi_table"}


def _field_names(rows: list[dict[str, Any]]) -> list[str]:
    return list(dict.fromkeys(key for row in rows for key in row if isinstance(key, str)))


def _extract_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*([\s\S]*?)```", candidate, re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("Presentation selection must be a JSON object.")
    return value


def build_presentation_prompt(
    question: str, rows: list[dict[str, Any]]
) -> tuple[str, str]:
    """Build the constrained selection prompt from fields actually returned."""
    fields = _field_names(rows)
    system = """Choose a display for already-returned Neo4j rows.
Return exactly one JSON object and no markdown. You may select only exact field
names in the supplied field list. Never calculate, aggregate, rename, convert,
or transform values. Prefer table when the fields are not suitable for a chart.

Allowed responses:
- table or kpi_table:
  {"display_type":"table","table_fields":["exact_field_name"]}
- bar, horizontal_bar, line, stacked_bar, or grouped_bar:
  {"display_type":"bar","x_field":"exact_field_name",
   "y_fields":["exact_numeric_field_name"],"series_field":null,
   "table_fields":["exact_field_name"]}

For a chart, x_field and each y_fields item must be a distinct supplied field.
series_field must be null or a distinct supplied field. table_fields must be a
non-empty list of supplied fields. Use a chart only when returned values already
support it; do not derive a metric."""
    user = f"""User question:
{question}

Actual return fields (the only permitted field names):
{json.dumps(fields, ensure_ascii=False)}

Returned rows (already final; do not alter them):
{json.dumps(rows[:80], ensure_ascii=False, default=str)}"""
    return system, user


def _valid_field_list(value: Any, fields: set[str]) -> list[str] | None:
    if not isinstance(value, list) or not value:
        return None
    if any(not isinstance(item, str) or item not in fields for item in value):
        return None
    return value if len(set(value)) == len(value) else None


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool) and math.isfinite(float(value))


def _chart_fields_are_usable(
    rows: list[dict[str, Any]],
    x_field: str,
    y_fields: list[str],
    series_field: str | None,
) -> bool:
    if not rows:
        return False
    for row in rows:
        if row.get(x_field) is None:
            return False
        if series_field is not None and row.get(series_field) is None:
            return False
        if any(not _is_finite_number(row.get(field)) for field in y_fields):
            return False
    return True


def _is_temporal_field(rows: list[dict[str, Any]], field: str) -> bool:
    return bool(rows) and all(
        re.fullmatch(r"\d{4}(?:-\d{2}){0,2}", str(row.get(field) or ""))
        for row in rows
    )


def _table_payload(rows: list[dict[str, Any]], fields: list[str]) -> dict[str, Any]:
    return {
        "columns": fields,
        "rows": [{field: row.get(field) for field in fields} for row in rows],
    }


def _data_note(fields: list[str]) -> str | None:
    notes: list[str] = []
    normalized = {field.casefold() for field in fields}
    if normalized & {"hours", "recorded_hours", "time_on_hours"}:
        notes.append("Recorded TIME_ON hours.")
    if "task_count" in normalized:
        notes.append("Assigned task count.")
    return " ".join(notes) or None


def validate_presentation_selection(
    selection: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Return a render-safe payload, or None when the LLM response is invalid."""
    fields = _field_names(rows)
    field_set = set(fields)
    display_type = selection.get("display_type")
    if display_type not in DISPLAY_TYPES:
        return None

    if display_type in {"table", "kpi_table"}:
        if set(selection) != {"display_type", "table_fields"}:
            return None
        table_fields = _valid_field_list(selection.get("table_fields"), field_set)
        if table_fields is None:
            return None
        return {
            "display_type": display_type,
            "table": _table_payload(rows, table_fields),
            "data_note": _data_note(table_fields),
        }

    if set(selection) != {
        "display_type",
        "x_field",
        "y_fields",
        "series_field",
        "table_fields",
    }:
        return None
    x_field = selection.get("x_field")
    y_fields = _valid_field_list(selection.get("y_fields"), field_set)
    series_field = selection.get("series_field")
    table_fields = _valid_field_list(selection.get("table_fields"), field_set)
    if (
        not isinstance(x_field, str)
        or x_field not in field_set
        or y_fields is None
        or table_fields is None
        or (series_field is not None and (not isinstance(series_field, str) or series_field not in field_set))
        or x_field in y_fields
        or (series_field is not None and (series_field == x_field or series_field in y_fields))
        or not _chart_fields_are_usable(rows, x_field, y_fields, series_field)
        or (display_type == "line" and not _is_temporal_field(rows, x_field))
    ):
        return None

    chart_type = "line" if display_type == "line" else "bar"
    return {
        "display_type": display_type,
        "chart_type": chart_type,
        "data": rows,
        "x": x_field,
        "y": y_fields,
        "series": series_field,
        "horizontal": display_type == "horizontal_bar",
        "stack": True if display_type == "stacked_bar" else (
            False if display_type == "grouped_bar" else None
        ),
        "table": _table_payload(rows, table_fields),
        "data_note": _data_note(y_fields),
    }


def select_result_presentation(
    question: str, rows: list[dict[str, Any]], chat: Chat
) -> tuple[dict[str, Any] | None, Usage, str | None]:
    """Select presentation without allowing its failure to invalidate query results."""
    if not rows or not _field_names(rows):
        return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, None
    try:
        system, user = build_presentation_prompt(question, rows)
        raw, usage = chat(system, user)
        presentation = validate_presentation_selection(_extract_json_object(raw), rows)
        warning = (
            None
            if presentation is not None
            else "Presentation selection was invalid; showing the text answer only."
        )
        return presentation, usage, warning
    except (
        json.JSONDecodeError,
        KeyError,
        OpenAIError,
        requests.RequestException,
        RuntimeError,
        TypeError,
        ValueError,
    ):
        return (
            None,
            {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "Presentation is unavailable; showing the text answer only.",
        )
