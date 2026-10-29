#!/bin/bash
# DIE-KV-32-SRC: apply_access (Codex pgh/src/apply_access.py, read-only) of the clean plan $1 onto the DIE-KV-31 src_phy
# native_grid.odb (read-only) -> access/access.odb (expected 75,934 contacts, non-PG sha unchanged).
set -euo pipefail
N=/srv/opentallas-scratch2/claude/die-kv-32-1029/src_phy
P=/srv/opentallas-scratch2/claude/die-kv-31-1029/src_phy
H=/srv/opentallas-scratch2/claude/die-kv-31-1029/pgh
C=/srv/opentallas-scratch2/claude/codex-kv-pg-0834
mkdir -p $N/access
docker run --rm --name dkv32-apply --memory=96g --cpus=2 -v $N:/n -v $P:/p:ro -v $H:/h:ro -v $C:/c:ro openroad/orfs:latest bash -lc "set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -python -no_init -exit /h/src/apply_access.py --odb /p/pg_grid/native_grid.odb --plan /n/$1 --grid /c/grid3_bbox/pg_rects.json --out /n/access/access.odb > /n/access/apply.log 2>&1; chown -R 1000:1000 /n/access"
echo STAGE_DONE apply $(date -Is)
