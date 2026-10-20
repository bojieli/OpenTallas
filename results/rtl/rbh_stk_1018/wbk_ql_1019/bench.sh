#!/bin/bash
# L2H-WBK 10-19: wbq benches + 4 mutants + wb_default on Verilator 5.050 (fleet, ot-epyc5) for the per-domain reset landing RTL
W=/home/ubuntu/wt/hbm-wbk-1018; H=ot-epyc5; R=/srv/opentallas-scratch/claude/l2h-wbk; L=/home/ubuntu/scratch/l2h-wbk
ssh $H "rm -rf $R/src $R/out; mkdir -p $R/src $R/out"
for d in rtl/hbm_accel rtl/lib rtl/model_ready_hbm_r14 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2 results/rtl/rbh_stk_1018/ref; do
 ssh $H "mkdir -p $R/src/$d"; rsync -a $W/$d/ $H:$R/src/$d/; done
git -C $W rev-parse HEAD | ssh $H "cat > $R/src/SOURCE_COMMIT"
CASES="wbq_e wbq_w wbq_e_wopen wbq_mut_quad wbq_mut_span wbq_mut_premature wbq_mut_ksaddr wb_default"
/home/ubuntu/bin/ot-run --mem 48 --threads 64 --dir $R --hosts $H -- bash -c "cd $R/src && for c in $CASES; do (JOBS=8 bash rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh $R/out/\$c \$c > $R/out/\$c.stdout 2>&1; echo rc=\$? >> $R/out/\$c.stdout) & done; wait; grep -H -E 'STK_|rc=' $R/out/*.stdout"  > $L/bench.out 2>&1
echo "BENCH_RC=$?" >> $L/bench.out
rsync -a --include='*/' --include='*.log' --include='*.stdout' --include='source.sha256' --exclude='build-*' --exclude='*' $H:$R/out/ $L/out/
