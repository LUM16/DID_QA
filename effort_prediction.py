"""Train and run person-by-DID effort forecasts from read-only Neo4j data."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from neo4j_client import get_driver, load_env

MODEL_VERSION = "did-effort-ridge-v1"
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent / "artifacts" / "did_effort_model.joblib"
)

TASK_FIELDS = (
    "task_count",
    "task_generation_count",
    "task_qc_count",
    "tlf_count",
    "tlf_generation_count",
    "tlf_qc_count",
    "adam_count",
    "adam_generation_count",
    "adam_qc_count",
    "sdtm_count",
    "sdtm_generation_count",
    "sdtm_qc_count",
)

NUMERIC_FEATURES = [
    *TASK_FIELDS,
    "person_completed_count",
    "person_median_hours",
    "person_recent_median_hours",
    "person_median_hours_per_task",
    "global_completed_count",
    "global_median_hours",
    "global_median_hours_per_task",
    "tlf_prior_overlap_count",
    "adam_prior_overlap_count",
    "sdtm_prior_overlap_count",
    "max_tlf_similarity",
    "max_adam_similarity",
    "max_sdtm_similarity",
    "max_overall_similarity",
    "days_since_similar_work",
]

CATEGORICAL_FEATURES = [
    "ta",
    "study_type",
    "reporting_event",
    "draft_or_final",
]

TRAINING_QUERY = """
MATCH (p:Person)-[wo:WORKS_ON]->(d:Delivery)
WHERE toLower(toString(d.DID_Status)) = 'completed'
  AND p.Name = $person
WITH p, d,
     count(wo) AS workOnRelCount,
     max(toFloat(coalesce(wo.Task_Num_Total, wo.CSR_Task_Num_Total))) AS taskCount,
     max(toFloat(coalesce(wo.Task_Num_Generation, wo.CSR_Task_Num_Generation))) AS taskGenerationCount,
     max(toFloat(coalesce(wo.Task_Num_QC, wo.CSR_Task_Num_QC))) AS taskQcCount,
     max(toFloat(coalesce(wo.TLF_Num_Total, wo.CSR_TLF_Num_Total))) AS tlfCount,
     max(toFloat(coalesce(wo.TLF_Num_Generation, wo.CSR_TLF_Num_Generation))) AS tlfGenerationCount,
     max(toFloat(coalesce(wo.TLF_Num_QC, wo.CSR_TLF_Num_QC))) AS tlfQcCount,
     max(toFloat(coalesce(wo.ADaM_Num_Total, wo.CSR_ADaM_Num_Total))) AS adamCount,
     max(toFloat(coalesce(wo.ADaM_Num_Generation, wo.CSR_ADaM_Num_Generation))) AS adamGenerationCount,
     max(toFloat(coalesce(wo.ADaM_Num_QC, wo.CSR_ADaM_Num_QC))) AS adamQcCount,
     max(toFloat(coalesce(wo.SDTM_Num_Total, wo.CSR_SDTM_Num_Total))) AS sdtmCount,
     max(toFloat(coalesce(wo.SDTM_Num_Generation, wo.CSR_SDTM_Num_Generation))) AS sdtmGenerationCount,
     max(toFloat(coalesce(wo.SDTM_Num_QC, wo.CSR_SDTM_Num_QC))) AS sdtmQcCount
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WITH p, d, workOnRelCount, taskCount, taskGenerationCount, taskQcCount,
     tlfCount, tlfGenerationCount, tlfQcCount,
     adamCount, adamGenerationCount, adamQcCount,
     sdtmCount, sdtmGenerationCount, sdtmQcCount,
     collect(DISTINCT s) AS studies
WITH p, d, workOnRelCount, taskCount, taskGenerationCount, taskQcCount,
     tlfCount, tlfGenerationCount, tlfQcCount,
     adamCount, adamGenerationCount, adamQcCount,
     sdtmCount, sdtmGenerationCount, sdtmQcCount,
     head(studies) AS s, size(studies) AS studyCount
