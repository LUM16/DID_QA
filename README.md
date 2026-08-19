# RSC Streamlit app — Neo4j natural-language Q&A

Self-contained package for **Posit Connect / RStudio Connect (RSC)**.
Uses network Neo4j + Pfizer Vox GenAI.

**Recommended production path:** push this folder to GitHub, then **Import from Git** on Connect. See [`GITHUB_DEPLOY.md`](GITHUB_DEPLOY.md).

## Contents

| File | Role |
|------|------|
| `app.py` | Streamlit entry point (publish this) |
| `agent.py` | NL → Cypher → answer |
| `neo4j_client.py` | Read-only Neo4j access |
| `vox_client.py` | Vox OAuth + chat completions |
| `requirements.txt` | Python deps |
| `manifest.json` | Required for Git-backed Connect deploy |
| `GITHUB_DEPLOY.md` | GitHub + Import from Git instructions |
| `.env.example` | Env var template (no secrets) |
| `.env` | Local test secrets (**do not commit**) |

## Local smoke test

```cmd
cd rsc-app
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

Open http://127.0.0.1:8501

## Deploy to Posit Connect

### Option A — GitHub (Git-backed, recommended)

1. Push this folder to a **private** GitHub repo (never include `.env`).
2. On Connect: **Publish → Import from Git**, branch `main`, directory that contains `manifest.json`.
3. Set **Vars** (same list as below). Do not upload `.env`.

Full steps (create repo, `git add` list, Connect UI, Vars): **[`GITHUB_DEPLOY.md`](GITHUB_DEPLOY.md)**.

### Option B — CLI (`rsconnect`)

```cmd
cd rsc-app
py -m pip install rsconnect-python
rsconnect add --name pfizer-connect --server https://YOUR-CONNECT-HOST --api-key YOUR_API_KEY
rsconnect deploy streamlit . --name "Neo4j QA" --entrypoint app.py
```

### Option C — Push-button publish from IDE

Publish `rsc-app` as a **Streamlit** content item; set primary/entrypoint to **`app.py`**.

### Environment variables on Connect (recommended)

Do **not** rely on uploading `.env` in production. Set Connect **Vars**:

- `NEO4J_URI` = `bolt://10.109.17.64:7687`
- `NEO4J_USERNAME` = `neo4j`
- `NEO4J_PASSWORD` = *(secret)*
- `NEO4J_DATABASE` = `neo4j`
- `VOX_GENAI_API` = `https://mule4api-comm-amer.pfizer.com/vox-genai-api-v2`
- `VOX_TOKEN_GEN_URL` = `https://prodfederate.pfizer.com/as/token.oauth2`
- `VOX_CLIENT_ID` = *(secret)*
- `VOX_CLIENT_SECRET` = *(secret)*
- `VOX_MODEL` = `gpt-4o`

`.rscignore` excludes `.env` from CLI publishes — set the **Vars** above on Connect.
For local testing, keep secrets in `rsc-app/.env` (already gitignored).

## Network checklist

From the **Connect server**, these must be reachable:

1. Neo4j Bolt: `10.109.17.64:7687`
2. Vox token: `https://prodfederate.pfizer.com`
3. Vox API: `https://mule4api-comm-amer.pfizer.com`

If schema load fails after publish, it is almost always firewall / routing between RSC and Neo4j.

## Security

- Prefer Connect Vars for passwords and client secrets.
- Rotate credentials after testing if they were shared in chat or committed by mistake.

## Tset for github