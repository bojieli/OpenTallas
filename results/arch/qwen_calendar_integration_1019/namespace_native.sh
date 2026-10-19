#!/bin/bash
set -euo pipefail
cd run
s=../src
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 4 -Wno-fatal  --top-module tb_programme_namespace_join -Mdir namespace_obj  "$s/rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv" "$s/rtl/qwen_dv/qfd_dv_stream.sv"  "$s/rtl/test/mu_qwen_seq/tb_programme_namespace_join.sv" > namespace_build.log 2>&1
for m in 0 1 2 3 4;do
 set +e
 namespace_obj/Vtb_programme_namespace_join "+INPUT=$PWD/programme_join/x_events.txt" "+MUT=$m" > "namespace_m$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep PROGRAMME_NAMESPACE_JOIN_PASS "namespace_m$m.log"
 else test "$rc" != 0;grep PROGRAMME_NAMESPACE_JOIN_FAIL "namespace_m$m.log";fi
done
