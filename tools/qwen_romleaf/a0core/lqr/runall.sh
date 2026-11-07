#!/bin/bash
# QC-A0C-B5 vB LQR proof set.  usage: runall.sh NL_KIT_RTL_OLD NL_KIT_RTL_NEW NK_KIT_RTL_OLD NK_KIT_RTL_NEW OUTDIR  (repo root)
#   *_NEW = the kit rtl after lqr_patch.py.  Must PASS: nl LQR 1 (+1 t_out cycle), nk LQR 7 (+3), nl/nk LQR 0 vs the
#   original rtl (OLD, 0 cycles).  Must FAIL: mutants 1 (no RX+1), 2 (RX+2), 3 (bank 0 col 1 not registered) on both.
set -uo pipefail
NLO=$1; NLN=$2; NKO=$3; NKN=$4; O=$(mkdir -p "$5" && realpath "$5"); D=tools/qwen_romleaf/a0core/lqr
cases=("nl $NLN l1 1 0" "nl $NLN l1_m1 1 1" "nl $NLN l1_m2 1 2" "nl $NLN l1_m3 1 3" "nk $NKN l7 7 0" "nk $NKN l7_m1 7 1"
       "nk $NKN l7_m2 7 2" "nk $NKN l7_m3 7 3")
for c in "${cases[@]}"; do set -- $c; bash $D/build.sh $1 $2 $O/$1_$3 $4 $5 8 > $O/$1_$3.build.out 2>&1 & done
OLD=$NLO bash $D/build.sh nl $NLN $O/nl_old0 0 0 8 > $O/nl_old0.build.out 2>&1 &
OLD=$NKO bash $D/build.sh nk $NKN $O/nk_old0 0 0 8 > $O/nk_old0.build.out 2>&1 &
wait
for d in $O/*/; do [ -x $d/obj/Vtb_a0_lqr ] || { echo "$(basename $d): BUILD FAILED"; continue; }
  (cd $d && ./obj/Vtb_a0_lqr +OT_ROM_DIR=$d/rom > run.log 2>&1); echo "$(basename $d): $(grep -h '^A0LQR_\(PASS\|FAIL\)' $d/run.log)"; done
