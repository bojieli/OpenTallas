#!/bin/bash
set -euo pipefail
cd /
W=/srv/opentallas-scratch3/claude/codex-su-1551/ksh_source
D=/srv/opentallas-scratch3/claude/codex-su-1551/kits/ksh_v700_f3
P=/srv/opentallas-scratch2/claude/kw24/hbm_d44v_7281a
mkdir -p "$D"
touch "$D/.keep"
test -z "$(git -C "$W" status --porcelain=v1 -uno)"
python3 -I "$W/results/die_hbm_1107/codex_su1551/ksh_local3/gen_f3.py" --views "$W/results/die_hbm_1107/codex_su1551/ksh_local3/ksh_views_v700.json" --view ot_hbm_svc_vm_kshare_splitstrap__v700685@5d7908703d6a --out "$D" --clock-pin-entry on --core-macros auto --util 0.40 --max-fanout 8 --sigmax M6 --face-reset-relay 2 --clock-regions "$P/core_clock_regions.json" --clock-taps density --clock-taps-shallow --tag _vF3 > "$D/gen.log" 2>&1
find "$D" -maxdepth 2 -name freeze.json -print
