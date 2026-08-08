#!/usr/bin/env bash
# MuniAI safe update: preflight -> backup -> update code -> deps -> build ->
# migrate -> restart -> health. Never deletes production data (spec §44).
set -euo pipefail

APP_DIR=/opt/muniai
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "\033[1;34m[update]\033[0m $*"; }
[ "$(id -u)" -eq 0 ] || { echo "Run as root."; exit 1; }

log "1/8 Preflight…"
systemctl is-active --quiet postgresql || { echo "PostgreSQL not running"; exit 1; }

log "2/8 Backup…"
bash "$APP_DIR/scripts/backup.sh"

log "3/8 Stop API…"
systemctl stop muniai-api.service || true

log "4/8 Update code…"
rsync -a --delete \
    --exclude '.venv' --exclude 'node_modules' --exclude 'dist' \
    --exclude 'data' --exclude 'logs' --exclude 'backups' --exclude 'models' \
    "$REPO_DIR/backend/" "$APP_DIR/backend/"
rsync -a --delete --exclude 'node_modules' --exclude 'dist' \
    "$REPO_DIR/frontend/" "$APP_DIR/frontend/"
cp -r "$REPO_DIR/config/." "$APP_DIR/config/"
cp -r "$REPO_DIR/scripts/." "$APP_DIR/scripts/"

log "5/8 Python deps…"
"$APP_DIR/venv/bin/pip" install -e "$APP_DIR/backend"

log "6/8 Frontend build…"
( cd "$APP_DIR/frontend" && npm ci && npm run build )

log "7/8 Migrate…"
( cd "$APP_DIR/backend" && "$APP_DIR/venv/bin/alembic" upgrade head )

chown -R muniai:muniai "$APP_DIR"
cp "$APP_DIR/config/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload
systemctl start muniai-api.service

log "8/8 Health check…"
sleep 3
if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null; then
    log "Update OK."
else
    echo "[update] HEALTH CHECK FAILED — check /opt/muniai/logs/api-error.log"
    exit 1
fi
