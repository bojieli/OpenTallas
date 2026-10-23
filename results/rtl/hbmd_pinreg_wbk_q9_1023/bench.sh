#!/bin/bash
# STEWARD-HBMd/PINREG q9 2026-10-23 (from HBM-WBK8 bench.sh): KPREG lockstep + wbq benches / mutants on Verilator 5.050,
# fleet via ot-run (inputs rsynced to the named hosts first; ot-run picks among them by memory).
# usage: bench.sh <tag> <mem_per_case_GB> <cases...>
set -u
W=${SRCW:-/home/ubuntu/wt/hbmd-pinreg-wbk-q9}; R=/srv/opentallas-scratch/claude/hbmd-pinreg-wbk-q9/bench; L=/home/ubuntu/scratch/hbmd-pinreg/bench
TAG=$1; MPC=$2; shift 2; CASES="$*"
HOSTS=${HOSTS:-"ot-gold1 ot-epyc7"}
mkdir -p $L
for H in $HOSTS; do
 ssh -o ControlPath=none $H "rm -rf $R/src-$TAG $R/out-$TAG; mkdir -p $R/src-$TAG $R/out-$TAG" || continue
 for d in rtl/hbm_accel rtl/lib rtl/link rtl/model_ready_hbm_r14 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2 results/rtl/rbh_stk_1018/ref; do
  ssh -o ControlPath=none $H "mkdir -p $R/src-$TAG/$d"; rsync -a -e 'ssh -o ControlPath=none' $W/$d/ $H:$R/src-$TAG/$d/; done
 (git -C $W rev-parse HEAD 2>/dev/null; git -C $W status --porcelain -- rtl 2>/dev/null; echo $W) | ssh -o ControlPath=none $H "cat > $R/src-$TAG/SOURCE_COMMIT"
done
N=$(echo $CASES | wc -w)
/home/ubuntu/bin/ot-run --mem $((MPC*N+8)) --threads $((4*N)) --dir $R/src-$TAG --hosts $(echo $HOSTS | tr ' ' ,) -- bash -c "cd $R/src-$TAG && H=\$(hostname); echo host=\$H; for c in $CASES; do (JOBS=4 bash rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh $R/out-$TAG/\$c \$c > $R/out-$TAG/\$c.stdout 2>&1; echo rc=\$? >> $R/out-$TAG/\$c.stdout) & done; wait; grep -H -E 'STK_|rc=|PASS|FAIL|Fatal|Error' $R/out-$TAG/*.stdout | head -400" > $L/bench-$TAG.out 2>&1
echo "BENCH_RC=$?" >> $L/bench-$TAG.out
H=$(sed -n 's/^host=//p' $L/bench-$TAG.out | head -1)
[ -n "$H" ] && rsync -a -e 'ssh -o ControlPath=none' --include='*/' --include='*.log' --include='*.stdout' --include='source.sha256' --exclude='*' $H:$R/out-$TAG/ $L/out-$TAG/
