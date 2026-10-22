#!/bin/bash
set -eu
V=/opt/verilator-5.050/bin/verilator
[ -x "$V" ] || V=$(command -v verilator)
"$V" --version
for case in ${PEER_CASES:-baseline exact bypass addr choice mailhold};do
 flags=();[ "$case" != baseline ] || flags=(-DOT_PEER_BASELINE);[ "$case" != mailhold ] || flags=(-DOT_PEER_MUT_MAILHOLD);[ "$case" != choice ] || flags=(-DOT_PEER_MUT_CHOICE);[ "$case" != bypass ] || flags=(-DOT_PEER_MUT_BYPASS);[ "$case" != addr ] || flags=(-DOT_PEER_MUT_ADDR)
 "$V" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -j 4 --top-module tb --Mdir "obj_$case" "${flags[@]}" rtl/test/host_peer_main_fixture_1020/mechanism/{original,tb}.sv rtl/test/host_peer_main_fixture_1020/historical/rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_link.sv rtl/test/host_peer_main_fixture_1020/historical/rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_sram_head.sv physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v > "build_$case.log" 2>&1
 set +e;"obj_$case/Vtb" +verilator+seed+17 +verilator+rand+reset+2 > "run_$case.log" 2>&1;rc=$?;set -e
 cat "run_$case.log"
 if [ "$case" = exact ] || [ "$case" = baseline ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];grep -q 'FAIL cycle=' "run_$case.log";fi
 done
