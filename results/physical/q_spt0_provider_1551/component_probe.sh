#!/bin/bash
set -euo pipefail
cd /
R=/srv/opentallas-scratch2/claude/codex-hbm-types-1551/q_spt0_native
S=/srv/opentallas-scratch2/claude/kw31/src_66d55
python3 -I -c 'import gzip,pathlib; r=pathlib.Path("/srv/opentallas-scratch2/claude/codex-hbm-types-1551/q_spt0_native");(r/"current66.json").write_bytes(gzip.decompress((r/"current66.json.gz").read_bytes()))'
python3 -I "$S/tools/die_plan/bind.py" component-proof /srv/opentallas-scratch2/claude/hbm-bind-9/m79fp/die_plan.json --out /srv/opentallas-scratch2/claude/hbm-bind-9/g_t11m79f --type q_spt0 --instance NW_spt0 --prepared-plan "$R/current66.json" --bind-context /srv/opentallas-scratch2/claude/hbm-bind-9/m79fp/die_plan.json --asbuilt /srv/opentallas-scratch2/claude/hbm-bind-6/tip2/physical/die_plan/hbm/bind/d44v/asbuilt_t11.json --receipt "$R/component_current66.json" > "$R/component_current66.log" 2>&1
