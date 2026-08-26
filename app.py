"""Streamlit entry point for Posit Connect (RSC) deployment."""

from __future__ import annotations

import streamlit as st

from agent import ask
from neo4j_client import connection_summary, get_schema, load_env
from vox_client import add_usage, empty_usage, models_vox_genai

st.set_page_config(
    page_title="Neo4j QA (RSC)",
    page_icon="◈",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
  .stApp { background: linear-gradient(165deg, #f3f6f4 0%, #e8eef2 45%, #f7f3ee 100%); }
  [data-testid="stHeader"] { background: transparent; }
  .block-container { padding-top: 1.5rem; max-width: 820px; }
  .brand {
    font-family: "Segoe UI", "PingFang SC", sans-serif;
    font-size: 2rem; font-weight: 700; letter-spacing: -0.02em;
    color: #1a3a32; margin-bottom: 0.15rem;
  }
  .tagline { color: #4a635c; margin-bottom: 1.4rem; }
  .cypher-box {
    font-family: Consolas, "Courier New", monospace;
    font-size: 0.82rem; background: #1e2a28; color: #c8e6d8;
    padding: 0.75rem 1rem; border-radius: 8px; overflow-x: auto;
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


ensure_state()

st.markdown('<div class="brand">Neo4j QA</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tagline">Ask the Neo4j graph in natural language · powered by Pfizer Vox GenAI · RSC edition</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Connection")
    st.caption(f"URI: `{connection_summary()}`")
    st.caption("Database: `neo4j` · read-only")

    st.divider()
    st.markdown("# List available Vox GenAI V2 models")
    try:
        available_models = models_vox_genai()
        if available_models:
            for model_name in available_models:
                st.caption(f"- `{model_name}`")
        else:
            st.warning("models_vox_genai() returned no available models.")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Failed to load Vox GenAI models: {exc}")

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
    st.caption("Each question usually uses 2 LLM calls (Cypher + answer).")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("cypher") and st.session_state.show_cypher and msg["role"] == "assistant":
            st.markdown(f'<div class="cypher-box">{msg["cypher"]}</div>', unsafe_allow_html=True)
        if msg.get("usage") and msg["role"] == "assistant":
            uu = msg["usage"]
            st.caption(
                f"Tokens this turn: {uu.get('total_tokens', 0)} "
                f"(prompt {uu.get('prompt_tokens', 0)} · completion {uu.get('completion_tokens', 0)})"
            )

prompt = st.chat_input("e.g. What deliveries does study C1071007 have?")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Querying Neo4j…"):
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            try:
                result = ask(prompt, history=history, schema=st.session_state.schema)
                st.session_state.schema = result["schema"]
                answer = result["answer"]
                cypher = result.get("cypher") or ""
                usage = result.get("usage") or empty_usage()
                st.session_state.token_usage = add_usage(st.session_state.token_usage, usage)
                st.markdown(answer)
                if cypher and st.session_state.show_cypher:
                    st.markdown(f'<div class="cypher-box">{cypher}</div>', unsafe_allow_html=True)
                st.caption(
                    f"Tokens this turn: {usage.get('total_tokens', 0)} "
                    f"(prompt {usage.get('prompt_tokens', 0)} · completion {usage.get('completion_tokens', 0)})"
                )
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "cypher": cypher, "usage": usage}
                )
            except Exception as exc:  # noqa: BLE001
                err = f"Something went wrong: {exc}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
