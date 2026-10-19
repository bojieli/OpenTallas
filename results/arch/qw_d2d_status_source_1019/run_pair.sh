#!/bin/bash
set -euo pipefail
R=$(pwd)
export JOBS=4
export XQ_PLAN="2,2,2,3,2,2/11,11,9,9,9,9,9"
pids=()
XQ_G=-GC_OVL=3 XQ_GEN_TXDP='8,3,1,10/21,4,3,3' bash rtl/test/qwen_split/run_xdie_exchange_sf6s.sh "$R/functional/pair_ready" pair_gen_txdp > functional/pair_ready.summary 2>&1 &
pids+=("$!")
XQ_G='-GC_OVL=3 -GC_SFMUT=1' XQ_GEN_TXDP='8,3,1,10/21,4,3,3' XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange_sf6s.sh "$R/functional/pair_mut_bypass" pair_gen_txdp > functional/pair_mut_bypass.summary 2>&1 &
pids+=("$!")
XQ_G='-GC_OVL=3' XQ_GEN_TXDP='9,3,1,10/21,4,3,3' XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange_sf6s.sh "$R/functional/pair_mut_c0late" pair_gen_txdp > functional/pair_mut_c0late.summary 2>&1 &
pids+=("$!")
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
cat functional/pair*.summary
exit "$rc"
