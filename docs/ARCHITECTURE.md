# MuniAI — Architecture

## Layers

```
Employees → Nginx/HTTPS → React SPA
                        → FastAPI (/api/v1)
                              ├─ Auth / RBAC            (backend-enforced, spec §15/§62)
                              ├─ AI Orchestrator        → LLMProvider (Ollama; vLLM-ready)
                              ├─ Chat (SSE streaming)
                              ├─ RAG Engine             [later]  PostgreSQL FTS + pgvector
                              ├─ Document Pipeline/OCR  [later]  Celery workers
                              ├─ Vehicle Intelligence   (deterministic rules ✅ / OCR later)
                              ├─ Tool/Integration layer [later]
                              ├─ External-AI escalation [later]  manual, sanitized
                              └─ Audit Engine
                        → PostgreSQL + pgvector · Redis · Ollama (all localhost)
```

## Key principles enforced in code

- **Local-first / zero cloud keys.** `app/core/config.py` has no cloud AI keys;
  the provider registry (`app/ai/registry.py`) only knows local providers.
- **The LLM is not the security boundary.** `require_permission` (`app/auth/deps.py`)
  and document-permission rows (`app/models/documents.py`) gate access before any
  content reaches a model.
- **Deterministic where correctness matters.** Insurance overlap/duplicate/expiry
  math lives in `app/vehicles/insurance_rules.py` — pure Python, unit-tested, never
  delegated to the LLM. AI is used only for OCR assistance, classification, and
  explanation.
- **Provenance is explicit.** Assistant messages carry `origin` (`LOCAL` vs
  `EXTERNAL_IMPORTED`) so the UI never implies MuniAI called a cloud AI.

## Backend module map (`backend/app`)

| Module        | Responsibility                                             |
|---------------|------------------------------------------------------------|
| `core`        | config, logging, uniform error handling                    |
| `db`          | SQLAlchemy base/session, seed/bootstrap                    |
| `models`      | ORM entities (IAM, chat, documents, agents, audit, vehicles) |
| `security`    | password hashing, JWT                                      |
| `auth`        | current-user + permission dependencies                     |
| `ai`          | `LLMProvider` interface + Ollama provider + registry       |
| `audit`       | audit event recording                                      |
| `vehicles`    | deterministic normalization + insurance rules engine       |
| `api/v1`      | routers: auth, meta/health, agents, chat                   |

## Data model (highlights)

`users · departments · roles · permissions · role_permissions · user_roles ·
documents · document_versions · document_permissions · document_chunks ·
embeddings(pgvector) · knowledge_bases · conversations · messages ·
message_sources · agents · tools · agent_tools · jobs · notifications ·
system_settings · integrations · audit_events · external_ai_escalations`

Vehicle module: `vehicles · vehicle_documents · vehicle_document_versions ·
vehicle_document_extractions · insurance_policies · insurance_conflicts ·
vehicle_compliance_rules · vehicle_alerts`.

All PKs are UUIDs; `created_at`/`updated_at` on mutable entities; soft-delete
where useful.
