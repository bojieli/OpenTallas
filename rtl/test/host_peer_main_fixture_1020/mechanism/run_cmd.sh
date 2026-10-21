#!/bin/bash
set -eu
V=/opt/verilator-5.050/bin/verilator;[ -x "$V" ] || V=$(command -v verilator)
"$V" --version
src=rtl/test/host_peer_main_fixture_1020/historical/rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_ctrl_token_service_packet_collected_pd2.sv
for case in ${CMD_CASES:-exact exact_token mutant};do
 flags=();[ "$case" != exact_token ] || flags=(-DOT_PEER_CMD_TOKEN);[ "$case" != mutant ] || flags=(-DOT_PEER_CMD_READ_MUT)
 "$V" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -j 4 --top-module tb_cmd --Mdir "obj_cmd_$case" "${flags[@]}" "$src" rtl/test/host_peer_main_fixture_1020/mechanism/tb_cmd.sv > "build_cmd_$case.log" 2>&1
 set +e;"obj_cmd_$case/Vtb_cmd" +verilator+seed+27 +verilator+rand+reset+2 > "run_cmd_$case.log" 2>&1;rc=$?;set -e
 cat "run_cmd_$case.log"
 if [ "$case" = exact ] || [ "$case" = exact_token ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];grep -q 'CMD_READ32 FAIL' "run_cmd_$case.log";fi
 done
