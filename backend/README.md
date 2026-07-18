# AuditPipe — strict GPT-5.6 forensic audit

AuditPipe ingests an arbitrary dossier, sends every readable evidence batch to
GPT-5.6, asks GPT-5.6 to synthesize the dossier-level conclusions, verifies all
returned quotes against the original files, and writes an attested report for
the CorteX frontend.

```text
Generic ingestion
  → GPT-5.6 evidence analysis for every batch
  → GPT-5.6 dossier synthesis and adversarial judgment
  → deterministic verbatim-quote verification
  → model-attested JSON
```

The code contains no sample-company identifiers, account exclusions, fixed
fraud findings, expected finding counts, materiality values, detector weights,
or dossier-specific fraud phrases. File structures and fraud categories are
discovered from the uploaded evidence. The only pinned model invariant is
`gpt-5.6`.

## Mandatory model processing

Offline report generation is intentionally unavailable. A run fails without
the OpenAI SDK, `OPENAI_API_KEY`, a completed API response, or a GPT-5.6 model
attestation. Each report records every response ID, requested model, returned
model, and token count under `model_attestation`.

The implementation uses the OpenAI Responses API with medium reasoning effort by
default. Configure the effort with `AUDIT_REASONING_EFFORT`; the model remains
pinned to GPT-5.6.

## Run

```bash
cd backend
pip install -e .
export OPENAI_API_KEY=sk-...

python -m auditpipe.run \
  --data data \
  --out output/findings.json \
  --evidence output/evidence.json

python -m auditpipe.server
```

The frontend API writes uploaded dossiers and generated reports under
`backend/runtime/` by default. Override that root with `CORTEX_RUNTIME_DIR`.

## Configuration

- `OPENAI_API_KEY` — required.
- `AUDIT_REASONING_EFFORT` — `low`, `medium`, `high`, `xhigh`, or `max`.
- `AUDIT_BATCH_CHARACTERS` — maximum evidence characters sent in one analysis batch.
- `AUDIT_MAX_OUTPUT_TOKENS` — response budget for each GPT call.
- `AUDIT_PARALLEL_BATCHES` — maximum concurrent evidence-analysis requests.
- `AUDIT_REQUEST_TIMEOUT_SECONDS` — maximum duration of one OpenAI request.
- `AUDIT_PROMPTS_DIR` — optional directory containing the two audit prompt files.
- `CORTEX_ALLOWED_ORIGINS` — comma-separated frontend origins.
- `CORTEX_API_HOST` and `CORTEX_API_PORT` — API listener settings.

## Integrity rules

- The API never serves a legacy, offline, unattested, or non-GPT-5.6 report.
- Every accepted finding requires at least one inculpatory quote that resolves
  verbatim to an uploaded source file.
- Invalid citations are removed; a finding without verified inculpatory evidence
  is discarded.
- No synthetic fallback findings or citations are created.
- Profit effect is supplied per finding by GPT-5.6 and summed by code without a
  fixed fraud-scheme allowlist.
