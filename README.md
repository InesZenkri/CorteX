# CorteX

Evidence-first fraud investigation for auditors. CorteX turns a dossier into a cited entity graph, ranked findings, and document-level proof.

## Repository

- `frontend/` — React + Vite auditor workspace (frontend-owned)
- `backend/` — reserved for the FastAPI service (backend-owned)
- `openapi.yaml` — shared API contract and integration source of truth

## Run locally

```bash
cd frontend
npm install
npm run dev
```

The frontend uses an in-browser API simulator by default. Set `VITE_API_BASE_URL=http://localhost:8000` to connect the same client to FastAPI. Set `VITE_USE_MOCK_API=false` to disable the simulator.

## Quality checks

```bash
npm run typecheck
npm run test
npm run build
```

All financial values arrive as strings. Every finding, contradiction, graph relationship, and monetary value carries citations. The backend should return `404` when cited documents are unavailable and `422` for invalid review mutations.

