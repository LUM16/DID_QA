"""Neo4j read-only helpers for the RSC Streamlit app."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

APP_ROOT = Path(__file__).resolve().parent
ENV_FILE = APP_ROOT / ".env"

FORBIDDEN = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|LOAD\s+CSV|FOREACH|CALL\s+\{)\b",
    re.IGNORECASE,
)


def load_env() -> None:
    """
    Load APP_ROOT/.env into os.environ.

    When .env exists (local RSC folder testing), its values win.
    On Posit Connect, prefer not bundling .env — set Vars instead; if no
    .env file is present, existing Connect Vars are used as-is.
    """
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def get_driver():
    load_env()
    uri = os.environ.get("NEO4J_URI", "bolt://10.109.17.64:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise ValueError("NEO4J_PASSWORD is not set (use Connect Vars or .env).")
    return GraphDatabase.driver(uri, auth=(user, password))


def ensure_read_only(query: str) -> None:
    stripped = query.strip().rstrip(";")
    if FORBIDDEN.search(stripped):
        raise ValueError("Only read-only Cypher queries are allowed.")


def run_cypher(query: str, limit_rows: int = 200) -> list[dict[str, Any]]:
    ensure_read_only(query)
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    driver = get_driver()
    try:
        with driver.session(database=database) as session:
            result = session.run(query)
            rows: list[dict[str, Any]] = []
            for i, record in enumerate(result):
                if i >= limit_rows:
                    break
                rows.append(record.data())
            return rows
    finally:
        driver.close()


def get_schema() -> dict[str, Any]:
    load_env()
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    driver = get_driver()
    try:
        with driver.session(database=database) as session:
            labels = [
                row["label"]
                for row in session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
            ]
            rel_types = [
                row["relationshipType"]
                for row in session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType "
                    "RETURN relationshipType ORDER BY relationshipType"
                )
            ]
            props = [
                row["propertyKey"]
                for row in session.run(
                    "CALL db.propertyKeys() YIELD propertyKey "
                    "RETURN propertyKey ORDER BY propertyKey"
                )
            ]
            counts = {}
            for label in labels[:20]:
                counts[label] = session.run(
                    f"MATCH (n:`{label}`) RETURN count(n) AS c"
                ).single()["c"]

            return {
                "labels": labels,
                "relationshipTypes": rel_types,
                "propertyKeys": props[:100],
                "nodeCountsByLabel": counts,
            }
    finally:
        driver.close()


def connection_summary() -> str:
    load_env()
    return os.environ.get("NEO4J_URI", "bolt://10.109.17.64:7687")
