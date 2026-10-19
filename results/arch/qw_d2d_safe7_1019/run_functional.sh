#!/bin/bash
# QW-D2D3 SF7 functional campaign (Verilator 5.050): 200k lockstep vs qfd_d2d_static_ovl (m0 PASS, m1..m5 negative
# controls FAIL) + 35-layer compute<->KV pair on the compiled seam / TXDP (PASS) and two pair negatives (FAIL).
set -euo pipefail
R=$(pwd)
mkdir -p functional
export JOBS=4
export XQ_PLAN="2,2,2,3,2,2/11,11,9,9,9,9,9"
pids=()
for m in 0 1 2 3 4 5; do
 bash rtl/test/qwen_split/run_qfd_d2d_sf7_equiv.sh "$R/functional/lockstep_m$m" "$m" 200000 > "functional/lockstep_m$m.summary" 2>&1 &
 pids+=("$!")
done
XQ_G=-GC_OVL=3 XQ_GEN_TXDP='8,3,1,10/21,4,3,3' bash rtl/test/qwen_split/run_xdie_exchange_sf7.sh "$R/functional/pair_ready" pair_gen_txdp > functional/pair_ready.summary 2>&1 &
pids+=("$!")
XQ_G='-GC_OVL=3 -GC_SFMUT=1' XQ_GEN_TXDP='8,3,1,10/21,4,3,3' XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange_sf7.sh "$R/functional/pair_mut_bypass" pair_gen_txdp > functional/pair_mut_bypass.summary 2>&1 &
pids+=("$!")
XQ_G='-GC_OVL=3' XQ_GEN_TXDP='9,3,1,10/21,4,3,3' XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange_sf7.sh "$R/functional/pair_mut_c0late" pair_gen_txdp > functional/pair_mut_c0late.summary 2>&1 &
pids+=("$!")
XQ_G='-GC_OVL=3 -GC_SFMUT=4' XQ_GEN_TXDP='8,3,1,10/21,4,3,3' XQ_GEN_TXDP_EXPECT=FAIL bash rtl/test/qwen_split/run_xdie_exchange_sf7.sh "$R/functional/pair_mut_ohtwin" pair_gen_txdp > functional/pair_mut_ohtwin.summary 2>&1 &
pids+=("$!")
rc=0
for p in "${pids[@]}"; do wait "$p" || rc=1; done
cat functional/*.summary
grep -qx 'sfeq_m0 got=PASS' functional/lockstep_m0.summary || rc=1
for m in 1 2 3 4 5; do grep -qx "sfeq_m$m got=FAIL" "functional/lockstep_m$m.summary" || rc=1; done
for p in pair_ready pair_mut_bypass pair_mut_c0late pair_mut_ohtwin; do
 grep -q -- '-> OK' "functional/$p.summary" || rc=1
 if grep -q UNEXPECTED "functional/$p.summary"; then rc=1; fi
done
echo "SF7_FUNCTIONAL rc=$rc"
exit "$rc"
