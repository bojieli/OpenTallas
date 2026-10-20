#!/bin/bash
set -eu
V=/opt/verilator-5.050/bin/verilator;[ -x "$V" ] || V=$(command -v verilator)
"$V" --version
src=rtl/test/host_peer_main_fixture_1020/historical/rtl/qwen_sys/host_cluster_20261017/peer_pd/qkd_host_ctrl_token_service_packet_collected_pd2.sv
queue=rtl/test/host_peer_main_fixture_1020/historical/rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_sram_head.sv
macro=physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v
for case in ${RX_CASES:-head sram flag_mut bypass_mut};do
 flags=(-DOT_PEER_CMD_TOKEN);[ "$case" != sram ] || flags+=(-DOT_PEER_RX_SRAM);[ "$case" != flag_mut ] || flags+=(-DOT_PEER_RX_FLAG_MUT);[ "$case" != bypass_mut ] || flags+=(-DOT_PEER_RX_SRAM -DOT_PEER_MUT_BYPASS)
 "$V" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -j 4 --top-module tb_rx --Mdir "obj_rx_$case" "${flags[@]}" "$src" "$queue" "$macro" rtl/test/host_peer_main_fixture_1020/mechanism/tb_rx.sv > "build_rx_$case.log" 2>&1
 set +e;"obj_rx_$case/Vtb_rx" +verilator+seed+27 +verilator+rand+reset+2 > "run_rx_$case.log" 2>&1;rc=$?;set -e
 cat "run_rx_$case.log"
 if [ "$case" = head ] || [ "$case" = sram ];then [ "$rc" = 0 ];else [ "$rc" != 0 ];grep -q 'RX_HEAD FAIL' "run_rx_$case.log";fi
 done
