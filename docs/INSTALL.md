# MuniAI — Installation

## Production (native Ubuntu 24.04, no Docker)

Target host for this deployment: **muniai.kortexd.com**.

1. Point DNS `A muniai.kortexd.com → <server IP>`.
2. Copy the repo to the server (e.g. `git clone` or `rsync`), then:

   ```bash
   sudo MUNIAI_DOMAIN=muniai.kortexd.com bash scripts/install.sh
   ```

   The installer: installs apt packages (PostgreSQL, pgvector, Redis, Nginx,
   Node 20, Tesseract he/ar/en, OCRmyPDF, ffmpeg), creates the `muniai` user and
   `/opt/muniai`, writes `/etc/muniai/muniai.env` with a generated secret,
   creates the DB + `vector` extension, builds the venv, runs migrations + seed,
   installs Ollama and pulls `llama3.1:8b` + `nomic-embed-text`, builds the
   frontend, installs the `muniai-api` systemd unit, configures Nginx + UFW, and
   runs a health check.

3. Issue TLS once DNS resolves:

   ```bash
   sudo certbot --nginx -d muniai.kortexd.com
   ```

4. Open `https://muniai.kortexd.com`, sign in with the bootstrap admin from
   `/etc/muniai/muniai.env`, and **change the password**.

Updates later: `sudo bash scripts/update.sh` (backs up, then updates safely).
Backups: `sudo bash scripts/backup.sh` (or schedule via cron / the scheduler unit).

## Local development (Windows or Linux)

Prereqs: Python 3.11+, Node 20+, PostgreSQL 14+ with pgvector, optional Ollama.

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate      # Linux: source .venv/bin/activate
pip install -e ".[dev]"
copy ..\.env.example .env                            # edit MUNIAI_DATABASE_URL
alembic upgrade head
python -m app.cli bootstrap
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api → :8000)
```

Without a local Ollama, the app runs but chat responses will report the AI
service as unavailable — that is expected and surfaced clearly in the UI.

## Verification performed in this foundation
- Backend imports + app builds; `pytest` → **13 passed** (insurance rules + RBAC).
- Frontend `tsc -b && vite build` → **build OK**.
- Full DB migration / live chat require PostgreSQL+pgvector and a running Ollama,
  provisioned by `install.sh` on the target host.
