#!/bin/bash
# First detailed route after reviewed rc0 GRT; no ECO or P&R replay.
set -euo pipefail
cd /
K=/srv/opentallas-scratch2/claude/codex-su-1209/fullx_vL_cts_release
python3 -I - "$K" <<'PY'
import json,sys,pathlib
k=pathlib.Path(sys.argv[1]);assert (k/'run/results/asap7/hbc_ot_hbm_su_pg_lane_full_x_core/base/5_1_grt.odb').is_file()
assert json.load(open(k/'lec/lec.json'))['verdict']=='EQUIVALENT'
for c in ['tt','ff']:
 d=json.load(open(k/f'vis_grt/nominal1551b/postcts_gate_{c}.json'));assert d['parasitics']=='global_routing'
assert 'other 0 other_wns 0.0' in (k/'vis_grt/nominal1551b/FF.log').read_text()
PY
bash "$K/run_kit_hbm.sh" "$K" route 32 16 > "$K/run_route_1551.log" 2>&1
