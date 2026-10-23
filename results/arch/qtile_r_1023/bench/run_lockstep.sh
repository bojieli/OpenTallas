#!/bin/bash
# QTILE-R 10-23: build once (Verilator 5.050) + run MUT 0..4.  usage: run_lockstep.sh SRCROOT OUTDIR [NCYC]
set -u
S=$1; O=$2; N=${3:-20000}
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p $O; cd $O
$V --version | tee version.txt
M=$S/physical/asap7_memory_macros; P=$S/rtl/qwen_dv/headprep13
SRCS="$S/results/arch/qtile_r_1023/bench/tb_hp13_pr_lockstep.sv
 $P/physical_abi/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1_physical.sv
 $P/physical_abi/qfd_tt_ctlm_dv_hp13_rrloc_native32_cpub39_1_physical_wtnbal24_pr.sv
 $P/corepub39/qfd_hp13_corepub39.sv $P/native32/qfd_tt_ctlm_dv_hp13_rrloc_helpers.sv $P/h16za/native32_1r_param.v
 $P/h16za/native32_helpers.sv $S/rtl/qwen_dv/qfd_tt_ctlm_dv_wtn.sv $P/wtn_balanced24/helpers.sv
 $P/wtn_balanced24/qfd_tt_ctlm_dv_wtn_balanced24.sv $P/physical_abi/qfd_dv_typed_witness_control_frozen.sv
 $M/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v $M/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v
 $M/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v"
sha256sum $SRCS > sources.sha256
/usr/bin/time -v $V --binary -j 16 --top-module tb_hp13_pr_lockstep -GNCYC=$N -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  --x-assign 0 --x-initial 0 -O2 -Mdir obj $SRCS > build.log 2>&1; rc=$?
tail -3 build.log; grep -E "Maximum resident" build.log
[ $rc -eq 0 ] || { echo "BUILD FAIL rc=$rc"; exit 2; }
for m in 0 1 2 3 4; do ./obj/Vtb_hp13_pr_lockstep +MUT=$m +SEED=7 > mut$m.log 2>&1; grep -h HP13PR_LOCKSTEP mut$m.log || { echo "MUT $m no verdict"; tail -3 mut$m.log; }; done
./obj/Vtb_hp13_pr_lockstep +MUT=0 +SEED=99 > mut0_s99.log 2>&1; grep -h HP13PR_LOCKSTEP mut0_s99.log
