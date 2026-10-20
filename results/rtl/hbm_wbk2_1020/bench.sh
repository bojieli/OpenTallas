#!/bin/bash
# HBM-WBK2 10-20: wbq benches + mutants on Verilator 5.050 (fleet via ot-run, unpinned among hosts holding the inputs)
# usage: bench.sh <tag> <cases...>
set -u
W=${SRCW:-/home/ubuntu/wt/hbm-wbk2-1020}; R=/srv/opentallas-scratch/claude/hbm-wbk2; L=/home/ubuntu/scratch/hbm-wbk2
TAG=$1; shift; CASES="$*"
HOSTS="ot-epyc5 ot-epyc9"
for H in $HOSTS; do
 ssh $H "rm -rf $R/src-$TAG $R/out-$TAG; mkdir -p $R/src-$TAG $R/out-$TAG" || continue
 for d in rtl/hbm_accel rtl/lib rtl/link rtl/model_ready_hbm_r14 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2 results/rtl/rbh_stk_1018/ref; do
  ssh $H "mkdir -p $R/src-$TAG/$d"; rsync -a $W/$d/ $H:$R/src-$TAG/$d/; done
 (git -C $W rev-parse HEAD 2>/dev/null; git -C $W status --porcelain -- rtl 2>/dev/null; echo $W) | ssh $H "cat > $R/src-$TAG/SOURCE_COMMIT"
done
N=$(echo $CASES | wc -w)
/home/ubuntu/bin/ot-run --mem $((6*N+8)) --threads $((4*N)) --dir $R/src-$TAG -- bash -c "cd $R/src-$TAG && H=\$(hostname); echo host=\$H; for c in $CASES; do (JOBS=4 bash rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh $R/out-$TAG/\$c \$c > $R/out-$TAG/\$c.stdout 2>&1; echo rc=\$? >> $R/out-$TAG/\$c.stdout) & done; wait; grep -H -E 'STK_|rc=|WB_BLOCK|PASS|FAIL|Fatal|Error' $R/out-$TAG/*.stdout | head -200" > $L/bench-$TAG.out 2>&1
echo "BENCH_RC=$?" >> $L/bench-$TAG.out
H=$(sed -n 's/^host=//p' $L/bench-$TAG.out | head -1)
[ -n "$H" ] && rsync -a --include='*/' --include='*.log' --include='*.stdout' --include='source.sha256' --include='build-*.log' --exclude='*' $H:$R/out-$TAG/ $L/out-$TAG/
