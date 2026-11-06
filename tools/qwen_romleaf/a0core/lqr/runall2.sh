#!/bin/bash
# QC-A0C-B5 vB2 proof set (lqr_patch.py + lqr2_patch.py).  usage: runall2.sh NL_OLD NL_NEW NK_OLD NK_NEW OUTDIR (repo root)
#   Must PASS: nl LQR 25 (1+8+16) and nk LQR 31 (7+8+16) with a fault pulse injected in both sides at FINJ ns, data
#   shifted by the vB pin cycles and the fault bit by exactly +1; nl/nk LQR 0 vs the original rtl (default-off).
#   Must FAIL: mutants 4 (slice 2 fault stage drops faults), 5 (two fault stages), 6 (south reset relay never released).
set -uo pipefail
NLO=$1; NLN=$2; NKO=$3; NKN=$4; O=$(mkdir -p "$5" && realpath "$5"); D=tools/qwen_romleaf/a0core/lqr
FI=${FINJ_NS:-1650.2}
cases=("nl $NLN l25 25 0" "nl $NLN l25_m4 25 4" "nl $NLN l25_m5 25 5" "nl $NLN l25_m6 25 6"
       "nk $NKN l31 31 0" "nk $NKN l31_m4 31 4" "nk $NKN l31_m5 31 5" "nk $NKN l31_m6 31 6")
J=${PAR:-5}
for c in "${cases[@]}"; do set -- $c
  while [ $(jobs -r | wc -l) -ge $J ]; do sleep 5; done
  FSHIFT=1 FINJ=$FI bash $D/build.sh $1 $2 $O/$1_$3 $4 $5 8 > $O/$1_$3.build.out 2>&1 &
done
while [ $(jobs -r | wc -l) -ge $J ]; do sleep 5; done
OLD=$NLO bash $D/build.sh nl $NLN $O/nl_old0 0 0 8 > $O/nl_old0.build.out 2>&1 &
OLD=$NKO bash $D/build.sh nk $NKN $O/nk_old0 0 0 8 > $O/nk_old0.build.out 2>&1 &
wait
for d in $O/*/; do [ -x $d/obj/Vtb_a0_lqr ] || { echo "$(basename $d): BUILD FAILED"; continue; }
  (cd $d && ./obj/Vtb_a0_lqr +OT_ROM_DIR=$d/rom > run.log 2>&1)
  echo "$(basename $d): $(grep -h '^A0LQR_\(PASS\|FAIL\)' $d/run.log) | $(grep -h '^A0LQR_FAULT' $d/run.log)"; rm -rf $d/obj; done
