#!/bin/bash
# TOK-QK 10-24: s8cal2 binary reused; calibrates re-run after the tree symlinks (to intel1 paths) were replaced by real
# files from main 8a5d1f3dab; then the stg pos family on the bound s8 row (stage_stg_die.sh).
E=/srv/opentallas-scratch2/claude/tok-qw/s8exp; T=$E/tree; W=$E/die
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
t0=$(date +%s); cd $T
export DV2_S8DIE=1 DV_LOWER_VFLAGS="$(cat $W/vflags.txt)"
python3 rtl/test/qwen_dv/dv_lower_bench.py --work $W/build --calibrate > $W/build/slice_calibrate.out 2>&1; echo "rc=$?" >> $W/build/slice_calibrate.out
echo "slicecal3 $(( $(date +%s)-t0 ))" >> $W/timing.txt
python3 rtl/test/qwen_dv/dv_lower_vec_bench.py --work $W/build --mode calibrate > $W/build/calibrate.out 2>&1; echo "rc=$?" >> $W/build/calibrate.out
echo "veccal3 $(( $(date +%s)-t0 ))" >> $W/timing.txt
grep -q "^rc=0" $W/build/slice_calibrate.out && grep -q "^rc=0" $W/build/calibrate.out || { echo "CAL FAIL"; tail -5 $W/build/slice_calibrate.out $W/build/calibrate.out; exit 6; }
bash $E/stage_stg_die.sh $E $E/stg_result.json $E/pos_runlist.txt --par 24
