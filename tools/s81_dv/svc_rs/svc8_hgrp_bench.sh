#!/usr/bin/env bash
# S81-SVC8 (10-20): lockstep bench ot_s81svc8_hgrp_s81 vs the old ot_hdc_v41x_attn_hgrp_s81 (tb_svc8_hgrp.sv).
# usage (repo root): svc8_hgrp_bench.sh OUT TAG "DEFINES" NCYC "RUNS"   RUNS = "seed:gid:ivp:ldp ..."
# TAG m0 (no defines) must PASS; mutants (-DSVC8_MUT_BANK, -DSVC8_RING_MUT_ADDR, -DSVC8_HGRP_MUT=2) must FAIL.
set -u
OUT=${1:?out}; TAG=${2:?tag}; DEFS=${3:-}; NCYC=${4:-20000}; RUNS=${5:-"1:1:4:3 2:3:0:2"}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
V=rtl/hdc/v41x; H=rtl/hdc
O=$(mkdir -p "$OUT" && cd "$OUT" && pwd)/$TAG; rm -rf "$O"; mkdir -p "$O"
"$VL" --version
SRC="tools/s81_dv/svc_rs/tb_svc8_hgrp.sv $V/ot_s81svc8_hgrp_s81.sv $V/ot_s81svc8_ring.sv $V/ot_s81svc8_sram_wreg.v \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v \
 $V/ot_hdc_v41x_attn_hgrp_s81.sv $V/ot_hdc_v41x_attn_tile_s.sv $V/ot_hdc_v41x_attn_tile_lat.sv \
 $V/ot_hdc_v41x_attn_tile.sv $V/ot_hdc_v41x_kreg.sv $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_prefix.sv \
 $H/ot_hdc_fp32_f12.sv $V/ot_dsrom_su_add6.sv"
sha256sum $SRC > "$O/sources.sha256"
"$VL" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style --unroll-count 64 \
    $DEFS -GNCYC=$NCYC --top-module tb_svc8_hgrp -Mdir "$O/obj" -o sim $SRC > "$O/build.log" 2>&1 \
    || { tail -30 "$O/build.log"; echo "SVC8_BENCH BUILD_FAIL tag=$TAG"; exit 2; }
fail=0
for r in $RUNS; do
  IFS=: read s g ip lp <<< "$r"
  "$O/obj/sim" +seed=$s +gid=$g +ivp=$ip +ldp=$lp > "$O/sim_s${s}_g${g}.log" 2>&1; rc=$?
  tail -7 "$O/sim_s${s}_g${g}.log"
  if [ $rc -eq 0 ] && grep -q "SVC8LOCK cycles=.* mismatches=0 " "$O/sim_s${s}_g${g}.log"; then
    echo "SVC8_BENCH PASS tag=$TAG run=$r $(grep -o 'SVC8LOCK.*' "$O/sim_s${s}_g${g}.log")"
  else
    echo "SVC8_BENCH FAIL tag=$TAG run=$r rc=$rc $(grep -o 'SVC8LOCK.*\|MISMATCH.*' "$O/sim_s${s}_g${g}.log" | head -2 | tr '\n' ' ')"; fail=1
  fi
done
exit $fail
