#!/bin/bash
# TYPE-SAFE-3 QC: event -> bind (for bus_groups) -> R8 re-derive -> strict bind -> miter
set -u
Q=/srv/opentallas-scratch3/claude/type-safe-3b/qc
cd $Q
mkdir -p old
stamp=$(date +%H%M%S)
[ -d bind_new ] && mv bind_new old/bind_new_$stamp
[ -f bind_new.log ] && mv bind_new.log old/bind_$stamp.log
sed -n '/^prlimit/,/cut -c1-500$/p' run.sh > /dev/null
rm -f plan/plan_qc53v4n_ts3.json
bash run.sh 2>&1 | sed -n '2,5p' | cut -c1-300
bash bind.sh > pass1.out 2>&1; echo PASS1 rc=$?
grep -c R8_STALE bind_new.log
bash r8.sh 2>&1 | grep -E "PADS rc|changed" | cut -c1-200
R=src/physical/die_plan/qwen_compute/qc_start_1106/runtime
rm -f $R/r8_ts3.json; cp r8/qwen_compute_r8_landing.json $R/r8_ts3.json
python3 -I r8cmp.py 2>&1 | cut -c1-900
mv bind_new old/bind_new_p1_$stamp; mv bind_new.log old/bind_p1_$stamp.log
bash bind.sh > pass2.out 2>&1; echo PASS2 rc=$?
tail -n 6 pass2.out | cut -c1-300
head -n 3 bind_new.log | cut -c1-300
ls -la miter.json | cut -c30-
python3 -I -c "
import json;print(open('$Q/miter.json').read()[:1500])"
