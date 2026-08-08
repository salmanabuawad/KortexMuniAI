#!/usr/bin/env bash
# MuniAI native installer for Ubuntu 24.04 LTS (NO Docker).
# Idempotent: safe to re-run. Never destroys an existing installation.
#
# Usage (as root):  sudo bash scripts/install.sh
set -euo pipefail

APP_DIR=/opt/muniai
APP_USER=muniai
ENV_FILE=/etc/muniai/muniai.env
DOMAIN="${MUNIAI_DOMAIN:-muniai.kortexd.com}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "\033[1;34m[muniai]\033[0m $*"; }
require_root() { [ "$(id -u)" -eq 0 ] || { echo "Run as root."; exit 1; }; }

require_root

# --- 1. OS + hardware detection ---------------------------------------------
log "Ubuntu: $(lsb_release -ds 2>/dev/null || echo unknown)"
log "CPU cores: $(nproc)  RAM: $(free -h | awk '/Mem:/{print $2}')  Disk: $(df -h / | awk 'NR==2{print $4}') free"
if command -v nvidia-smi >/dev/null 2>&1; then
    log "GPU detected: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | head -1)"
else
    log "No NVIDIA GPU detected — MuniAI will run CPU-only (smaller models recommended)."
fi

# --- 2. System packages ------------------------------------------------------
log "Installing system packages…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
    curl ca-certificates gnupg lsb-release ufw git \
    python3 python3-venv python3-dev build-essential \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    tesseract-ocr tesseract-ocr-heb tesseract-ocr-ara \
    ocrmypdf ffmpeg

# pgvector extension package (Ubuntu 24.04 ships postgresql-16).
PG_VER="$(ls /usr/lib/postgresql/ 2>/dev/null | sort -n | tail -1 || true)"
apt-get install -y "postgresql-${PG_VER}-pgvector" || \
    log "WARN: postgresql-${PG_VER}-pgvector not found; install pgvector manually."

# Node.js LTS (for building the frontend).
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
fi

# --- 3. App user + directories ----------------------------------------------
id "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"/{backend,frontend,data/{documents,uploads,processed,thumbnails,audio,temp},models,logs,backups,scripts,config}
mkdir -p /etc/muniai /var/www/certbot

# Sync code (rsync if available, else cp). Excludes venv/node_modules/data.
log "Copying application code to $APP_DIR…"
rsync -a --delete \
    --exclude '.venv' --exclude 'node_modules' --exclude 'dist' \
    --exclude 'data' --exclude 'logs' --exclude 'backups' --exclude 'models' \
    "$REPO_DIR/backend/" "$APP_DIR/backend/"
rsync -a --delete --exclude 'node_modules' --exclude 'dist' \
    "$REPO_DIR/frontend/" "$APP_DIR/frontend/"
cp -r "$REPO_DIR/config/." "$APP_DIR/config/"
cp -r "$REPO_DIR/scripts/." "$APP_DIR/scripts/"

# --- 4. Secrets / env --------------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    log "Creating $ENV_FILE from template (EDIT SECRETS after install)…"
    cp "$REPO_DIR/.env.example" "$ENV_FILE"
    SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
    sed -i "s|^MUNIAI_SECRET_KEY=.*|MUNIAI_SECRET_KEY=${SECRET}|" "$ENV_FILE"
    sed -i "s|^MUNIAI_ENV=.*|MUNIAI_ENV=production|" "$ENV_FILE"
    sed -i "s|^MUNIAI_BASE_URL=.*|MUNIAI_BASE_URL=https://${DOMAIN}|" "$ENV_FILE"
    sed -i "s|^MUNIAI_CORS_ORIGINS=.*|MUNIAI_CORS_ORIGINS=https://${DOMAIN}|" "$ENV_FILE"
    sed -i "s|^MUNIAI_DATA_DIR=.*|MUNIAI_DATA_DIR=${APP_DIR}/data|" "$ENV_FILE"
    chmod 640 "$ENV_FILE"
fi

# --- 5. PostgreSQL -----------------------------------------------------------
log "Configuring PostgreSQL…"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='muniai'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER muniai WITH PASSWORD 'muniai';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='muniai'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE muniai OWNER muniai;"
sudo -u postgres psql -d muniai -c "CREATE EXTENSION IF NOT EXISTS vector;"

# --- 6. Python venv + backend ------------------------------------------------
log "Setting up Python virtualenv…"
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -e "$APP_DIR/backend"

log "Running database migrations + seed…"
( cd "$APP_DIR/backend" && "$APP_DIR/venv/bin/alembic" upgrade head )
( cd "$APP_DIR/backend" && "$APP_DIR/venv/bin/python" -m app.cli bootstrap )

# --- 7. Ollama (local AI) ----------------------------------------------------
if ! command -v ollama >/dev/null 2>&1; then
    log "Installing Ollama…"
    curl -fsSL https://ollama.com/install.sh | sh
fi
log "Pulling local models (chat + embeddings)…"
ollama pull llama3.1:8b || log "WARN: model pull failed; pull manually later."
ollama pull nomic-embed-text || true

# --- 8. Frontend build -------------------------------------------------------
log "Building frontend…"
( cd "$APP_DIR/frontend" && npm ci && npm run build )

# --- 9. Permissions ----------------------------------------------------------
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# --- 10. systemd -------------------------------------------------------------
log "Installing systemd units…"
cp "$APP_DIR/config/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now muniai-api.service
# worker/scheduler depend on the jobs module (later session); enable then.

# --- 11. Nginx + firewall ----------------------------------------------------
log "Configuring Nginx…"
cp "$APP_DIR/config/nginx/muniai.conf" /etc/nginx/sites-available/muniai.conf
ln -sf /etc/nginx/sites-available/muniai.conf /etc/nginx/sites-enabled/muniai.conf
nginx -t && systemctl reload nginx

log "Configuring UFW…"
ufw allow 22/tcp || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
yes | ufw enable || true

log "TLS: run  certbot --nginx -d ${DOMAIN}  once DNS points here."

# --- 12. Health --------------------------------------------------------------
sleep 2
if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null; then
    log "API health check: OK"
else
    log "WARN: API health check failed — see /opt/muniai/logs/api-error.log"
fi

log "Done. MuniAI will be available at https://${DOMAIN}"
log "Bootstrap admin is in ${ENV_FILE} — CHANGE THE PASSWORD after first login."
