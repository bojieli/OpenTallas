#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
python3 "$R/rebuild_abstracts.py" --plan /srv/opentallas-scratch2/claude/wt/codex-kv-0822/results/die_kv_29_1029/event27f/plan_reserved.json --windows "$R/physical_overlay/island_windows.json" --kit "$R/source_kit" --tools /srv/opentallas-scratch2/claude/wt/codex-kv-0822/tools/die_plan --out "$R/full_abstracts" > "$R/full_abstracts.log" 2>&1
