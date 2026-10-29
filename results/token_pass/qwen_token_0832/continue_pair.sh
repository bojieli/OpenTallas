#!/bin/bash
# Run on intel2. Continue exactly the existing repaired native vehicle after a
# genuinely successful first-layer proof. No source rebuild or nominal tie-offs.
set -euo pipefail
T=/srv/opentallas-scratch2/claude/codex-qwen-token-0832
W=/srv/opentallas-scratch2/claude/wt/codex-qwen-token-0832
P=/srv/opentallas-scratch2/claude/tok-qwen-7-1029/kvl/lr_nominal
mkdir -p "$T"
exec 9>"$T/continuation.lock"
flock -n 9 || exit 0
if [ -f "$T/continuation_launched" ];then exit 0;fi
while :;do
 status=$(ssh -o ControlPath=none intel1 python3 - "$P" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);t=(p/'sim.log').read_text(errors='replace')
if re.search(r'^KVSLICE_BOOT FAIL|^FAR_FAULT|^FAR_RESULT_MISMATCH',t,re.M):print('FAIL')
elif re.search(r'^KVSLICE_BOOT PASS',t,re.M) and re.search(r'^FAR_CAL ',t,re.M) and re.search(r'^FAR_LAYER layer 0 cal_start [0-9]+ result_first [0-9]+ result_last [0-9]+ ok 32 bad 0 ',t,re.M):print('READY')
elif (p/'exit').exists():print('ENDED_WITHOUT_POSITIVE')
else:print('WAIT')
PY
 )
 printf '%s %s\n' "$(date -Is)" "$status" >> "$T/continuation.log"
 case "$status" in READY)break;;FAIL|ENDED_WITHOUT_POSITIVE)exit 1;;WAIT)sleep 60;;*)exit 2;;esac
done
# Paths remain on intel1; --dir admits only where the exact source exists.
# Keep the proof vehicle immutable. Both runs use its existing generated map,
# exact DCAL ROM and real-history vectors, plus the corrected control classifier.
run(){
 local name=$1 post=$2 mut=$3
 ~/.local/bin/ot-run --mem 10 --threads 1 --dir "$W" -- bash -c '
  set -euo pipefail
  W=$1;T=$2;name=$3;post=$4;mut=$5
  B=/srv/opentallas-scratch2/claude/tok-qwen-7-1029/native_b5_lr/obj/Vtb_kvslice
  export IMG=/srv/opentallas-scratch2/claude/tok-kv-1-1028/vimg5
  export PHY_MAP=/srv/opentallas-scratch2/claude/tok-qwen-7-1029/native_b5_lr/phy_slice_map.json
  export KV_DCAL_VIAMAP=/srv/opentallas-scratch2/claude/die-kv-18-1028/dcal/p86/kv_dcal_r0_c0.viamap.hex
  export CTX=8192 POST=$post
  if [ "$mut" = 1 ];then export MUT_KSWAP=phy_WS_0;fi
  exec bash "$W/tools/qwen_layerbench/kv_dieslice/run_kvl.sh" "$B" /srv/opentallas-scratch2/claude/tok-kv-2-1028/vec "$T/kvl" "$name" d0_g0
 ' _ "$W" "$T" "$name" "$post" "$mut" > "$T/$name.otrun.log" 2>&1
}
date -Is > "$T/continuation_launched"
run nominal 300000 0 & n=$!
run m3_kswap 40000 1 & m=$!
printf '%s nominal_client %s m3_client %s\n' "$(date -Is)" "$n" "$m" >> "$T/continuation.log"
set +e
wait "$n";nr=$?
wait "$m";mr=$?
printf 'nominal %s m3_kswap %s\n' "$nr" "$mr" > "$T/continuation_exit"
test "$nr" = 0 && test "$mr" = 0
