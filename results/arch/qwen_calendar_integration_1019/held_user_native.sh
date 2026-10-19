#!/bin/bash
set -euo pipefail
cd run
s=../src
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 4 -Wno-fatal --top-module tb_programme_held_user_join -Mdir held_user_obj "$s/rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv" "$s/rtl/qwen_dv/qfd_dv_stream.sv" "$s/rtl/qwen_dv/qfd_dv_held_user_xbase.sv" "$s/rtl/test/mu_qwen_seq/tb_programme_held_user_join.sv" > held_user_build.log 2>&1
for m in 0 1 2 3 4 5 6 7 8 9 10;do
 set +e
 held_user_obj/Vtb_programme_held_user_join "+INPUT=$PWD/programme_join/x_events.txt" "+MUT=$m" > "held_user_m$m.log" 2>&1
 rc=$?
 set -e
 if [ "$m" = 0 ];then test "$rc" = 0;grep PROGRAMME_HELD_USER_JOIN_PASS "held_user_m$m.log"
 else test "$rc" != 0;grep PROGRAMME_HELD_USER_JOIN_FAIL "held_user_m$m.log";fi
done
