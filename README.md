<div align="center">
  <img src="frontend/public/cortex.png" alt="CorteX logo" width="220" />

  <h1>CorteX</h1>

  <p><strong>Follow the money. Find the fraud. Prove it.</strong></p>
  <p>An evidence-first AI workspace that turns messy audit dossiers into traceable findings, cited relationships, and source-level proof.</p>

  <p>
    <img alt="React" src="https://img.shields.io/badge/React-19-20232a?logo=react&logoColor=61DAFB" />
    <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white" />
    <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi&logoColor=white" />
    <img alt="OpenAI" src="https://img.shields.io/badge/Powered%20by-GPT--5.6-111111?logo=openai&logoColor=white" />
    <img alt="Evidence first" src="https://img.shields.io/badge/Evidence-source%20verified-6C5CE7" />
  </p>
</div>

---

## The problem we wanted to solve

AI can read a company dossier and declare *“fraud”* in seconds. In a real audit, that answer is useless unless an auditor can verify exactly how it was reached.

Audit teams work across PDFs, spreadsheets, exports, contracts, confirmations, invoices, and scanned evidence. The important contradiction is rarely contained in one file. It appears between files: the ledger disagrees with the bank confirmation, two supposedly independent suppliers share an account, or a payment predates the document that authorized it.

At the same time, false positives are expensive. A discrepancy may come from foreign exchange, cut-off timing, VAT treatment, partial delivery, or a credit note. An investigation tool therefore needs more than pattern recognition—it needs provenance, adversarial reasoning, and a human review path.

