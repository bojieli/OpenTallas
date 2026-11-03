#!/bin/bash
# ONE corrected ready-wait full36 run. Existing NOWAIT A/B never modified.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
python3 "$D/runtime_guard.py"
[ -x "$D/b/obj/Vtb_kvslice" ]
[ ! -e "$D/runs/full_readywait" ] || { echo 'NOT RUN: sole run already exists'; exit 3; }
export IMG=/srv/opentallas-scratch2/claude/kv-fn-7/veh60/vimg
export KV_DCAL_VIAMAP=/srv/opentallas-scratch2/claude/kv-fn-7/veh60/dcal/kv_dcal_r0_c0.viamap.hex
export PHY_MAP="$D/b/phy_slice_map.json" POST=290867 CTX=8192
python3 "$D/observe_window.py" "$D/runs/full_readywait" --watch > "$D/window_observer.log" 2>&1 & observer=$!
# The observer creates the output folder; run_kvl may populate it normally.
set +e
bash /srv/opentallas-scratch2/claude/kv-fn-7/veh60/src_main/tools/qwen_layerbench/kv_dieslice/run_kvl.sh \
 "$D/b/obj/Vtb_kvslice" /srv/opentallas-scratch2/claude/kv-fn-7/vec "$D/runs" full_readywait d0_g0 \
 +HOST_TOKEN_TOK=1 +HOST_TOKEN_POS=8191 +HOST_TOKEN_GEN=1 +HOST_TOKEN_EPOCH=4 +HOST_TOKEN_SEPOCH=0
rc=$?
set -e
# Ensure observer terminates on every runner failure before a simulator exit file exists.
[ -f "$D/runs/full_readywait/exit" ] || printf '%s\n' "$rc" > "$D/runs/full_readywait/exit"
wait "$observer"
python3 "$D/qualify_run.py"
exit "$rc"
