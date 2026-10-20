#!/bin/bash
# LH-SMATT/INT8 10-19: run_smh_int8_tile_bench.sh <workdir> [MUT none|pend|sign|tag] [CYCLES] [SEED]  (repo root; Verilator 5.050)
set -u
W=$1; M=${2:-none}; C=${3:-20000}; S=${4:-1}
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
T=rtl/hbm_accel/sm/static
D=""; case "$M" in pend) D=-DOT_I8T_MUT_PEND;; sign) D=-DOT_I8T_MUT_SIGN;; tag) D=-DOT_I8T_MUT_TAG;; none) ;; *) echo "bad MUT $M"; exit 2;; esac
mkdir -p "$W"; W=$(realpath "$W")
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD $D -GCYCLES=$C -GSEED=$S \
  --top-module tb_smh_int8_tile_safe --Mdir "$W/obj" -o tb \
  $T/test/tb_smh_int8_tile_safe.sv $T/ot_smh_int8_tile_safe.sv $T/ot_smh_static_int8.sv rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv \
  > "$W/build.log" 2>&1 || { tail -20 "$W/build.log"; echo "I8T BUILD FAIL"; exit 1; }
"$W/obj/tb" | tee "$W/run.log" | tail -8
grep -q "^I8T PASS" "$W/run.log"
