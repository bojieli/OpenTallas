#!/bin/bash
set -uo pipefail
cd /srv/opentallas-scratch/codex/own-idxscore/src4
out=/srv/opentallas-scratch/codex/own-idxscore/leaf_exact4
mkdir -p "$out"
rc=0
for mode in pos gap4 qlate1 seam swap; do
 bash rtl/test/hbm_idx_static/run_chunk_rt_equiv.sh "$out/$mode" "$mode" > "$out/$mode.log" 2>&1
 r=$?
 if [[ "$mode" = pos || "$mode" = gap4 ]]; then
  if [[ $r != 0 ]] || ! grep -q 'CHUNK_RT_EQUIV PASS' "$out/$mode.log"; then rc=1; fi
 else
  if [[ $r = 0 ]] || ! grep -q 'MISMATCH' "$out/$mode.log"; then rc=1; fi
 fi
 echo "LEAF_GATE_MODE $mode rc=$r cumulative=$rc"
 tail -9 "$out/$mode.log"
done
[[ $rc = 0 ]] && echo LEAF_EXACT_GATE_PASS || echo LEAF_EXACT_GATE_FAIL
exit "$rc"
