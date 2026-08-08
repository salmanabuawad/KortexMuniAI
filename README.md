# MuniAI

**A private, local-first AI platform for a municipality.**

MuniAI is the municipality's secure AI layer over its documents, knowledge,
departments and (later) municipal systems. It is **not** just a chatbot.

## Core principles

1. Municipal data stays **local by default**.
2. **Local AI is the default AI** (Ollama; vLLM-ready via a provider interface).
3. **No municipal data is ever automatically sent to any cloud AI.**
4. External AI escalation is **manual and user-controlled** (sanitized prompt, copy/paste).
5. Every answer respects **user + department permissions** (enforced in the backend, not the prompt).
6. Answers from documents **show their sources**.
7. Everything important is **auditable**.
8. **Hebrew, Arabic and English** are first-class (RTL/LTR).
9. Core functions work **without internet**.
10. The architecture is **modular** — new municipal systems connect via a tool/API layer.

## Status — Phase 1 (MVP), foundation

This repository currently contains the **working foundation**:

- ✅ Native (no Docker) project layout under `/opt/muniai`
- ✅ FastAPI backend: config, DB session, security (bcrypt + JWT), error handling, health
- ✅ PostgreSQL + pgvector schema (SQLAlchemy models + Alembic migration)
- ✅ Local auth + RBAC (roles, permissions, departments) with bootstrap admin
- ✅ AI provider abstraction + **OllamaProvider** (chat / stream / embeddings / health)
- ✅ Conversations + **streaming chat** (SSE), audited, with LOCAL-AI indicator
- ✅ Agents framework (data model + list API); default municipal agents seeded
- ✅ React + TypeScript + Vite + MUI shell: login, chat, i18n (he/ar/en) with RTL
- ✅ Ops scaffolding: `install.sh`, systemd units, Nginx config, `backup.sh`, `update.sh`

Marked clearly as **interface-for-later / Coming Later** (not faked as working):
document pipeline & OCR, RAG retrieval, source citations & viewer, vehicle-document
OCR / insurance-intelligence engine, global-AI escalation UI, admin center, Entra/M365,
meetings, GIS, WhatsApp. See `docs/ROADMAP.md`.

## Repository layout

```
muniai/
├── backend/     FastAPI app, models, migrations, tests
├── frontend/    React + TS + Vite + MUI
├── scripts/     install / update / backup (native Ubuntu, systemd)
├── config/      nginx + systemd unit templates
├── data/        local filesystem storage (gitignored)
├── docs/        architecture, install, roadmap
├── models/      local LLM/embedding models (gitignored)
├── logs/ backups/
```

## Quick start (local development, Windows or Linux)

Prerequisites: Python 3.11+, Node 20+, PostgreSQL 14+ with pgvector, (optional) Ollama.

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cp ../.env.example .env                              # edit DATABASE_URL etc.
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

API docs: http://localhost:8000/api/v1/docs · Frontend: http://localhost:5173

## Production (native Ubuntu 24.04, no Docker)

See [docs/INSTALL.md](docs/INSTALL.md). Run `scripts/install.sh` as root; it installs
PostgreSQL+pgvector, Redis, Nginx, Node, creates the `muniai` user, builds the frontend,
installs systemd units, and configures UFW/HTTPS.

## License / ownership

Built by Kortex Digital. Product name **MuniAI**; reusable across municipalities
(branding is configurable, not hard-coded).
