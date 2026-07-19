# AI Contract Review

An AI-powered contract review system that leverages **Temporal Workflows**, **FastAPI**, and an **OpenAI-compatible LLM API** (Groq / OpenAI / OpenRouter) to analyze, summarize, and compare legal contracts stored in AWS S3.

---

## Features

- 📄 Process multiple PDF contracts
- 🤖 AI-powered contract summarization (per-contract) + cross-contract risk synthesis
- ⚡ Temporal workflows for reliable, retryable background processing
- 🔀 Parallel processing via child workflows (fan-out / fan-in)
- ☁️ Download contracts directly from AWS S3 (S3-compatible storage) "idrivee2"
- 🌐 FastAPI REST API

> **Note:** PostgreSQL/Docker Compose files exist under `setup/` for local infra experiments, but the current application code does not read/write to a database — all state lives in Temporal.

---

## Tech Stack

- Python 3.x
- FastAPI
- Temporal (Python SDK, `temporalio`)
- PyMuPDF / `pymupdf4llm` (PDF → Markdown extraction)
- OpenAI-compatible client, pointed at Groq by default
- AWS S3 (Boto3, S3-compatible endpoint)

---

## Project Structure

## Project Structure
 
```text
.
├── app/
│   ├── ai-contract-review/        # this project
│   │   ├── Docker/
│   │   │   ├── Dockerfile         # builds worker + api into one image
│   │   │   └── docker-compose.yml # Temporal + Postgres + Temporal UI + worker + api
│   │   ├── activities.py          # extract_pdf, call_llm activities
│   │   ├── child_workflow.py      # PDFSummaryWorkflow (per-PDF)
│   │   ├── parent_workflow.py     # ContractReviewWorkflow (fan-out/fan-in)
│   │   ├── prompts.py             # summary / synthesis / revision prompts
│   │   ├── worker.py              # Temporal worker entrypoint
│   │   ├── requirements.txt
│   │   └── .env
│   ├── client-app/
│   │   └── main.py                # FastAPI app (lives here, not in ai-contract-review/)
│   ├── pdf-extraction/            
│   └── pdf-extraction-temporal/   
│
├── setup/
│   └── samples-server/
│       └── compose/
│           └── docker-compose-postgres.yml   # legacy/unused — superseded by Docker/docker-compose.yml above
│
├── temporal/                      # local Temporal CLI / venv artifacts
└── .env
```

---

## Prerequisites

- Python 3.11+
- A running Temporal server (self-hosted or Temporal CLI dev server)
- An S3-compatible bucket + credentials 
- An API key for at least one LLM provider (Groq, OpenAI, or OpenRouter)

---

## Create Virtual Environment

Linux / macOS
```bash
python -m venv venv
source venv/bin/activate
```

Windows
```powershell
python -m venv venv
venv\Scripts\activate
```

---

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file in `app/ai-contract-review/`:

---
 
## Run with Docker
 
The easiest way to run everything (Temporal server + its Postgres backing store + Temporal Web UI + the worker + the FastAPI app) is via the provided Docker Compose setup.

### Start everything
 
```bash
cd app/ai-contract-review/Docker
docker compose up --build
```
### Resetting from scratch
 
If Temporal's Postgres volume ever gets into a bad state (e.g. an interrupted schema setup), wipe it and start clean:
 
```bash
docker compose down -v
docker compose up --build
```

## Start Temporal Server

Using the Temporal CLI dev server (simplest option):

```bash
temporal server start-dev
```

Or via your own Temporal cluster — just make sure `TEMPORAL_HOST` / `TEMPORAL_NAMESPACE` in `.env` point to it.

---

## Start the Worker

```bash
cd app/ai-contract-review
python worker.py
```

This registers `ContractReviewWorkflow`, `PDFSummaryWorkflow`, and the `extract_pdf` / `call_llm` activities on `TEMPORAL_TASK_QUEUE`.

---

## Start the FastAPI App

```bash
uvicorn main:app --reload
```

Default docs:
```
http://localhost:8000/docs
```

---

## API Examples

### Health check
```
GET /health
```

### Start a contract review (async)
```
POST /contract-review/start
```
Request body:
```json
{
  "s3_paths": [
    "s3://your-bucket/legal-docs/vendor-service-agreement.pdf",
    "s3://your-bucket/legal-docs/nda-innovate-consultpro.pdf",
    "s3://your-bucket/legal-docs/software-license-globalsoft.pdf"
  ]
}
```
Response:
```json
{
  "workflow_id": "contract-review-<uuid>"
}
```

### Check workflow status / result
```
GET /workflow/status/{workflow_id}
```
Response:
```json
{
  "workflow_id": "contract-review-<uuid>",
  "workflow_status": "COMPLETED",
  "workflow_result": { "report": "...", "source": ["..."], "approved_by": "System" }
}
```



---

## Workflow

```
Client
  │
  ▼
FastAPI (main.py)
  │
  ▼
ContractReviewWorkflow (parent_workflow.py)
  │
  ├─────────────┬─────────────┐
  ▼             ▼             ▼
PDFSummaryWorkflow (one per PDF, run in parallel via child workflows)
  │
  ├─ extract_pdf activity   (download from S3 + PyMuPDF → Markdown)
  ├─ call_llm activity      (per-contract summary + key risks)
  ▼
Return PDFSummaryOutput to parent
  │
  ▼
Parent aggregates all summaries
  │
  ▼
call_llm activity (cross-contract synthesis)
  │
  ▼
ContractReviewOutput (report, source, approved_by)
```

---

## Troubleshooting

**Missing API key**
```
KeyError: 'GROQ_API_KEY'
```
Ensure `.env` is present and loaded (`load_dotenv()` runs on import) and the key names match exactly.

**LLM 402 / rate-limit errors**
Check your provider account (Groq/OpenAI/OpenRouter) has available credits/quota.

**S3 download errors**
Verify `AWS_S3_ENDPOINT_URL`, region, and credentials match your S3-compatible provider, and that `TEMP_DIR` exists and is writable.

**Temporal connection error**
Confirm the Temporal server is reachable at `TEMPORAL_HOST` before starting `worker.py` or the FastAPI app.

---
