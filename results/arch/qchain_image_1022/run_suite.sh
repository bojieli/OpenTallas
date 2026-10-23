#!/bin/bash
set -eu
R=/srv/opentallas-scratch/claude/codex-qdie-2000
S=$R/dv2f21g5r52cxc/src
O=$R/qchain_r53_seam
mkdir -p "$O"
cd "$S"
export D2D_MU=1 D2D_EMB_WINDOW=595 D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213
D2D_DIE_STAGES=2,2,2,3,2,2/11,11,9,9,9,9,9 bash "$R/d2d_production_current.sh" "$O/reproduce" > "$O/reproduce.log" 2>&1
BASE=0
cmp "$O/reproduce/d2d_cal_image.svh" rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew595_r16.svh || BASE=$?
printf 'BASELINE_REPRODUCE_RC %s\n' "$BASE"
D2D_STATUS_OFS=$(python3 - <<'PYS'
import sys
sys.path[:0]=['tools/qwen_split']
import d2d_link_calendar as L
stages=L.parse_stages('3,3,3,3,2,2/11,11,9,9,9,9,9')
txd=L.producer_txd(stages,kv_codec=2)
for e,extra in {'C':[2,2,0,2],'K':[2,2,2,2]}.items():
 txd[e]=[v+x for v,x in zip(txd[e],extra)]
for ofs in range(40,49):
 msgs,_=L.layer_msgs(0,0,[100,100,100,4000],8,7,ofs,status_delay=213,attn_tx_shift=1)
 try:L.compile_cal(msgs,6,7,0,txd)
 except SystemExit:continue
 print(ofs);break
else:raise SystemExit('no STATUS slot in existing source compiler search40..48')
PYS
)
export D2D_STATUS_OFS
printf 'CURRENT_SOURCE_STATUS_OFS %s\n' "$D2D_STATUS_OFS"
D2D_DIE_STAGES=3,3,3,3,2,2/11,11,9,9,9,9,9 bash "$R/d2d_production_current.sh" "$O/current_seam" > "$O/current_seam.log" 2>&1
printf 'SEAM_DIAGNOSTIC_ONLY: EW595 preserved; current ROPE/headprepare/F16 programme still open\n'
sha256sum "$O/current_seam/d2d_cal_image.svh"

D2D_ROPE=1 D2D_EMB_WINDOW=1627 D2D_DIE_STAGES=3,3,3,3,2,2/11,11,9,9,9,9,9 bash "$R/d2d_production_current.sh" "$O/rope1627_model" > "$O/rope1627_model.log" 2>&1
printf 'ROPE1627_MODEL_ONLY: current head_prepare transport not yet available; no token qualification\n'
python3 - "$O" <<'PYC'
from pathlib import Path
import json,sys
r=Path(sys.argv[1])
for n in ('reproduce','current_seam','rope1627_model'):
 p=r/n/'program/calendar.json';d=json.loads(p.read_text());print(n,'topkeys',list(d));print(json.dumps(d.get('program',{}),sort_keys=True))
PYC
exit "$BASE"
