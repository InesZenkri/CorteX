# CorteX

Evidence-first fraud investigation for auditors. CorteX turns a dossier into a cited entity graph, ranked findings, and document-level proof.

## Repository

- `frontend/` — React + Vite auditor workspace (frontend-owned)
- `backend/` — reserved for the FastAPI service (backend-owned)
- `openapi.yaml` — shared API contract and integration source of truth

## Run locally

```bash
cd frontend && npm install
cd ../backend && python3 -m venv .venv && .venv/bin/pip install -e .
```

Run the two services in separate terminals from the repository root:

```bash
npm run dev:backend
npm run dev:frontend
```

Vite proxies `/api` to FastAPI on port 8000. Set `VITE_API_BASE_URL` only when the API is hosted elsewhere. The legacy demo API is available explicitly with `VITE_USE_MOCK_API=true`.
Investigations require GPT-5.6 processing. Provide `OPENAI_API_KEY` in the project or backend `.env`; the backend rejects offline or unattested report generation.

## Quality checks

```bash
npm run typecheck
npm run test
npm run build
```

All financial values arrive as strings. Every finding, contradiction, graph relationship, and monetary value carries citations. The backend should return `404` when cited documents are unavailable and `422` for invalid review mutations.
