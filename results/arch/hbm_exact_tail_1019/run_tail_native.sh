#!/bin/bash
set -euo pipefail
cd src
SRCS="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_cg.sv rtl/qwen_split/qfd_fwd_lane.sv rtl/hbm_accel/die_glue/ot_hbm_lane.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/tb/tb_exact_tail.sv"
iverilog -g2012 -s tb_exact_tail -o ../tail.iv $SRCS > ../iverilog.build.log 2>&1
vvp ../tail.iv > ../iverilog.pass.log 2>&1
iverilog -g2012 -DMUT_NO_RELAY -s tb_exact_tail -o ../tail_mut.iv $SRCS > ../iverilog_mut.build.log 2>&1
set +e
vvp ../tail_mut.iv > ../iverilog.mutant.log 2>&1
rc=$?
set -e
[ "$rc" != 0 ] && grep -q TAIL_RESET_OR_DATA_MISMATCH ../iverilog.mutant.log
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version > ../verilator.version
$V --binary --timing -j 4 -Wno-fatal --top-module tb_exact_tail --Mdir ../obj_tail $SRCS > ../verilator.build.log 2>&1
../obj_tail/Vtb_exact_tail > ../verilator.pass.log 2>&1
grep -q EXACT_TAIL_NATIVE_PASS ../verilator.pass.log
echo EXACT_TAIL_NATIVE_ALL_PASS
