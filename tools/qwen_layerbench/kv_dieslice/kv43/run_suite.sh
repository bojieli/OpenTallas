#!/bin/bash
# TOK-QK 10-24: KV die-slice verdict suite on one build (all in parallel): boot smoke nominal + frame mutant, token phase
# nominal + m1 (+MUT_CMD_LATE: compute far end one command late) + m2 (+MUT_RL24=phy_WS_0: HBM RL+1 on one slice)
# + m3 (preload K rows of phy_WS_0 swapped t<->t^1).  m4 (boot-image word) NOT RUN: needs the image encoder.
#   run_suite.sh BUILDDIR IMGDIR OUT [MUT_FRAME]     env POST (default 300000), CTX (256)
set -u
H=$(cd "$(dirname "$0")/.." && pwd); R=$(cd $H/../../.. && pwd)
B=$1; I=$2; O=$(mkdir -p $3 && readlink -f $3); MF=${4:-100}
V=$R/results/arch/qwen_tp8_native_dispatch_1014/checkpoint_service_vectors
bash $H/run.sh $B $I $O/boot $MF > $O/boot.out 2>&1 &
bash $H/run_tok.sh $B $I $O/tok nominal $V > $O/tok_nominal.out 2>&1 &
bash $H/run_tok.sh $B $I $O/tok m1 $V +MUT_CMD_LATE > $O/tok_m1.out 2>&1 &
bash $H/run_tok.sh $B $I $O/tok m2 $V +MUT_RL24=phy_WS_0 > $O/tok_m2.out 2>&1 &
PRELOAD_ARGS="--mut-kswap phy_WS_0" bash $H/run_tok.sh $B $I $O/tok m3 $V > $O/tok_m3.out 2>&1 &
wait
cat $O/boot.out $O/tok_*.out | tee $O/suite_summary.txt