This is the broader problem space in which [Cortea](https://www.cortea.ai/de) works: AI-assisted audit quality, consistency checks, traceable evidence, and workflows where auditors retain control over conclusions. **CorteX is an independent hackathon project and is not affiliated with or endorsed by Cortea.**

## Our answer

> **The model proposes. The system verifies. The auditor decides.**

CorteX converts an uploaded folder hierarchy into an interactive investigation workspace. It analyzes the dossier with GPT-5.6, rejects claims whose quotations cannot be resolved to an uploaded source, and presents surviving findings through a cited entity graph and review workflow.

The primary journey is deliberately simple:

```text
Suspicious relationship
        ↓
Ranked finding
        ↓
Reasoning and contradiction chain
        ↓
Exact source document and passage
        ↓
Auditor confirms, rejects, or requests review
```

## The pipeline

```mermaid
flowchart LR
    A[Upload dossier] --> B[Generic ingestion]
    B --> C[GPT-5.6 evidence batches]
    C --> D[Dossier synthesis]
    D --> E[Deterministic quote verification]
    E --> F[Entity graph]
    F --> G[Ranked findings]
    G --> H[Auditor review]

    C -. source passages .-> E
    E -. rejects invalid citations .-> D
```

### 1. Generic ingestion

CorteX preserves nested folder structures and reads common audit evidence formats including PDF, CSV, XLSX, DOCX, TXT, XML, and GDPdU-style exports. No sample-company names, expected fraud labels, or dossier-specific conclusions are hardcoded into the pipeline.

### 2. Evidence analysis

Readable evidence is divided into bounded batches and analyzed concurrently with GPT-5.6. The model identifies facts, relationships, control failures, contradictions, and unusual transactions while retaining the supporting source filename and verbatim quotation.

### 3. Cross-document synthesis

The dossier-level pass combines observations across documents. This is where deeper schemes emerge: shared identifiers, inconsistent balances, suspicious timing, related parties, or evidence that does not reconcile across independent sources.

### 4. Verification gate

Every proposed citation is checked against the original uploaded content. A finding without verified inculpatory evidence is discarded. The backend does not manufacture placeholder citations or silently publish an offline fallback report.

### 5. Auditor workspace

Verified output becomes:

- An explorable backend-generated entity graph
- Ranked findings and observations
- Minimal contradiction sets
- Linked source passages
- Human confirm, reject, and needs-review controls
- A live investigation journey showing actual backend stages

## What makes CorteX different

| Principle | How CorteX applies it |
|---|---|
| No number without a source | Financial claims retain supporting evidence and citations |
| No black-box verdict | Findings expose their narrative, evidence, and linked graph path |
| No silent fallback | Investigations require successful GPT-5.6 processing and attestation |
| No synthetic proof | Unresolvable quotations are removed before findings reach the UI |
| No automatic conviction | The auditor remains responsible for the final review decision |
| No flattened dossier | Uploaded subfolders and relative paths are preserved |

## Product experience

### Folder-native evidence intake

Drop one or multiple audit folders into the browser. CorteX preserves their hierarchy, calculates file and folder sizes, caches the browser selection locally, and lets auditors inspect individual files before starting an investigation.

### Live investigation

The workspace streams real backend stages—evidence reading, concurrent GPT batches, synthesis, and quote verification—while a responsive activity flow explains the work currently happening.

### Graph-driven investigation

The frontend renders the graph returned by FastAPI. Backend data controls the entities, relationships, risks, citations, linked findings, and explanations; React Flow only handles layout and interaction.

### Evidence-level review

Selecting a citation opens the underlying backend document. Text evidence is highlighted directly, while PDFs open at the cited page.

## Architecture

```text
CorteX/
├── frontend/                 React + TypeScript + Vite auditor workspace
│   ├── public/cortex.png     Project logo
│   └── src/                  Upload, documents, graph, findings, evidence UI
├── backend/                  FastAPI + GPT-5.6 forensic pipeline
│   ├── auditpipe/            Ingestion, LLM, verification, API adapters
│   ├── prompts/              Evidence-analysis and synthesis prompts
│   └── runtime/              Local uploaded dossiers and generated reports
├── openapi.yaml              Shared frontend/backend API contract
└── package.json              Root development commands
```

## Technology

**Frontend:** React, TypeScript, Vite, TanStack Query, React Flow, Lucide, PDF/browser previews.

**Backend:** Python, FastAPI, OpenAI Responses API, Pydantic, PyPDF, OpenPyXL, python-docx.

**Model:** GPT-5.6 with recorded response IDs, returned model identifiers, and token usage in the report attestation.

## Run locally

### 1. Install

```bash
npm --prefix frontend install

cd backend
python3 -m venv .venv
.venv/bin/pip install -e .
cd ..
```

### 2. Configure the backend

Create `backend/.env`:

```env
OPENAI_API_KEY=your_openai_api_key

# Optional tuning
AUDIT_REASONING_EFFORT=medium
AUDIT_PARALLEL_BATCHES=4
AUDIT_REQUEST_TIMEOUT_SECONDS=600
```

Create `frontend/.env.local`:

```env
VITE_USE_LLM=true
```

`OPENAI_API_KEY` must remain in the backend. Never expose it through a `VITE_` variable.

### 3. Start both services

Open two terminals from the repository root:

```bash
# Terminal 1 — FastAPI on http://127.0.0.1:8000
npm run dev:backend
```

```bash
# Terminal 2 — Vite on http://localhost:5173
npm run dev:frontend
```

Vite proxies `/api` to FastAPI during local development.

## API contract

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/upload` | Upload a nested dossier |
| `POST` | `/api/investigate` | Start the GPT-5.6 investigation |
| `GET` | `/api/investigation/summary` | Poll real processing stage and status |
| `GET` | `/api/dossiers` | Retrieve the active dossier |
| `GET` | `/api/dossiers/{id}/documents` | List uploaded evidence |
| `GET` | `/api/dossiers/{id}/graph` | Retrieve the generated entity graph |
| `GET` | `/api/dossiers/{id}/findings` | Retrieve ranked findings |
| `GET` | `/api/findings/{id}` | Retrieve reasoning and citations |
| `PATCH` | `/api/findings/{id}` | Record an auditor decision |
| `GET` | `/api/documents/{id}/file` | Open the original source document |

The complete shared schema is defined in [`openapi.yaml`](openapi.yaml).

## Quality checks

```bash
npm run typecheck
npm run test
npm run build

backend/.venv/bin/python -m unittest discover -s backend/tests -p 'test_*.py'
```

## Current scope

CorteX currently focuses on the investigation workflow: upload, AI evidence analysis, source verification, entity graph exploration, findings, document inspection, and auditor review.

Authentication, multi-user permissions, workpaper export, and free-form cited audit chat are future milestones.

---

<div align="center">
  <strong>CorteX</strong><br />
  <sub>AI can raise the suspicion. Evidence has to prove it.</sub>
</div>