CALL {
  WITH p, d
  OPTIONAL MATCH (p)-[time:TIME_ON]->(dm:DIDN_Month)-[:BELONGS_TO]->(d)
  RETURN sum(toFloat(time.Hour)) AS actualHours,
         count(time) AS timeRecordCount
}
CALL {
  WITH s
  OPTIONAL MATCH (s)-[:HAS_DETAIL]->(si:Study_Info)
  RETURN head(collect(DISTINCT si.TA)) AS ta,
         head(collect(DISTINCT si.Study_Type)) AS studyType
}
CALL {
  WITH d
  OPTIONAL MATCH (d)-[rel:HAS_TLF]->(item:TLF)
  RETURN collect(DISTINCT {
    name: item.Name, category: item.Category, type: item.Type,
    source: item.Source, generation: rel.Generation, qc: rel.QC
  }) AS tlfs
}
CALL {
  WITH d
  OPTIONAL MATCH (d)-[rel:HAS_ADAM]->(item:ADaM)
  RETURN collect(DISTINCT {
    name: item.Name, category: item.Category, type: item.Type,
    generation: rel.Generation, qc: rel.QC
  }) AS adams
}
CALL {
  WITH d
  OPTIONAL MATCH (d)-[rel:HAS_SDTM]->(item:SDTM)
  RETURN collect(DISTINCT {
    name: item.Name, category: item.Category, type: item.Type,
    generation: rel.Generation, qc: rel.QC
  }) AS sdtms
}
RETURN p.Name AS person, d.DID AS did, s.Name AS study,
       substring(toString(d.Actual_Delivery_Date), 0, 10) AS completion_date,
       actualHours AS actual_hours,
       taskCount AS task_count,
       taskGenerationCount AS task_generation_count,
       taskQcCount AS task_qc_count,
       tlfCount AS tlf_count,
       tlfGenerationCount AS tlf_generation_count,
       tlfQcCount AS tlf_qc_count,
       adamCount AS adam_count,
       adamGenerationCount AS adam_generation_count,
       adamQcCount AS adam_qc_count,
       sdtmCount AS sdtm_count,
       sdtmGenerationCount AS sdtm_generation_count,
       sdtmQcCount AS sdtm_qc_count,
       ta, studyType AS study_type,
       d.Reporting_Event AS reporting_event,
       d.Draft_or_Final AS draft_or_final,
       tlfs, adams, sdtms,
       workOnRelCount AS work_on_rel_count,
       studyCount AS study_count,
       timeRecordCount AS time_record_count
ORDER BY completion_date, did, person
"""

TRAINING_PEOPLE_QUERY = """
MATCH (p:Person)-[:WORKS_ON]->(d:Delivery)
WHERE toLower(toString(d.DID_Status)) = 'completed'
  AND p.Name IS NOT NULL
RETURN DISTINCT p.Name AS person
ORDER BY person
"""

TARGET_QUERY = """
MATCH (p:Person)-[wo:WORKS_ON]->(d:Delivery)
WHERE replace(toUpper(toString(p.Name)), ' ', '') =
      replace(toUpper($person), ' ', '')
   OR replace(toUpper(toString(p.Name)), ' ', '') CONTAINS
      replace(toUpper($person), ' ', '')
WITH p, wo, d
WHERE toString(d.DID) = toString($did)
  AND toLower(toString(d.DID_Status)) IN ['planned', 'ongoing']
WITH p, d,
     count(wo) AS workOnRelCount,
     max(toFloat(coalesce(wo.Task_Num_Total, wo.CSR_Task_Num_Total))) AS taskCount,
     max(toFloat(coalesce(wo.Task_Num_Generation, wo.CSR_Task_Num_Generation))) AS taskGenerationCount,
     max(toFloat(coalesce(wo.Task_Num_QC, wo.CSR_Task_Num_QC))) AS taskQcCount,
     max(toFloat(coalesce(wo.TLF_Num_Total, wo.CSR_TLF_Num_Total))) AS tlfCount,
     max(toFloat(coalesce(wo.TLF_Num_Generation, wo.CSR_TLF_Num_Generation))) AS tlfGenerationCount,
     max(toFloat(coalesce(wo.TLF_Num_QC, wo.CSR_TLF_Num_QC))) AS tlfQcCount,
     max(toFloat(coalesce(wo.ADaM_Num_Total, wo.CSR_ADaM_Num_Total))) AS adamCount,
     max(toFloat(coalesce(wo.ADaM_Num_Generation, wo.CSR_ADaM_Num_Generation))) AS adamGenerationCount,
     max(toFloat(coalesce(wo.ADaM_Num_QC, wo.CSR_ADaM_Num_QC))) AS adamQcCount,
     max(toFloat(coalesce(wo.SDTM_Num_Total, wo.CSR_SDTM_Num_Total))) AS sdtmCount,
     max(toFloat(coalesce(wo.SDTM_Num_Generation, wo.CSR_SDTM_Num_Generation))) AS sdtmGenerationCount,
     max(toFloat(coalesce(wo.SDTM_Num_QC, wo.CSR_SDTM_Num_QC))) AS sdtmQcCount
