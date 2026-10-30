#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-start-1851
W=/srv/opentallas-scratch2/claude/wt/codex-head-start-1851
I=/srv/opentallas-scratch2/claude/die-head-33/start
P=$I/leaf/capture/plan.json
L=/srv/opentallas-scratch2/claude/head-start-2/in/cells.lef
python3 "$R/ports.py" "$W" "$P" "$I/map/start_stages.json" "$R/packed.json" "$R/physical_ports.json" > "$R/ports.log" 2>&1
python3 "$W/tools/s81_head/head_start_edge_drivers.py" --mapped "$I/map/mapped.json" --top ot_die_start_stages --stages "$I/map/start_stages.json" --physical "$R/physical_ports.json" --plan "$P" --ctree "$R/clock" --lef "$L" --out "$R/driven" > "$R/drivers.log" 2>&1
python3 "$W/tools/s81_head/head_start_local_clock.py" --physical "$R/driven/physical.json" --stages "$I/map/start_stages.json" --plan "$P" --ctree "$R/clock" --lef "$L" --out "$R/physical_lc.json" > "$R/local_clock.log" 2>&1
python3 /srv/opentallas-scratch2/claude/head-start-2/start_reach.py --repo "$W" --mapped "$R/driven/mapped.json" --physical "$R/physical_lc.json" --stages "$I/map/start_stages.json" --ctree "$R/clock" --lef "$L" --plan "$P" --out "$R/reach.json" > "$R/reach.log" 2>&1
python3 /srv/opentallas-scratch2/claude/head-start-2/render_reach.py "$W" "$R/driven/mapped.json" "$R/physical_lc.json" "$I/map/start_stages.json" "$R/clock" "$L" "$P" "$R/reach.json" "$R/render" > "$R/render.log" 2>&1
