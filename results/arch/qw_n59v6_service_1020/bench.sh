#!/bin/bash
set -uo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
unit=$1;run=$2;mkdir -p "$run"
export VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
export N59_RECV=1 N59_RECV_MUT=0 N59_QB_ALIGN=1 N59_QB_LOCAL32=1 N59_QB_LOCAL_MUT=0 N59_SVC_LOCAL32=1 N59_SVC_LOCAL_MUT=0
export SPL_SOFF=3 SPL_BOFF=0 SPL_ROFF=4 SPLIT_ONLY=rnd_s1
case "$unit" in
 default_rnd) N59_SVC_LOCAL32=0;;
 local_rnd) :;;
 local_reset8) SPLIT_ONLY=rnd_reset8;;
 local_mu) SPLIT_ONLY=mu_ovl_positive;;
 local_dv) SPLIT_ONLY=dv_positive;;
 component)
  for m in 0 1 2;do
   "$VERILATOR" --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_kvn_local -GMUT=$m -Mdir "$run/component$m.obj" "$root/rtl/qwen_split/qfd_kvn_static_transport.sv" "$root/results/arch/qw_n59v6_service_1020/tb_kvn_local.sv" > "$run/component$m.build.log" 2>&1 || exit 2
   "$run/component$m.obj/Vtb_kvn_local" > "$run/component$m.log" 2>&1 || exit 3
  done
  grep -q '^KVN_LOCAL_PASS' "$run/component0.log" && grep -q '^KVN_LOCAL_MUTANT_REJECTED' "$run/component1.log" && grep -q '^KVN_LOCAL_MUTANT_REJECTED' "$run/component2.log" || exit 4
  echo N59SVC_COMPONENT_PASS;exit 0;;
 *) exit 2;;
esac
bash "$root/rtl/test/qwen_split/run_native59_split_bench.sh" "$run" > "$run/wrapper.log" 2>&1
rc=$?
test "$rc" = 0 || { echo "N59SVC_FAIL $unit rc=$rc";exit 1; }
echo "N59SVC_PASS $unit"
