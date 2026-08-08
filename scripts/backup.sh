#!/usr/bin/env bash
# MuniAI backup — PostgreSQL + documents + config. Does NOT back up downloadable
# LLM model files (spec §43). Retention configurable via MUNIAI_BACKUP_KEEP_DAYS.
set -euo pipefail

APP_DIR=/opt/muniai
BACKUP_DIR="$APP_DIR/backups"
ENV_FILE=/etc/muniai/muniai.env
STAMP="$(date +%Y%m%d-%H%M%S)"
KEEP_DAYS="${MUNIAI_BACKUP_KEEP_DAYS:-30}"

mkdir -p "$BACKUP_DIR"
echo "[backup] starting $STAMP"

# Database (parse DB name from DATABASE_URL; default 'muniai').
DB_NAME="$(grep -oP 'MUNIAI_DATABASE_URL=.*/\K[^?]+' "$ENV_FILE" 2>/dev/null || echo muniai)"
sudo -u postgres pg_dump -Fc "$DB_NAME" > "$BACKUP_DIR/db-$STAMP.dump"

# Documents + config.
tar -czf "$BACKUP_DIR/data-$STAMP.tar.gz" -C "$APP_DIR" data
tar -czf "$BACKUP_DIR/config-$STAMP.tar.gz" -C / etc/muniai

# Retention.
find "$BACKUP_DIR" -type f -mtime +"$KEEP_DAYS" -name '*.dump' -delete
find "$BACKUP_DIR" -type f -mtime +"$KEEP_DAYS" -name '*.tar.gz' -delete

echo "[backup] complete → $BACKUP_DIR (db-$STAMP.dump)"
echo "[backup] restore: sudo -u postgres pg_restore -c -d $DB_NAME $BACKUP_DIR/db-$STAMP.dump"