OPTIONAL MATCH (s:Study)-[:HAS_DELIVERY]->(d)
WITH p, d, workOnRelCount, taskCount, taskGenerationCount, taskQcCount,
     tlfCount, tlfGenerationCount, tlfQcCount,
     adamCount, adamGenerationCount, adamQcCount,
     sdtmCount, sdtmGenerationCount, sdtmQcCount,
     head(collect(DISTINCT s)) AS s
CALL {
  WITH s
  OPTIONAL MATCH (s)-[:HAS_DETAIL]->(si:Study_Info)
  RETURN head(collect(DISTINCT si.TA)) AS ta,
         head(collect(DISTINCT si.Study_Type)) AS studyType
}
CALL {
  WITH d
  OPTIONAL MATCH (d)-[rel:HAS_TLF]->(item:TLF)
  RETURN collect(DISTINCT {
    name: item.Name, category: item.Category, type: item.Type,
    source: item.Source, generation: rel.Generation, qc: rel.QC
  }) AS tlfs
}
CALL {
  WITH d
  OPTIONAL MATCH (d)-[rel:HAS_ADAM]->(item:ADaM)
  RETURN collect(DISTINCT {
    name: item.Name, category: item.Category, type: item.Type,
    generation: rel.Generation, qc: rel.QC
  }) AS adams
}
CALL {
  WITH d
  OPTIONAL MATCH (d)-[rel:HAS_SDTM]->(item:SDTM)
  RETURN collect(DISTINCT {
    name: item.Name, category: item.Category, type: item.Type,
    generation: rel.Generation, qc: rel.QC
  }) AS sdtms
}
RETURN p.Name AS person, d.DID AS did, s.Name AS study,
       substring(toString(d.Planned_Delivery_Date), 0, 10) AS planned_date,
       taskCount AS task_count,
       taskGenerationCount AS task_generation_count,
       taskQcCount AS task_qc_count,
       tlfCount AS tlf_count,
       tlfGenerationCount AS tlf_generation_count,
       tlfQcCount AS tlf_qc_count,
       adamCount AS adam_count,
       adamGenerationCount AS adam_generation_count,
       adamQcCount AS adam_qc_count,
       sdtmCount AS sdtm_count,
       sdtmGenerationCount AS sdtm_generation_count,
       sdtmQcCount AS sdtm_qc_count,
       ta, studyType AS study_type,
       d.Reporting_Event AS reporting_event,
       d.Draft_or_Final AS draft_or_final,
       tlfs, adams, sdtms,
       workOnRelCount AS work_on_rel_count
