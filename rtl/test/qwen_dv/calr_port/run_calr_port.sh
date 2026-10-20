#!/bin/bash
# QW-F16SUB: CALR port bench (see tb).  usage: run_calr_port.sh OUTDIR MUT   (from repo root; `verilator` = daemon 5.050)
#   MUT 0: CALR_PORT_PASS expected.  MUT 34 (dq one short) / 2 (entry halves swapped): CALR_PORT_EDGE_MISMATCH expected.
set -uo pipefail
OUT=${1:?outdir}; MUT=${2:-0}; R=$(pwd)
mkdir -p "$OUT"; verilator --version
M=$R/physical/asap7_memory_macros
SRCS="$R/rtl/qwen_dv/qfd_dv_cmd_cal_mu.sv $R/rtl/test/qwen_dv/calr_port/qfd_dv_cmd_cal_mu_f16ref.sv $R/rtl/qwen_dv/qfd_dv_calendar_rom.sv
 $R/rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv $M/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
 $M/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v $R/rtl/test/qwen_dv/calr_port/tb_qfd_dv_cmd_cal_mu_calr_port.sv"
verilator --binary --timing -j 8 -Wno-fatal --top-module tb_qfd_dv_cmd_cal_mu_calr_port -GMUT=$MUT -Mdir "$OUT/obj" $SRCS > "$OUT/build.log" 2>&1 \
  || { tail -40 "$OUT/build.log"; echo CALR_PORT_BUILD_FAIL; exit 3; }
"$OUT/obj/Vtb_qfd_dv_cmd_cal_mu_calr_port" +OT_ROM_DIR="$R/rtl/test/qwen_dv/calr_port" 2>&1 | tee "$OUT/sim.log" | tail -12
grep -q '^CALR_PORT_PASS' "$OUT/sim.log"
