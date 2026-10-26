#!/bin/bash
# QC-TOK 2026-10-25: re-run the two lm cases (fail1 = harness: lower_lm read the absent 10-18 slice_ages default) with the
# vehicle slice ages (die/build/slice_ages.json = s8exp_wf3 calibration of this same obj_n12; equal to slice_calibrate.out),
# then re-summarise stgdie/result.json with the stage script's own summary (fail1 outputs kept in runs/<case>.fail1).
set -u
E=$(cd "$(dirname "$0")" && pwd); T=$E/tree; W=$E/die; S=$E/stgdie
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH DV2_S8DIE=1 PYTHONDONTWRITEBYTECODE=1
cd $T
cp $S/result.json $S/result.fail1.json; cp $S/runs.log $S/runs.fail1.log
for name in lm LGPOS_lm_arf; do
  [ -d $S/runs/$name.fail1 ] || mv $S/runs/$name $S/runs/$name.fail1
  line=$(grep "^die $name " $S/runlist.txt | cut -d" " -f3-)
  d=$S/runs/$name; mkdir -p $d; ln -sfn $W/build/obj_n12 $d/obj_n12
  DV_LOWER_VFLAGS="$(cat $W/vflags.txt)" python3 $line --slice-ages $W/build/slice_ages.json --work $d > $d/bench.out 2>&1; echo "rc=$?" >> $d/bench.out
  echo "die $name $(head -1 $d/bench.out | cut -c1-160)" | tee -a $S/runs.log
done
sed -n "/^python3 - \"\$S\" \"\$STG\" <<.PY./,/^PY$/p" $T/tools/qwen_tokfunc/stage_stg_die.sh | sed "1d;\$d" > $S/summary.py
python3 $S/summary.py $S $E/stg_result.json
