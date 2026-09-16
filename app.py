"""Streamlit entry point for Posit Connect (RSC) deployment."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from neo4j_client import connection_summary, get_schema, load_env
from vox_client import add_usage, empty_usage

APP_NAME = "DID Insight"
APP_TAGLINE = "Graph intelligence and resource forecasting"
EXAMPLE_DU_SCOPE_PATH = Path(__file__).resolve().parent / "docs" / "C5001001_61.xlsx"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: linear-gradient(165deg, #f3f6f4 0%, #e8eef2 45%, #f7f3ee 100%); }
      [data-testid="stHeader"] { background: transparent; }
      .block-container { padding-top: 1.25rem; max-width: 820px; }
      .brand {
        font-family: "Segoe UI", "PingFang SC", sans-serif;
        font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;
        color: #1a3a32; margin-bottom: 0.15rem;
      }
      .brand-hero {
        font-size: 2.55rem; letter-spacing: -0.03em; margin-bottom: 0.35rem;
      }
      .brand-compact {
        font-size: 1.2rem; font-weight: 700; letter-spacing: -0.02em;
        color: #1a3a32; margin-bottom: 0.1rem;
      }
      .tagline { color: #4a635c; margin-bottom: 1.4rem; }
      .tagline-hero { font-size: 1.08rem; color: #4a635c; margin-bottom: 0; }
      .landing-hero {
        padding: 16vh 0 1.75rem 0;
        text-align: center;
      }
      .cypher-box {
        font-family: Consolas, "Courier New", monospace;
        font-size: 0.82rem; background: #1e2a28; color: #c8e6d8;
        padding: 0.75rem 1rem; border-radius: 8px; overflow-x: auto;
      }
      .block-container:has(.landing-marker) [data-testid="stTextArea"] [data-baseweb="textarea"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
      }
      .block-container:has(.landing-marker) [data-testid="stTextArea"] [data-baseweb="textarea"] > div {
        background: rgba(255, 255, 255, 0.88) !important;
        border: 1px solid #c5d4ce !important;
        border-radius: 16px !important;
        box-shadow: 0 10px 32px rgba(26, 58, 50, 0.08) !important;
      }
      .block-container:has(.landing-marker) [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within > div {
        border: 1px solid #3d6b5e !important;
        box-shadow: 0 10px 32px rgba(26, 58, 50, 0.08) !important;
        outline: none !important;
      }
      .block-container:has(.landing-marker) [data-testid="stTextArea"] textarea {
        font-size: 1.08rem;
        min-height: 7.2rem;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background: transparent !important;
        border-radius: 16px;
        padding: 0.9rem 1rem;
      }
      .block-container:has(.landing-marker) [data-testid="stTextArea"] textarea:focus,
      .block-container:has(.landing-marker) [data-testid="stTextArea"] textarea:focus-visible {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
      }
      [data-testid="stChatInput"],
      [data-testid="stChatInput"]:focus,
      [data-testid="stChatInput"]:focus-within,
      [data-testid="stChatInput"] *:focus,
      [data-testid="stChatInput"] *:focus-visible,
      [data-testid="stChatInput"] *:focus-within {
        outline: none !important;
      }
      [data-testid="stChatInput"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
      }
      [data-testid="stChatInput"] > div {
        background: rgba(255, 255, 255, 0.9) !important;
        border: 1px solid #c5d4ce !important;
        border-radius: 18px !important;
        box-shadow: 0 8px 24px rgba(26, 58, 50, 0.08) !important;
      }
      [data-testid="stChatInput"]:focus-within > div {
        border: 1px solid #3d6b5e !important;
        box-shadow: 0 8px 24px rgba(26, 58, 50, 0.08) !important;
      }
      [data-testid="stChatInput"] [data-baseweb="textarea"],
      [data-testid="stChatInput"] [data-baseweb="textarea"] > div,
      [data-testid="stChatInput"] [data-baseweb="base-input"],
      [data-testid="stChatInput"] textarea {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background: transparent !important;
      }
      [data-testid="stChatInput"] textarea {
        font-size: 1.05rem !important;
        min-height: 3.4rem !important;
      }
      [data-testid="stBottomBlockContainer"] {
        background: transparent !important;
        padding-bottom: 1.4rem;
      }
      .block-container:has(.landing-marker) [data-testid="stFormSubmitButton"] button {
        background: #1a3a32 !important;
        border-color: #1a3a32 !important;
        color: #fff !important;
        min-height: 2.6rem;
        font-weight: 600;
        border-radius: 10px;
      }
      .block-container:has(.landing-marker) [data-testid="stFormSubmitButton"] button:hover {
        background: #24483e !important;
        border-color: #24483e !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def ensure_state() -> None:
    load_env()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "schema" not in st.session_state:
        st.session_state.schema = None
    if "show_cypher" not in st.session_state:
        st.session_state.show_cypher = True
    if "token_usage" not in st.session_state:
        st.session_state.token_usage = empty_usage()


def history_for_ask() -> list[dict]:
    return [
        {
            **{"role": m["role"], "content": m["content"]},
            **({"prediction": m["prediction"]} if m.get("prediction") else {}),
        }
        for m in st.session_state.messages[:-1]
    ]


def render_visualization(visualization: dict | None) -> None:
    """Render legacy chart payloads and validated post-query chart payloads."""
    if not visualization or not visualization.get("data"):
        return
    st.caption(visualization.get("title", ""))
    chart_type = visualization.get("chart_type")
    if chart_type == "monthly_hours_chart":
        st.bar_chart(visualization["data"], x="month", y="hours")
    elif chart_type == "did_effort_distribution_chart":
        st.bar_chart(
            visualization["data"],
            x="person",
            y=visualization.get("value_field", "hours"),
            horizontal=True,
        )
    elif chart_type in {"bar", "line"}:
        x = visualization.get("x")
        y = visualization.get("y")
        if not x or not y:
            return
        kwargs = {"x": x, "y": y}
        if visualization.get("series"):
            kwargs["color"] = visualization["series"]
        try:
            if chart_type == "line":
                st.line_chart(visualization["data"], **kwargs)
            else:
                kwargs["horizontal"] = visualization.get("horizontal", False)
                if visualization.get("stack") is not None:
                    kwargs["stack"] = visualization["stack"]
                st.bar_chart(visualization["data"], **kwargs)
        except (KeyError, TypeError, ValueError):
            st.info("The returned chart fields could not be rendered; see the table below.")


def render_result_presentation(presentation: dict | None) -> None:
    """Render the optional chart and its always-safe table fallback."""
    if not presentation:
        return
    render_visualization(presentation)
    table = presentation.get("table") or {}
    if table.get("columns"):
        st.dataframe(table["rows"], use_container_width=True, hide_index=True)
    if presentation.get("data_note"):
        st.caption(presentation["data_note"])


def render_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("visualization") and msg["role"] == "assistant":
            render_result_presentation(msg["visualization"])
        if msg.get("presentation_warning") and msg["role"] == "assistant":
            st.caption(msg["presentation_warning"])
        if msg.get("cypher") and st.session_state.show_cypher and msg["role"] == "assistant":
            st.markdown(f'<div class="cypher-box">{msg["cypher"]}</div>', unsafe_allow_html=True)
        if msg.get("usage") and msg["role"] == "assistant":
            uu = msg["usage"]
            st.caption(
                f"Tokens this turn: {uu.get('total_tokens', 0)} "
                f"(prompt {uu.get('prompt_tokens', 0)} · completion {uu.get('completion_tokens', 0)})"
            )


def enqueue_prompt(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()


def complete_pending_turn() -> None:
    if not st.session_state.messages:
        return
    last = st.session_state.messages[-1]
    if last["role"] != "user":
        return

    prompt = last["content"]
    with st.chat_message("assistant"):
        with st.spinner("Working…"):
            try:
                from agent import ask

                result = ask(prompt, history=history_for_ask(), schema=st.session_state.schema)
                st.session_state.schema = result["schema"]
                answer = result["answer"]
                cypher = result.get("cypher") or ""
                usage = result.get("usage") or empty_usage()
                st.session_state.token_usage = add_usage(st.session_state.token_usage, usage)
                st.markdown(answer)
                render_result_presentation(result.get("visualization"))
                if result.get("presentation_warning"):
                    st.caption(result["presentation_warning"])
                if cypher and st.session_state.show_cypher:
                    st.markdown(f'<div class="cypher-box">{cypher}</div>', unsafe_allow_html=True)
                st.caption(
                    f"Tokens this turn: {usage.get('total_tokens', 0)} "
                    f"(prompt {usage.get('prompt_tokens', 0)} · completion {usage.get('completion_tokens', 0)})"
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "cypher": cypher,
                        "usage": usage,
                        "prediction": result.get("prediction"),
                        "visualization": result.get("visualization"),
                        "presentation_warning": result.get("presentation_warning"),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                err = f"Something went wrong: {exc}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})


def render_team_recommendation() -> None:
    """Render the upload-driven, read-only DU team scope-match workflow."""
    st.subheader("Recommend DU Team")
    st.caption(
        "Upload a new Delivery scope. Recommendations use completed Neo4j history, "
        "current Team Lead membership, and the shared TLF similarity cache."
    )
    st.info(
        "Accepted input: one Excel workbook with sheets named TLF and Data, or a "
        "TLF CSV plus a Data CSV. The uploaded scope is not written to Neo4j."
    )
    st.markdown("**Example input — `C5001001_61.xlsx`**")
    st.caption(
        "This example contains TLF and Data sheets and can be downloaded, reviewed, "
        "then uploaded directly to try the recommendation workflow."
    )
    if EXAMPLE_DU_SCOPE_PATH.exists():
        st.download_button(
            "Download example input",
            data=EXAMPLE_DU_SCOPE_PATH.read_bytes(),
            file_name=EXAMPLE_DU_SCOPE_PATH.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        st.warning("The bundled DU recommendation example input is unavailable.")
    primary_file = st.file_uploader(
        "Delivery scope workbook or TLF CSV",
        type=["xlsx", "csv"],
        key="du_scope_primary",
    )
    data_csv_file = None
    if primary_file and primary_file.name.lower().endswith(".csv"):
        data_csv_file = st.file_uploader(
            "Data CSV",
            type=["csv"],
            key="du_scope_data",
        )
    if not primary_file:
        return
    upload_key = (
        primary_file.name,
        len(primary_file.getvalue()),
        data_csv_file.name if data_csv_file else "",
        len(data_csv_file.getvalue()) if data_csv_file else 0,
    )
    if st.button("Recommend DU teams", type="primary", use_container_width=True):
        try:
            from du_team_recommendation import recommend_uploaded_scope

            with st.spinner("Reading scope and comparing completed DU experience..."):
                result = recommend_uploaded_scope(primary_file, data_csv_file)
            st.session_state.du_team_recommendation = result
            st.session_state.du_team_recommendation_input = upload_key
        except (RuntimeError, ValueError) as exc:
            st.error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"DU team recommendation failed: {exc}")
            return

    result = st.session_state.get("du_team_recommendation")
    if not result or st.session_state.get("du_team_recommendation_input") != upload_key:
        return
    counts = result["target_counts"]
    left, middle, right = st.columns(3)
    left.metric("Target TLFs", counts["tlfs"])
    middle.metric("Target ADaM", counts["adams"])
    right.metric("Target SDTM", counts["sdtms"])
    snapshot = result["history_snapshot"]
    st.caption(
        f"DU history snapshot: {snapshot['generated_at']} · "
        f"{snapshot['history_row_count']:,} completed DU-DID rows."
    )

    recommendations = result["recommendations"]
    if not recommendations:
        st.warning("No DU team recommendations were produced from the available history.")
        return
    st.bar_chart(
        [
            {"du_team": row["du_team"], "score": row["score"]}
            for row in recommendations
        ],
        x="du_team",
        y="score",
        horizontal=True,
    )
    st.caption(
        "Overall score is a transparent scope-match score, not a trained-model probability."
    )
    for row in recommendations:
        st.markdown(
            f"### #{row['rank']} — {row['du_team']} · {row['score']:.1f}/100"
        )
        st.caption(row["recommendation_level"])
        st.dataframe(
            [
                {
                    "TLF semantic coverage": f"{row['tlf_semantic_coverage']:.1%}",
                    "ADaM coverage": f"{row['adam_coverage']:.1%}",
                    "SDTM coverage": f"{row['sdtm_coverage']:.1%}",
                    "Similar DID >= 70%": row["similar_did_count_ge_70"],
                    "Similar DID >= 85%": row["similar_did_count_ge_85"],
                    "Completed DIDs": row["completed_did_count"],
                    "Semantic candidates": row["semantic_candidate_did_count"],
                    "Active DIDs": row["active_did_count"],
                }
            ],
            use_container_width=True,
            hide_index=True,
        )
        gaps = []
        if row["missing_adams"]:
            gaps.append(f"Missing ADaM: {', '.join(row['missing_adams'])}")
        if row["missing_sdtms"]:
            gaps.append(f"Missing SDTM: {', '.join(row['missing_sdtms'])}")
        if row["missing_exact_tlfs"]:
            gaps.append(
                f"No exact historical TLF title match: {len(row['missing_exact_tlfs'])}"
            )
        if gaps:
            st.warning(" | ".join(gaps))
        else:
            st.success("No exact ADaM or SDTM coverage gaps were found.")
        with st.expander("Most similar completed DIDs"):
            st.dataframe(
                [
                    {
                        "DID": did["did"],
                        "Completed": did["completion_date"],
                        "Scope similarity": f"{did['combined_similarity']:.1%}",
                        "TLF semantic coverage": f"{did['tlf_semantic_coverage']:.1%}",
                    }
                    for did in row["similar_dids"]
                ],
                use_container_width=True,
                hide_index=True,
            )
    cache = result["cache"]
    st.caption(
        f"Shared TLF similarity cache: {cache['hits']:,} hits · "
        f"{cache['misses']:,} new comparisons."
    )


def render_tlf_person_allocation() -> None:
    """Render snapshot-only Generation/QC allocation for uploaded TLFs."""
    st.subheader("Allocate TLF People")
    st.caption(
        "Match a DU Team Lead to the manually refreshed snapshot, then recommend "
        "Generation and QC people from completed TLF role evidence. This tab never queries Neo4j."
    )
    st.info(
        "Primary balancing: each prior primary allocation reduces that person's next "
        "primary score by 12 points, helping avoid concentration in one person."
    )
    st.markdown("**Example input — `C5001001_61.xlsx`**")
    if EXAMPLE_DU_SCOPE_PATH.exists():
        st.download_button(
            "Download example input",
            data=EXAMPLE_DU_SCOPE_PATH.read_bytes(),
            file_name=EXAMPLE_DU_SCOPE_PATH.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="tlf_allocation_example",
        )
    team_lead_input = st.text_input(
        "DU Team Lead name",
        placeholder="Enter the Team Lead name to match against the snapshot",
        key="tlf_allocation_team_lead",
    )
    primary_file = st.file_uploader(
        "Delivery scope workbook or TLF CSV",
        type=["xlsx", "csv"],
        key="tlf_allocation_primary",
    )
    data_csv_file = None
    if primary_file and primary_file.name.lower().endswith(".csv"):
        data_csv_file = st.file_uploader(
            "Data CSV", type=["csv"], key="tlf_allocation_data"
        )
    if not primary_file:
        return
    upload_key = (
        team_lead_input.strip(),
        primary_file.name,
        len(primary_file.getvalue()),
        data_csv_file.name if data_csv_file else "",
        len(data_csv_file.getvalue()) if data_csv_file else 0,
    )
    if st.button("Allocate TLF people", type="primary", use_container_width=True):
        if not team_lead_input.strip():
            st.error("Enter a DU Team Lead name.")
            return
        try:
            from tlf_person_allocation import allocate_uploaded_tlfs

            with st.spinner("Validating the Team Lead and comparing completed TLF role evidence..."):
                result = allocate_uploaded_tlfs(
                    team_lead_input, primary_file, data_csv_file
                )
            st.session_state.tlf_person_allocation = result
            st.session_state.tlf_person_allocation_input = upload_key
        except (RuntimeError, ValueError, FileNotFoundError) as exc:
            st.error(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"TLF person allocation failed: {exc}")
            return
    result = st.session_state.get("tlf_person_allocation")
    if not result or st.session_state.get("tlf_person_allocation_input") != upload_key:
        return
    snapshot = result["snapshot"]
    st.caption(
        f"Snapshot: {snapshot['generated_at']} · {snapshot['history_row_count']:,} "
        f"Person × DID × TLF role-evidence rows."
    )
    st.success(
        f"LLM Team Lead match: {result['team_match']['team_lead_name']} "
        "(strictly validated against snapshot candidates)."
    )
    for allocation in result["allocations"]:
        tlf = allocation["tlf"]
        st.markdown(f"### {tlf['name']}")
        rows = []
        for role, label in (("generation", "Generation"), ("qc", "QC")):
            recommendation = allocation[role]
            primary = recommendation["primary"]
            rows.append(
                {
                    "Role": label,
                    "Recommendation": "Primary",
                    "Person": primary["person"] if primary else "Lead review required",
                    "Score": primary["adjusted_score"] if primary else None,
                    "Active DIDs": primary["active_did_count"] if primary else None,
                    "Evidence DID": primary["evidence_did"] if primary else None,
                }
            )
            for index, backup in enumerate(recommendation["backups"], start=1):
                rows.append(
                    {
                        "Role": label,
                        "Recommendation": f"Backup {index}",
                        "Person": backup["person"],
                        "Score": backup["adjusted_score"],
                        "Active DIDs": backup["active_did_count"],
                        "Evidence DID": backup["evidence_did"],
                    }
                )
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if allocation["lead_review_required"]:
            st.warning(allocation["fallback_reason"])
        if len(allocation["generation"]["backups"]) < 2 or len(allocation["qc"]["backups"]) < 2:
            st.caption("Fewer than two evidence-qualified backups are available; lead review is needed.")
    cache = result["cache"]
    st.caption(
        f"Shared TLF similarity cache: {cache['hits']:,} hits · "
        f"{cache['misses']:,} misses/new single-TLF comparisons."
    )


ensure_state()

with st.sidebar:
    st.subheader("Connection")
    st.caption(f"URI: `{connection_summary()}`")
    st.caption("Database: `neo4j` · read-only")

    st.divider()
    st.session_state.show_cypher = st.toggle(
        "Show generated Cypher", value=st.session_state.show_cypher
    )

    if st.button("Refresh schema cache", use_container_width=True):
        try:
            with st.spinner("Loading schema…"):
                st.session_state.schema = get_schema()
            st.success("Schema updated")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.token_usage = empty_usage()
        st.rerun()

    if st.session_state.schema:
        labels = st.session_state.schema.get("labels", [])
        st.caption(f"Cached labels: {len(labels)}")

    st.subheader("Token usage (this session)")
    u = st.session_state.token_usage
    st.metric("Total tokens", u.get("total_tokens", 0))
    st.caption(
        f"Prompt: {u.get('prompt_tokens', 0)} · Completion: {u.get('completion_tokens', 0)}"
    )
    st.caption("Normal Q&A usually uses 3 LLM calls (Cypher + answer + presentation).")

chat_tab, team_tab, allocation_tab = st.tabs(
    ["Ask Neo4j", "Recommend DU Team", "Allocate TLF People"]
)

with chat_tab:
    in_conversation = bool(st.session_state.messages)
    if not in_conversation:
        st.markdown(
            f"""
            <div class="landing-marker"></div>
            <div class="landing-hero">
              <div class="brand brand-hero">{APP_NAME}</div>
              <div class="tagline-hero">{APP_TAGLINE}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        left, mid, right = st.columns([0.06, 0.88, 0.06])
        with mid:
            with st.form("landing_ask", clear_on_submit=True, border=False):
                landing_text = st.text_area(
                    "Question",
                    placeholder="Ask about studies, deliveries, workload, or forecast DID effort…",
                    height=120,
                    label_visibility="collapsed",
                )
                submitted = st.form_submit_button(
                    "Ask", type="primary", use_container_width=True
                )
            if submitted:
                prompt = (landing_text or "").strip()
                if prompt:
                    enqueue_prompt(prompt)
    else:
        st.markdown(f'<div class="brand-compact">{APP_NAME}</div>', unsafe_allow_html=True)
        st.caption(APP_TAGLINE)
        for msg in st.session_state.messages:
            render_message(msg)
        complete_pending_turn()
        follow_up = st.chat_input("Ask a follow-up…")
        if follow_up:
            enqueue_prompt(follow_up.strip())

with team_tab:
    render_team_recommendation()

with allocation_tab:
    render_tlf_person_allocation()
