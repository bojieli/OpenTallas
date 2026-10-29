#!/bin/bash
# DIE-KV-16: V-D-H check on bind5 (PASS) and the mutant bind5m (FAIL on one member), then KV constants + image assets.
set -u
W=/srv/opentallas-scratch2/claude/wt/die-kv-16; R=/srv/opentallas-scratch2/claude/die-kv-16-1028
cd $W
python3 physical/die_plan/qwen_kvsys/r8/kv_pv_v_pads.py check $R/bind5 --json $R/vdh_bind5.json; echo VDH_BIND5_RC=$?
python3 results/die_kv_15_1028/v_offset_check.py $R/bind5 --json $R/v_offset_bind5.json | head -3; echo VOFF_BIND5_RC=$?
[ -d $R/bind5m ] && { python3 physical/die_plan/qwen_kvsys/r8/kv_pv_v_pads.py check $R/bind5m --json $R/vdh_bind5m.json; echo VDH_BIND5M_RC=$?; }
OUT=$R/img5 KV_BIND=$R/bind5 QC_BIND=/srv/opentallas-scratch2/claude/die-kv-13-1028/qc_fresh_v3 QC_SRC=${QC_SRC:-$W} \
  bash results/kv_native_image_13/run_constants2.sh
OUT=$R/img5 python3 results/kv_native_image_13/emit_assets.py; echo EMIT_RC=$?
grep -c "^\[OK" $R/img5/kv_constants2.log; grep -v "^\[OK" $R/img5/kv_constants2.log | head
