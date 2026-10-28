#!/bin/bash
# TOK-ALL-17: REAL ot_s81hd_ctl_core latency probes (same file set as tools/s81_head/head_ctl_bench.sh)
set -e
T=/srv/opentallas-scratch2/claude/tok17-head; R=/srv/opentallas-scratch2/claude/wt/claude-tok17-head
O=$T/ctl/o; rm -rf $O; mkdir -p $O; S=rtl/dsrom_sys/s81_head
for n in ctl_core ctl_hsf0_static static_issue util beat_link host276 best64 mesh_ep_core ar_control_hsf0 rank_merge_hsf0 result_landing_hsf0 fault_state_hsf0;do cp $R/$S/ot_s81hd_$n.sv $O/;done
cp $R/rtl/dsrom_sys/mtp/{dsfd_mtp_tops,ot_dsrom_mtp_link_pair,ot_dsrom_mtp_seq}.sv $R/rtl/lib/ot_rst_relay_tree3.sv $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v $T/ctl/tb_tok17_ctl_lat.sv $O/
cd $O; V=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --binary --timing --build-jobs 4 -O1 -Wno-fatal --top-module tb_tok17_ctl_lat -Mdir obj *.sv *.v > build.log 2>&1
obj/Vtb_tok17_ctl_lat > run_shuf.log 2>&1 || true
obj/Vtb_tok17_ctl_lat +B2B > run_b2b.log 2>&1 || true
grep -h "LAT\|PASS\|FAIL\|RESULT_EDGE\|Fatal" run_shuf.log run_b2b.log
