#!/bin/bash
# SM-element attention bench r8 (H-SM 2026-10-15): QK calendar regenerated from the measured landings
# (qk_landing_calibration.json).  Positive: every op of ds640 (52) and ds128 (48) exact.  Negative controls (must FAIL):
# converter mutants KV MUT 1 (KV8 lane uses the wrong block scale) and MUT 2 (wrong beat), calendar mutants r7clear (the
# r7 clear law) and early (publication one cycle before the measured last landing).
# usage: run_elem_r8.sh SRC_DIR OUT_DIR
set -u
S=$1; O=$2; mkdir -p $O; cd $S
E="python3 tools/hbm_sm_attention/sm_elem_bench.py run"
$E --shape ds640 --ops all --work $O/w640 --out $O/ds640_all.json > $O/ds640_all.log 2>&1; echo "ds640_all rc=$?" >> $O/rc.log
$E --shape ds128 --ops all --work $O/w128 --out $O/ds128_all.json > $O/ds128_all.log 2>&1; echo "ds128_all rc=$?" >> $O/rc.log
for m in 1 2; do $E --shape ds640 --ops qk_sm0,pv_sm0 --dmut $m --work $O/wm --out $O/ds640_kv$m.json > $O/ds640_kv$m.log 2>&1; echo "ds640_kv$m rc=$?" >> $O/rc.log; done
for m in r7clear early; do $E --shape ds640 --ops qk_sm0 --smut $m --work $O/w640 --out $O/ds640_$m.json > $O/ds640_$m.log 2>&1; echo "ds640_$m rc=$?" >> $O/rc.log; done
echo DONE >> $O/rc.log
