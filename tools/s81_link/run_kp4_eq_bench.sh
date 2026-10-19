#!/usr/bin/env bash
# S81-TILES2 2026-10-17: bit-exact equivalence of the four-tile KP4 decoder (dsyn / ddly / dchn / dout) vs the frozen
# two-tile decoder of 33a35eb7d, RTL (same cycle) and hardware view (every tile pin registered, +2 cycles).
# usage: run_kp4_eq_bench.sh MODE OUTDIR   MODE: base (PASS) | dmut (DMUT 2, FAIL) | amut (DMUT 3, FAIL) | seam (SEAMMUT 1, FAIL)
#        | preg (PREGMUT 1: the hardened parent's input landing register missing, FAIL)
set -u
mode=${1:?base|dmut|amut|seam|preg}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link; M=$R/physical/asap7_memory_macros
case $mode in base) g="";; dmut) g="-GDMUT=2";; amut) g="-GDMUT=3";; seam) g="-GSEAMMUT=1";; preg) g="-GPREGMUT=1";; *) echo "KP4_EQ BAD_MODE $mode"; exit 2;; esac
python3 "$R/tools/s81_link/rs544.py" vectors "$out/vec.hex" --n 16 --seed 5 > /dev/null
verilator --binary --timing -j ${KP4_J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTITOP +incdir+$L \
  --top-module tb_s81_kp4_eq $g --Mdir "$out/obj" -o tb "$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" "$L/ot_s81_kp4_bm.sv" \
  "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" "$L/ot_s81_kp4_dec.sv" \
  "$L/ref/ot_s81_kp4_dec_r33.sv" "$M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" \
  "$L/tb_s81_kp4_eq.sv" > "$out/build.log" 2>&1 || { echo "KP4_EQ BUILD_FAIL $mode"; tail -5 "$out/build.log"; exit 2; }
"$out/obj/tb" +vec="$out/vec.hex" +verilator+seed+${KP4_SEED:-11} > "$out/run.log" 2>&1
grep '^ERR' "$out/run.log" | head -3
grep '^TB_S81_KP4' "$out/run.log" | tail -3
grep -q '^TB_S81_KP4_EQ PASS$' "$out/run.log"
