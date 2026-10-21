#!/usr/bin/env bash
# DRIVE-S81-ATTN1 (10-20): NT1 engine lockstep bench (tb_attn1_nt1.sv): ot_hdc_v41x_attn_s NTP 1 vs NTP 0 (4 tiles).
# usage (repo root): attn1_bench.sh OUT TAG "VFLAGS" "RUNS"
#   VFLAGS: -GNMUT=<n> -GNTP=<n> ...;  RUNS = space list of plusarg sets, ',' separated (e.g. "seed=1,njob=12 seed=2,bub=0")
# TAG m0 (no NMUT) must print ATTN1LOCK ... PASS for every run; NMUT 1/2/3 mutants must FAIL (mismatches > 0).
set -u
OUT=${1:?out}; TAG=${2:?tag}; VF=${3:-}; RUNS=${4:-"seed=1"}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
V=rtl/hdc/v41x; H=rtl/hdc
O=$(mkdir -p "$OUT" && cd "$OUT" && pwd)/$TAG; rm -rf "$O"; mkdir -p "$O"
"$VL" --version | tee "$O/verilator.version"
SRC="tools/s81_dv/svc_rs/tb_attn1_nt1.sv $V/ot_hdc_v41x_attn_s.sv $V/ot_hdc_v41x_attn_tile_s.sv $V/ot_hdc_v41x_kreg.sv \
 $V/ot_hdc_v41x_attn_tile_lat.sv $V/ot_hdc_v41x_attn_tile.sv $V/ot_hdc_v41x_attn.sv $V/ot_hdc_v41x_attn_staging.sv \
 $V/ot_hdc_v41x_attn_hgrp_s81.sv $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_prefix.sv $H/ot_hdc_fp32_f12.sv \
 $V/ot_dsrom_su_add6.sv $H/ot_hdc_delay.sv $H/ot_hdc_fastfp_lat_f12.sv $H/ot_hdc_fp32_mul_lat.sv"
sha256sum $SRC > "$O/sources.sha256"
"$VL" --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style --unroll-count 64 \
    -CFLAGS -O1 $VF --top-module tb_attn1_nt1 -Mdir "$O/obj" -o sim $SRC > "$O/build.log" 2>&1 \
    || { tail -40 "$O/build.log"; echo "ATTN1_BENCH BUILD_FAIL tag=$TAG"; exit 2; }
fail=0; i=0
for r in $RUNS; do
  i=$((i+1)); args=""; for a in ${r//,/ }; do args="$args +$a"; done
  "$O/obj/sim" $args > "$O/run_$i.log" 2>&1; rc=$?
  line=$(grep -h 'ATTN1PROBE\|ATTN1LOCK\|MISMATCH' "$O/run_$i.log" | head -4 | tr '\n' ' ')
  if [ $rc -eq 0 ] && grep -q "ATTN1LOCK .* mismatches=0 .*PASS" "$O/run_$i.log"; then
    echo "ATTN1_BENCH PASS tag=$TAG run=$r $line"
  else
    echo "ATTN1_BENCH FAIL tag=$TAG run=$r rc=$rc $line"; fail=1
  fi
done
exit $fail
