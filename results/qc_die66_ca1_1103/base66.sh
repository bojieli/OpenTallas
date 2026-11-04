#!/bin/bash
# DIE-QC-66/CLK: base-of-record strict bind + G0C base (base plan copied next to plan_qc52 so relative pins_file paths resolve)
set -u
W=$1; R=$2; cd $W
PB=physical/die_plan/qwen_compute/plan_of_record/.plan_qc52_ca1base.json; cp $R/plan_base.json $PB
S=$R/status; say(){ echo "$* $(date)" | tee -a $S; }
mkdir -p $R/b0 $R/g0c_base; for f in asbuilt.json asbuilt_sources.json; do cp $R/elab/$f $R/b0/$f; done
python3 -I tools/die_plan/bind.py bind $PB --asbuilt results/qc_die63_red_1102/bind/final_asbuilt.json --out $R/b0 --strict > $R/b0.log 2>&1; say "B0 BASE-OF-RECORD strict rc=$? $(grep -m1 '"errors"' $R/b0.log | cut -c1-300)"
python3 -I tools/die_plan/check.py $PB --out $R/g0c_base --completeness > $R/g0c_base/check.log 2>&1; say "G G0C base rc=$? $(grep -m1 'G0C FAIL\|G0C PASS' $R/g0c_base/check.log|cut -c1-200)"
rm -f $PB; say BASEDONE
