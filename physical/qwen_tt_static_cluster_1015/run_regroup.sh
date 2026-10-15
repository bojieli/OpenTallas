#!/bin/bash
# usage: run_regroup.sh MUT NCYC   (MUT=1 swaps two tree-return bits, MUT=2 two tree-command bits in the dut)
set -e
MUT=${1:-0}; N=${2:-100000}; P=physical/qwen_tt_static_cluster_1015
NEW=rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_parent.sv
case $MUT in
 1) sed 's/\.rom_ret_i(rom_ret),/.rom_ret_i({rom_ret[94:2],rom_ret[0],rom_ret[1]}),/' $NEW > /tmp/rg_m$$.sv; NEW=/tmp/rg_m$$.sv;;
 2) sed 's/\.cmd(rom_cmd),\.ret(rom_ret));/.cmd({rom_cmd[379:2],rom_cmd[0],rom_cmd[1]}),.ret(rom_ret));/' $NEW > /tmp/rg_m$$.sv; NEW=/tmp/rg_m$$.sv;;
esac
grep -q "rom_ret\[0\],rom_ret\[1\]\|rom_cmd\[0\],rom_cmd\[1\]" $NEW || [ $MUT = 0 ] || { echo "mutant not applied"; exit 9; }
SR=$(sed 's#_bb\.v#.v#g' $P/srcs.txt)
O=/tmp/rg_obj_$MUT_$$
verilator --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -DNCYC=$N --top-module tb_tt_static_regroup -Mdir $O \
  $SR rtl/qwen_sys/static_schedule_20261014/ot_qfd_tt_ctlm_static_hr.sv $NEW $P/ot_qfd_tt_ctlm_static_parent_ref.sv $P/tb_tt_static_regroup.sv > /tmp/rg_build_$MUT.log 2>&1 || { tail -20 /tmp/rg_build_$MUT.log; exit 2; }
$O/Vtb_tt_static_regroup | tail -12