"""


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _read_query(query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    load_env()
    driver = get_driver()
    try:
        database = __import__("os").environ.get("NEO4J_DATABASE", "neo4j")
        with driver.session(database=database) as session:
            return session.execute_read(
                lambda tx: [record.data() for record in tx.run(query, parameters or {})]
            )
    finally:
        driver.close()


def load_training_records() -> list[dict[str, Any]]:
    """Load completed Person x DID records in small, independent transactions."""
    people = [
        row["person"]
        for row in _read_query(TRAINING_PEOPLE_QUERY)
        if row.get("person")
    ]
    records: list[dict[str, Any]] = []
    for person in people:
        records.extend(
            _normalize_record(row)
            for row in _read_query(TRAINING_QUERY, {"person": person})
        )
    return records


def load_target_record(person: str, did: str) -> dict[str, Any]:
    """Load one planned or ongoing Person x DID record."""
    rows = _read_query(TARGET_QUERY, {"person": person, "did": did})
    if not rows:
        raise ValueError(
            f"No Planned/Ongoing WORKS_ON record found for person={person!r}, DID={did!r}."
        )
    if len(rows) > 1:
        raise ValueError(f"Expected one target record, found {len(rows)}.")
    record = _normalize_record(rows[0])
    if record.get("work_on_rel_count") != 1:
        raise ValueError("Target has duplicate WORKS_ON relationships.")
    return record


def _number(value: Any) -> float:
    if value is None or value == "":
        return 0.0
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected a numeric value, got {value!r}.") from exc
    if not math.isfinite(result):
        raise ValueError(f"Expected a finite numeric value, got {value!r}.")
    return result


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(record)
    for field in TASK_FIELDS:
        normalized[field] = _number(record.get(field))
    if "actual_hours" in record and record.get("actual_hours") is not None:
        normalized["actual_hours"] = _number(record["actual_hours"])
    for kind in ("tlfs", "adams", "sdtms"):
        normalized[kind] = [
            dict(item) for item in (record.get(kind) or []) if item and item.get("name")
        ]
    return normalized


def quality_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return blocking and warning-level data quality findings."""
    key_counts: dict[tuple[str, str], int] = {}
    for row in records:
        key = (str(row.get("person") or ""), str(row.get("did") or ""))
        key_counts[key] = key_counts.get(key, 0) + 1

    duplicate_keys = [
        {"person": person, "did": did, "count": count}
        for (person, did), count in key_counts.items()
        if count > 1
    ]
    return {
        "record_count": len(records),
        "unique_people": len({row.get("person") for row in records if row.get("person")}),
        "unique_dids": len({row.get("did") for row in records if row.get("did")}),
        "missing_completion_date": sum(not row.get("completion_date") for row in records),
        "missing_actual_hours": sum(row.get("actual_hours") is None for row in records),
        "non_positive_actual_hours": sum(
            row.get("actual_hours") is not None and row["actual_hours"] <= 0
            for row in records
        ),
        "duplicate_person_did": duplicate_keys,
        "duplicate_work_on_relationships": sum(
            _number(row.get("work_on_rel_count")) != 1 for row in records
        ),
        "multiple_studies": sum(_number(row.get("study_count")) > 1 for row in records),
        "no_time_records": sum(_number(row.get("time_record_count")) == 0 for row in records),
        "negative_task_counts": sum(
            any(_number(row.get(field)) < 0 for field in TASK_FIELDS) for row in records
        ),
    }


