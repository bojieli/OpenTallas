#!/bin/bash
# after DS1M: Qwen8K minimum parent (build-jobs 2: child verilations peak 78-148 GB each), then stop the memguard
D=/srv/opentallas-scratch/claude/tk-hbm-harvest/fsr
until [ -f $D/ds1m.done ]; do sleep 120; done
sed -i "s/--build-jobs 3/--build-jobs 2/" $D/qwen8k.sh
bash $D/qwen8k.sh > $D/qwen8k.log 2>&1
for t in lorentz-margin lorentz-margin-qwen8k; do for m in base wrong_release corrupt_gold; do
 f=$D/../$t/work/run_$m/run.log; [ -f $f ] && echo "$t $m rc=$(cat $D/../$t/work/run_$m/run.exit) $(grep -E 'PASS|FAIL|Fatal|mismatch|cycles' $f | tail -2 | tr '\n' ' ' | cut -c1-300)"
done; done > $D/summary.txt
touch $D/stop_guard
