#!/bin/bash
set -u
rc=0
for pair in 24:23 40:39; do
 export GATHER_PERIOD=${pair%:*} GATHER_RESPONSE=${pair#*:}
 for m in 0 1; do
  out="$PWD/out_p${GATHER_PERIOD}_m${m}"
  bash rtl/hbm_accel/generic/peers/static_hc/run_gather_f32.sh "$out" "$m" > "$PWD/summary_p${GATHER_PERIOD}_m${m}.log" 2>&1
  child_rc=$?
  cat "$PWD/summary_p${GATHER_PERIOD}_m${m}.log"
  if [ "$m" = 0 ]; then
   grep -q 'GATHER_F32 PASS MUT=0' "$out/run.log" || rc=1
  else
   grep -q 'GATHER_F32 FAIL MUT=1' "$out/run.log" || rc=1
  fi
  echo "READER_CASE period=$GATHER_PERIOD response=$GATHER_RESPONSE mutant=$m child_rc=$child_rc"
 done
done
echo "READER_SOURCE_WITNESS_FINAL rc=$rc"
exit "$rc"