def clean_training_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply explicit eligibility rules for model training."""
    cleaned = []
    for row in records:
        if not row.get("person") or not row.get("did") or not row.get("completion_date"):
            continue
        if row.get("actual_hours") is None or _number(row["actual_hours"]) <= 0:
            continue
        if _number(row.get("work_on_rel_count", 1)) != 1:
            continue
        if _number(row.get("study_count", 1)) > 1:
            continue
        try:
            datetime.fromisoformat(str(row["completion_date"])[:10])
        except ValueError:
            continue
        cleaned.append(_normalize_record(row))
    return cleaned


def _normalized_name(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def _assignment_matches(value: Any, person: str) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (list, tuple, set)):
        return any(_assignment_matches(item, person) for item in value)
    return _normalized_name(value) == _normalized_name(person)


def _item_set(record: dict[str, Any], kind: str) -> set[str]:
    person = str(record.get("person") or "")
    items = record.get(kind) or []
    assigned = {
        _normalized_name(item.get("name"))
        for item in items
        if _assignment_matches(item.get("generation"), person)
        or _assignment_matches(item.get("qc"), person)
    }
    if assigned:
        return assigned
    return {_normalized_name(item.get("name")) for item in items if item.get("name")}


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _as_date(value: Any) -> date:
    return datetime.fromisoformat(str(value)[:10]).date()


def _safe_median(values: Iterable[float]) -> float:
    values = list(values)
    return float(median(values)) if values else 0.0


def build_feature_row(
    target: dict[str, Any], history: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build time-safe features and return the most similar personal history."""
    target_date_value = target.get("completion_date") or target.get("as_of_date")
    target_date = _as_date(target_date_value) if target_date_value else date.today()
    eligible = [
        row
        for row in history
        if row.get("completion_date") and _as_date(row["completion_date"]) < target_date
    ]
    person_history = [
        row
        for row in eligible
        if _normalized_name(row.get("person")) == _normalized_name(target.get("person"))
    ]

    global_hours = [_number(row["actual_hours"]) for row in eligible]
    global_rates = [
        _number(row["actual_hours"]) / _number(row["task_count"])
        for row in eligible
        if _number(row.get("task_count")) > 0
    ]
    person_hours = [_number(row["actual_hours"]) for row in person_history]
    person_rates = [
        _number(row["actual_hours"]) / _number(row["task_count"])
        for row in person_history
        if _number(row.get("task_count")) > 0
    ]

    target_sets = {kind: _item_set(target, kind) for kind in ("tlfs", "adams", "sdtms")}
    historical_union = {
        kind: set().union(*(_item_set(row, kind) for row in person_history))
        if person_history
        else set()
        for kind in ("tlfs", "adams", "sdtms")
    }

    similarities = []
    for row in person_history:
        scores = {
            kind: _jaccard(target_sets[kind], _item_set(row, kind))
            for kind in ("tlfs", "adams", "sdtms")
        }
        non_empty_scores = [
            score
            for kind, score in scores.items()
            if target_sets[kind] or _item_set(row, kind)
        ]
        similarities.append(
            {
                "did": row.get("did"),
                "study": row.get("study"),
                "completion_date": row.get("completion_date"),
                "actual_hours": row.get("actual_hours"),
                "tlf_similarity": scores["tlfs"],
                "adam_similarity": scores["adams"],
                "sdtm_similarity": scores["sdtms"],
                "overall_similarity": (
                    sum(non_empty_scores) / len(non_empty_scores)
                    if non_empty_scores
                    else 0.0
                ),
            }
        )
    similarities.sort(key=lambda item: item["overall_similarity"], reverse=True)
    best = similarities[0] if similarities else None

    feature = {field: _number(target.get(field)) for field in TASK_FIELDS}
    feature.update(
        {
            "person_completed_count": float(len(person_history)),
            "person_median_hours": _safe_median(person_hours),
            "person_recent_median_hours": _safe_median(person_hours[-5:]),
            "person_median_hours_per_task": _safe_median(person_rates),
            "global_completed_count": float(len(eligible)),
            "global_median_hours": _safe_median(global_hours),
            "global_median_hours_per_task": _safe_median(global_rates),
            "tlf_prior_overlap_count": float(
                len(target_sets["tlfs"] & historical_union["tlfs"])
            ),
            "adam_prior_overlap_count": float(
                len(target_sets["adams"] & historical_union["adams"])
            ),
            "sdtm_prior_overlap_count": float(
                len(target_sets["sdtms"] & historical_union["sdtms"])
            ),
            "max_tlf_similarity": max(
                (item["tlf_similarity"] for item in similarities), default=0.0
            ),
            "max_adam_similarity": max(
                (item["adam_similarity"] for item in similarities), default=0.0
            ),
            "max_sdtm_similarity": max(
                (item["sdtm_similarity"] for item in similarities), default=0.0
            ),
            "max_overall_similarity": best["overall_similarity"] if best else 0.0,
            "days_since_similar_work": float(
                (target_date - _as_date(best["completion_date"])).days
                if best and best["overall_similarity"] > 0
                else 3650
            ),
            "ta": str(target.get("ta") or "UNKNOWN"),
            "study_type": str(target.get("study_type") or "UNKNOWN"),
            "reporting_event": str(target.get("reporting_event") or "UNKNOWN"),
            "draft_or_final": str(target.get("draft_or_final") or "UNKNOWN"),
        }
    )
    return feature, similarities[:5]


def build_training_features(
    records: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], np.ndarray]:
    ordered = sorted(records, key=lambda row: (row["completion_date"], str(row["did"])))
    features = []
    labels = []
    for row in ordered:
        feature, _ = build_feature_row(row, ordered)
        features.append(feature)
        labels.append(_number(row["actual_hours"]))
    return features, np.asarray(labels, dtype=float)


def _matrix(features: list[dict[str, Any]]) -> list[list[Any]]:
    columns = NUMERIC_FEATURES + CATEGORICAL_FEATURES
    return [[feature.get(column) for column in columns] for feature in features]


