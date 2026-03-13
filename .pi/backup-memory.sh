#!/bin/bash
# OpenClaw Memory Backup Script
# Runs daily to backup workspace files to OneDrive

SOURCE_DIR="/Users/aiserver/.openclaw/workspace"
BACKUP_DIR="/Users/aiserver/srv/backup/openclaw"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="openclaw_backup_${DATE}.tar.gz"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Create tar.gz archive of critical files
cd "$SOURCE_DIR" || exit 1

tar -czf "${BACKUP_DIR}/${BACKUP_FILE}" \
    --exclude='.git' \
    --exclude='dashboard-site/node_modules' \
    --exclude='.pi' \
    AGENTS.md \
    BOOTSTRAP.md \
    HEARTBEAT.md \
    IDENTITY.md \
    MEMORY.md \
    SOUL.md \
    TOOLS.md \
    USER.md \
    memory/ \
    avatars/ \
    2>>"$LOG_FILE"

if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS: Backup created - ${BACKUP_FILE}" >> "$LOG_FILE"
    
    # 同時複製一份到 OneDrive（如果權限允許）
    ONEDRIVE_DIR="/Users/aiserver/srv/sync/OneDrive/ai_source/backup/openclaw"
    if [ -d "$ONEDRIVE_DIR" ]; then
        cp "${BACKUP_DIR}/${BACKUP_FILE}" "${ONEDRIVE_DIR}/" 2>/dev/null || true
    fi
    
    # Keep only last 30 backups (delete older ones)
    ls -t "${BACKUP_DIR}"/openclaw_backup_*.tar.gz 2>/dev/null | tail -n +31 | xargs -r rm -f
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Cleaned up old backups (kept last 30)" >> "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup failed" >> "$LOG_FILE"
    exit 1
fi

exit 0
