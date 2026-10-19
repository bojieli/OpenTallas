#!/usr/bin/env bash
# TW-S81/SERDES 2026-10-19: two-die link bench of the landed column SerDes ot_pdie_serdes_col (tb_s81_pdie_col).
# usage: run_serdes_col_bench.sh MODE OUTDIR   MODE: col (PASS) | col_ref (PASS) | ref_col (PASS) | mut1 (FAIL) | mut2 (FAIL)
# Verilator (fleet: the daemon's 5.050); run via ot-run, never on localhost.
set -u
mode=${1:?col|col_ref|ref_col|mut1|mut2}; out=${2:?fresh output directory}; mkdir -p "$out"
R=$(cd "$(dirname "$0")/../.." && pwd); L=$R/rtl/dsrom_sys/s81_link; M=$R/physical/asap7_memory_macros
case $mode in col) g="-GMODE=0";; col_ref) g="-GMODE=1";; ref_col) g="-GMODE=2";; mut1) g="-GMODE=0 -GMUT=1";; mut2) g="-GMODE=0 -GMUT=2";;
  *) echo "PDIE_COL BAD_MODE $mode"; exit 2;; esac
verilator --version > "$out/verilator.version" 2>&1
verilator --binary --timing -j ${COL_J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTITOP +incdir+$L \
  --top-module tb_s81_pdie_col $g --Mdir "$out/obj" -o tb "$L/ot_s81_kp4_common.sv" "$L/ot_s81_kp4_enc.sv" "$L/ot_s81_kp4_bm.sv" \
  "$L/ot_s81_kp4_dsyn.sv" "$L/ot_s81_kp4_ddly.sv" "$L/ot_s81_kp4_dchn.sv" "$L/ot_s81_kp4_dout.sv" "$L/ot_s81_kp4_dec.sv" \
  "$L/ot_pdie_serdes.sv" "$L/native/ot_s81_kp4_dec_native_flat.sv" "$L/ot_s81_edge3.sv" "$L/ot_s81_kp4_dec_edge3.sv" \
  "$R/rtl/common/landed_parent/ot_pl_land.sv" "$L/col/ot_pdie_serdes_edge3.sv" \
  "$M/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v" "$M/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v" \
  "$L/col/tb_s81_pdie_col.sv" > "$out/build.log" 2>&1 || { echo "PDIE_COL BUILD_FAIL $mode"; tail -5 "$out/build.log"; exit 2; }
"$out/obj/tb" +verilator+seed+${COL_SEED:-11} > "$out/run.log" 2>&1
grep '^ERR' "$out/run.log" | head -3
grep '^TB_S81_PDIE_COL' "$out/run.log" | tail -2
grep -q '^TB_S81_PDIE_COL PASS$' "$out/run.log"
