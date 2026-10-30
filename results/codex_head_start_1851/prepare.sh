#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-start-1851
W=/srv/opentallas-scratch2/claude/wt/codex-head-start-1851
I=/srv/opentallas-scratch2/claude/die-head-33/start
P=$I/leaf/capture/plan.json
L=/srv/opentallas-scratch2/claude/head-start-2/in/cells.lef
python3 "$R/legalize_clock.py" "$W" "$I/leaf/provider" "$P" "$L" "$R/clock" > "$R/legalize.log" 2>&1
python3 "$W/tools/s81_head/head_start_pack.py" --plan "$P" --stages "$I/map/start_stages.json" --mapped "$I/map/mapped.json" --top ot_die_start_stages --ctree "$R/clock" --lef "$L" --out "$R/packed.json" > "$R/pack.log" 2>&1
