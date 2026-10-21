#!/bin/bash
# QW-TLPROD: TABLE_REL unit bench (see tb).  usage: run_calr_rel.sh OUTDIR MUT IMAGE_DIR  (from repo root; verilator = 5.050)
#   MUT 0 + the produced image (calr_table_producer --mode rel): CALR_REL_PASS.  MUT 35 (drop stage 17), or the image
#   without the producer entry (--mode none) / with an absolute stage-1 entry (--mode abs1): CALR_REL_FAIL.
set -uo pipefail
OUT=${1:?outdir}; MUT=${2:-0}; IMG=${3:?image dir}; R=$(pwd)
mkdir -p "$OUT"; verilator --version
M=$R/physical/asap7_memory_macros
SRCS="$R/rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv $R/rtl/qwen_dv/qfd_dv_calendar_rom.sv $R/rtl/lib/ot_ks_add.sv $R/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv $R/rtl/qwen_sys/program_receiver_20261014/qkd_program_pw_observer_p.sv $M/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v $R/rtl/test/qwen_dv/calr_rel/tb_qfd_dv_cmd_cal_mu_calr_rel.sv"
verilator --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_dv_cmd_cal_mu_calr_rel -GMUT=$MUT -Mdir "$OUT/obj" $SRCS > "$OUT/build.log" 2>&1 \
  || { tail -40 "$OUT/build.log"; echo CALR_REL_BUILD_FAIL; exit 3; }
"$OUT/obj/Vtb_qfd_dv_cmd_cal_mu_calr_rel" +OT_ROM_DIR="$IMG" 2>&1 | tee "$OUT/sim.log" | tail -8
grep -q '^CALR_REL_PASS' "$OUT/sim.log"
