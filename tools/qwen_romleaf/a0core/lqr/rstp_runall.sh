#!/bin/bash
# QC-NLNK-RF2 vR proof set.  usage: rstp_runall.sh NL_OLD NL_NEW NK_OLD NK_NEW OUTDIR  (repo root)
# Must PASS: nl/nk RSTP 3 vs RSTP 0 (t_out delta 0, fault bit shift 0, reset edges +3) and RSTP 0 vs the original rtl (default-off).
# Must FAIL: mutants 1-4 (rstp_patch.py).
set -uo pipefail
NLO=$1; NLN=$2; NKO=$3; NKN=$4; O=$(mkdir -p "$5" && realpath "$5"); D=tools/qwen_romleaf/a0core/lqr
J=${PAR:-5}
for t in nl nk; do
  [[ $t == nl ]] && N=$NLN || N=$NKN
  for m in 0 1 2 3 4; do
    while [ $(jobs -r | wc -l) -ge $J ]; do sleep 5; done
    bash $D/rstp_build.sh $t $N $O/${t}_r3_m$m 3 $m 8 > $O/${t}_r3_m$m.build.out 2>&1 &
  done
done
while [ $(jobs -r | wc -l) -ge $J ]; do sleep 5; done
OLD=$NLO bash $D/rstp_build.sh nl $NLN $O/nl_old0 0 0 8 > $O/nl_old0.build.out 2>&1 &
OLD=$NKO bash $D/rstp_build.sh nk $NKN $O/nk_old0 0 0 8 > $O/nk_old0.build.out 2>&1 &
wait
for d in $O/*/; do [ -x $d/obj/Vtb_a0_rstp ] || { echo "$(basename $d): BUILD FAILED"; continue; }
  (cd $d && ./obj/Vtb_a0_rstp +OT_ROM_DIR=$d/rom > run.log 2>&1)
  echo "$(basename $d): $(grep -h '^A0RSTP_\(PASS\|FAIL\)' $d/run.log) | $(grep -h '^A0RSTP_RESET' $d/run.log)"; rm -rf $d/obj; done
