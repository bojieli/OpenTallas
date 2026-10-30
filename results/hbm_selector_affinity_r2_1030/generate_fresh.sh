#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
W=/srv/opentallas-scratch2/claude/wt/codex-hbm-selector-roles-1030
R=/srv/opentallas-scratch2/claude/codex-hbm-selector-1030/roles_fresh
P=/srv/opentallas-scratch2/claude/die-hbm-32/plan/d32q
V=/srv/opentallas-scratch2/claude/hbm-cores-kits-26/k32/views_d32q.json
cd "$W"
python3 results/die_hbm_kits_1027/mk_c20.py "$P" "$V" "$R/slice" "$R/kits" "$W" ot_hbm_idx_selector_static_sel --islands-only --ft-pin-dx-um 1.08 > "$R/slice.log" 2>&1
python3 "$R/generate_roles.py" --repo "$W" --views "$V" --slice "$R/slice" --out "$R/kits" > "$R/generate.log" 2>&1
for K in "$R"/kits/ot_hbm_idx_selector_static_sel_*; do
 python3 tools/die_plan/kit_preflight.py --contract --plan-dir "$P" --out "$K/preflight_candidate.json" "$K" > "$K/preflight_candidate.log" 2>&1
 tail -3 "$K/preflight_candidate.log"
done