def _pipeline() -> Pipeline:
    numeric_indices = list(range(len(NUMERIC_FEATURES)))
    categorical_indices = list(
        range(len(NUMERIC_FEATURES), len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES))
    )
    preprocessing = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scale", StandardScaler()),
                    ]
                ),
                numeric_indices,
            ),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                categorical_indices,
            ),
        ]
    )
    return Pipeline([("preprocess", preprocessing), ("regressor", Ridge(alpha=1.0))])


def _grouped_time_split(
    records: list[dict[str, Any]],
) -> tuple[set[str], set[str], set[str]]:
    did_dates: dict[str, date] = {}
    for row in records:
        did = str(row["did"])
        completion = _as_date(row["completion_date"])
        did_dates[did] = max(did_dates.get(did, completion), completion)
    ordered = sorted(did_dates, key=lambda did: (did_dates[did], did))
    if len(ordered) < 6:
        raise ValueError("At least 6 completed DIDs are required for a grouped time split.")
    train_end = max(1, int(len(ordered) * 0.70))
    calibration_end = max(train_end + 1, int(len(ordered) * 0.85))
    calibration_end = min(calibration_end, len(ordered) - 1)
    return (
        set(ordered[:train_end]),
        set(ordered[train_end:calibration_end]),
        set(ordered[calibration_end:]),
    )


def _predict_hours(model: Pipeline, features: list[dict[str, Any]]) -> np.ndarray:
    return np.maximum(0.0, np.expm1(model.predict(_matrix(features))))


@lru_cache(maxsize=4)
def _load_model_artifact(path: str, modified_time_ns: int) -> dict[str, Any]:
    """Cache a model until its on-disk modification time changes."""
    del modified_time_ns
    return joblib.load(path)


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    errors = predicted - actual
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "median_ae": float(np.median(np.abs(errors))),
        "rmse": float(math.sqrt(mean_squared_error(actual, predicted))),
        "wape": float(np.abs(errors).sum() / actual.sum()) if actual.sum() else 0.0,
        "bias": float(errors.mean()),
    }


def train_model(
    records: list[dict[str, Any]], model_path: Path, minimum_records: int = 20
) -> dict[str, Any]:
    """Train, time-test, calibrate upper prediction bounds, and persist the model."""
    cleaned = sorted(
        clean_training_records(records),
        key=lambda row: (row["completion_date"], str(row["did"]), str(row["person"])),
    )
    if len(cleaned) < minimum_records:
        raise ValueError(
            f"Only {len(cleaned)} eligible records; at least {minimum_records} are required."
        )
    features, labels = build_training_features(cleaned)
    train_dids, calibration_dids, test_dids = _grouped_time_split(cleaned)
    train_idx = [i for i, row in enumerate(cleaned) if str(row["did"]) in train_dids]
    calibration_idx = [
        i for i, row in enumerate(cleaned) if str(row["did"]) in calibration_dids
    ]
    test_idx = [i for i, row in enumerate(cleaned) if str(row["did"]) in test_dids]

    evaluation_model = _pipeline()
    evaluation_model.fit(
        _matrix([features[i] for i in train_idx]), np.log1p(labels[train_idx])
    )
    calibration_predictions = _predict_hours(
        evaluation_model, [features[i] for i in calibration_idx]
    )
    calibration_residuals = labels[calibration_idx] - calibration_predictions
    upper_adjustments = {
        "p80": max(0.0, float(np.quantile(calibration_residuals, 0.80))),
        "p90": max(0.0, float(np.quantile(calibration_residuals, 0.90))),
    }
    test_predictions = _predict_hours(evaluation_model, [features[i] for i in test_idx])
    metrics = _metrics(labels[test_idx], test_predictions)
    metrics["p80_coverage"] = float(
        np.mean(labels[test_idx] <= test_predictions + upper_adjustments["p80"])
    )
    metrics["p90_coverage"] = float(
        np.mean(labels[test_idx] <= test_predictions + upper_adjustments["p90"])
    )

    final_model = _pipeline()
    final_model.fit(_matrix(features), np.log1p(labels))
    artifact = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now().astimezone().isoformat(),
        "model": final_model,
        "history": cleaned,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "upper_adjustments": upper_adjustments,
        "metrics": metrics,
        "split": {
            "train_records": len(train_idx),
            "calibration_records": len(calibration_idx),
            "test_records": len(test_idx),
            "train_dids": len(train_dids),
            "calibration_dids": len(calibration_dids),
            "test_dids": len(test_dids),
        },
    }
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    return {
        "model_path": str(model_path.resolve()),
        "model_version": MODEL_VERSION,
        "eligible_records": len(cleaned),
        "metrics": metrics,
        "upper_adjustments": upper_adjustments,
        "split": artifact["split"],
    }


