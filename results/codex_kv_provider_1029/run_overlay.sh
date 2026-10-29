#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-kv-0822
python3 "$R/make_physical_overlay.py" --plan "$R/plan_e27f.json" --constraints "$R/native_bound/constraints/constraints.json" --placements "$R/proposal_open/placements.json" --tools /srv/opentallas-scratch2/claude/wt/codex-kv-0822/tools/die_plan --out "$R/physical_overlay" > "$R/physical_overlay.log" 2>&1
