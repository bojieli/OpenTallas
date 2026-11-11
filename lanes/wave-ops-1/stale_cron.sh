#!/bin/bash
# WAVE-OPS-1 hourly STALE post (COORD 11-10 (3)): tools/stale_list.py --post rewrites lanes/STALE.tsv and appends one
# queue post grouped by owner lane (unowned -> COORD); committed through coord-commit.sh.  Read-only on the fleet.
# Disable: remove the "wave-ops-1/stale_cron.sh" line from the localhost crontab.
set -u
cd /
C=/home/ubuntu/coord
LOG=/home/ubuntu/.local/state/wave-ops-1/stale_cron.log
mkdir -p /home/ubuntu/.local/state/wave-ops-1
exec 9>/home/ubuntu/.local/state/wave-ops-1/stale_cron.lock; flock -n 9 || exit 0
S="$(date '+%Y-%m-%d %H:%M %Z')"
OUT=$(cd "$C" && timeout 600 python3 -I tools/stale_list.py --post 2>&1)
rc=$?
echo "$S rc=$rc $(echo "$OUT" | head -1 | cut -c1-200)" >> "$LOG"
[ $rc -eq 0 ] || exit 0
cd "$C" && timeout 280 "$C/bin/coord-commit.sh" "WAVE-OPS-1 STALE hourly $S (DO_NOT_COUNT)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" lanes/COORD-REVIEW-QUEUE.md lanes/STALE.tsv >> "$LOG" 2>&1