def predict_record(
    target: dict[str, Any], model_path: Path, as_of_date: str | None = None
) -> dict[str, Any]:
    """Predict total effort for one normalized target record."""
    resolved_model_path = model_path.resolve()
    if not resolved_model_path.exists():
        raise FileNotFoundError(
            f"Effort model not found: {resolved_model_path}. Train the model before predicting."
        )
    artifact = _load_model_artifact(
        str(resolved_model_path), resolved_model_path.stat().st_mtime_ns
    )
    target = _normalize_record(target)
    target["as_of_date"] = as_of_date or date.today().isoformat()
    history = [
        row
        for row in artifact["history"]
        if _as_date(row["completion_date"]) < _as_date(target["as_of_date"])
    ]
    feature, similar = build_feature_row(target, history)
    p50 = float(_predict_hours(artifact["model"], [feature])[0])
    adjustments = artifact["upper_adjustments"]
    warnings = []
    if feature["person_completed_count"] < 5:
        warnings.append("This person has fewer than 5 eligible completed DID records.")
    if feature["global_completed_count"] < 20:
        warnings.append("Fewer than 20 historical records precede the prediction date.")
    if not any(target.get(kind) for kind in ("tlfs", "adams", "sdtms")):
        warnings.append("No TLF/ADaM/SDTM details were available for similarity features.")
    return {
        "person": target.get("person"),
        "did": target.get("did"),
        "prediction_type": "total_hours",
        "as_of_date": target["as_of_date"],
        "p50_hours": round(p50, 1),
        "p80_hours": round(p50 + adjustments["p80"], 1),
        "p90_hours": round(p50 + adjustments["p90"], 1),
        "model_version": artifact["model_version"],
        "person_completed_did_count": int(feature["person_completed_count"]),
        "similar_historical_dids": similar,
        "warnings": warnings,
    }


def predict_effort(
    person: str,
    did: str,
    model_path: Path = DEFAULT_MODEL_PATH,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Load a target from Neo4j and forecast it; intended for Agent tool wiring."""
    return predict_record(
        load_target_record(person, did),
        model_path=model_path,
        as_of_date=as_of_date,
    )


def _load_json_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        raise ValueError("Input JSON must be a list or an object containing a records list.")
    return [_normalize_record(record) for record in records]


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Export completed DID records.")
    extract_parser.add_argument("--output", type=Path, required=True)

    train_parser = subparsers.add_parser("train", help="Train and save the effort model.")
    train_parser.add_argument("--input", type=Path, help="Extract JSON; omit to query Neo4j.")
    train_parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    train_parser.add_argument("--minimum-records", type=int, default=20)

    predict_parser = subparsers.add_parser(
        "predict", help="Predict a planned or ongoing Person x DID."
    )
    predict_parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    predict_parser.add_argument("--person", required=True)
    predict_parser.add_argument("--did", required=True)
    predict_parser.add_argument("--as-of-date")

    args = parser.parse_args()
    if args.command == "extract":
        records = load_training_records()
        payload = {
            "extracted_at": datetime.now().astimezone().isoformat(),
            "quality": quality_report(records),
            "records": records,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=_json_default),
            encoding="utf-8",
        )
        _print_json({"output": str(args.output.resolve()), "quality": payload["quality"]})
    elif args.command == "train":
        records = _load_json_records(args.input) if args.input else load_training_records()
        _print_json(train_model(records, args.model, args.minimum_records))
    else:
        _print_json(
            predict_effort(args.person, args.did, args.model, args.as_of_date)
        )


if __name__ == "__main__":
    main()
