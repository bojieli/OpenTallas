#!/bin/bash
# DIE-KV-32-SRC: plan std-cell PG access, variant A form (M7 band_share_obs soft + charged per COORD 11:12) + attribution,
# M8-stripe landing mode $1 (off|fallback|first), out dir $2, optional --limit $3. Inputs read-only from DIE-KV-31 / codex-kv-pg-0834.
set -euo pipefail
N=/srv/opentallas-scratch2/claude/die-kv-32-1029/src_phy
C=/srv/opentallas-scratch2/claude/codex-kv-pg-0834
O=/srv/opentallas-scratch2/claude/die-kv-31-1029/src_phy/access/overlay.json
V=/srv/opentallas-scratch2/claude/die-kv-31-1029/venv/bin/python
mkdir -p $N/$2
systemd-run --user --scope -q -p MemoryMax=24G /usr/bin/time -v $V $N/plan_access_v32.py --input $C/grid3_bbox --out $N/$2 --clock-seed $C/grid3_bbox/clock_seed.json --native-overlay $O --soft-block-layer M7 --y-reach 1400 --m8-landing $1 --limit ${3:-0} ${EXTRA:-} > $N/$2.log 2> $N/$2.time
echo DONE $1 $2 $(date -Is) >> $N/$2.log
