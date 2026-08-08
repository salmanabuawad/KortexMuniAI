# MuniAI — Roadmap & implementation status

Honest status of each spec area. "✅ done" means implemented and verified in this
foundation; "🟡 partial" means the data model / interface exists; "⬜ later" means
a defined interface with no working feature yet (surfaced in the UI as *Coming Later*).

## Phase 1 (MVP)

| Area                              | Status | Notes |
|-----------------------------------|--------|-------|
| Native Ubuntu layout (no Docker)  | ✅ | `/opt/muniai`, systemd, Nginx, UFW |
| Config / secrets (`muniai.env`)   | ✅ | no cloud AI keys required |
| PostgreSQL + pgvector schema      | ✅ | models + Alembic `0001_initial` (HNSW index) |
| Auth (local) + JWT                | ✅ | bootstrap admin, `/auth/login`,`/me` |
| RBAC (roles/permissions/depts)    | ✅ | backend-enforced `require_permission` |
| AI provider abstraction + Ollama  | ✅ | chat/stream/embeddings/health/models |
| Streaming chat (SSE)              | ✅ | audited, LOCAL-AI indicator |
| Agents framework                  | 🟡 | data model + list API + seeded agents; tool exec later |
| Frontend shell (React/TS/MUI)     | ✅ | login, chat, i18n he/ar/en, RTL |
| Audit engine                      | ✅ | login/logout/ai_query recorded |
| System health endpoint            | ✅ | DB + AI provider |
| Backup / update scripts           | ✅ | `backup.sh`, `update.sh` |
| **Vehicle insurance rules engine**| ✅ | deterministic overlap/duplicate/redundancy/expiry + tests |
| Document upload + pipeline        | ✅ | sync ingest (extract→chunk→embed→index); worker-ready |
| Text extraction (txt/pdf/docx)    | ✅ | PyMuPDF + python-docx |
| OCR for scanned/image docs        | 🟡 | Tesseract path coded (guarded); not installed on server yet |
| Vehicle-document OCR + extraction | ✅ | deterministic extraction + review/verify API + Vehicles UI |
| RAG retrieval + hybrid ranking    | ✅ | pgvector semantic + keyword, permission-filtered; live-verified |
| Source citations                  | ✅ | persisted `message_sources`, shown as [n] chips in chat |
| Document viewer                   | ⬜ | download works; in-page PDF viewer later |
| Global-AI manual escalation       | ✅ | PII sanitizer + prepare/import endpoints + dialog |
| Admin center                      | ✅ | stats, users, models, integrations, audit |
| Setup wizard                      | ⬜ | bootstrap admin + seeding covers first login |

## Phase 2
Microsoft Entra ID (OIDC) · SharePoint/OneDrive/Outlook · Meetings/transcription ·
Vehicle Management connector · Asset Management.

## Phase 3
GIS / street intelligence · road-hazard system · WhatsApp · resident services.

## Recommended next step
Wire the **document upload + pipeline + embeddings + permission-aware RAG +
citations** vertical slice, then the **vehicle-document OCR review UI** on top of
the already-working deterministic insurance engine.
