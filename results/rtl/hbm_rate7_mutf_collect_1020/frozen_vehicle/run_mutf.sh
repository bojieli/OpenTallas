#!/usr/bin/env bash
# HBM-COLLFUSE2: causal MUT_FORCE witnesses for the TP-8 qw8_* SU records (tb +MUT_FORCE: lane 0 of VM read 0 := +0x7f000000)
cd "$(dirname "$0")" || exit 9
JOBS=6 bash run_toksim_su.sh build mr10 > build.summary 2>&1 || { echo BUILD_FAIL; exit 2; }
mkdir -p out
for r in qw8_softmax_max qw8_bf16_p qw8_pv_normalize qw8_round_q qw8_row_scale_qkv; do
 ( TAG=_POS bash run_toksim_su.sh run mr10 vec_tp8/$r > out/${r}_POS.summary 2>&1
   TAG=_MUT_FORCE bash run_toksim_su.sh run mr10 vec_tp8/$r +MUT_FORCE > out/${r}_MUT_FORCE.summary 2>&1 ) &
done; wait
for r in qw8_softmax_max qw8_bf16_p qw8_pv_normalize qw8_round_q qw8_row_scale_qkv; do
 p=$(grep -c "SU_TOP PASS" vec_tp8/$r/sim_mr10_POS.log); m=$(grep -c "SU_TOP FAIL" vec_tp8/$r/sim_mr10_MUT_FORCE.log)
 echo "$r POS_PASS=$p MUT_FORCE_FAIL=$m"
done > out/verdict.txt
echo ALLDONE > out/done.txt
