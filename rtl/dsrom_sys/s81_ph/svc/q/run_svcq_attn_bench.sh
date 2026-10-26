#!/usr/bin/env bash
# CLAUDE s81-svcq-1011: build + run the slab attention exact gate (tb_s81_svcq_attn) on the golden vectors of
# tools/v41_ckv_sel_attn_vectors.py.  Usage (from the repo root, on a fleet host under ot-heavy):
#   rtl/dsrom_sys/s81_ph/svc/q/run_svcq_attn_bench.sh BUILD VEC "DIE ST [DEFINE]" ... 
# BUILD = build dir (one executable per (DIE, ST, DEFINE)); VEC = vectors root (cases full1m short300 skew1m tail46).
# Env: ENGDEF=SVCQ_ENG_FG3 (as-built engine latencies), CASES (default all four), SEEDS (default "1 2"), JOBS (default 16).
set -euo pipefail
B=$1; VEC=$2; shift 2
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
CASES=${CASES:-"full1m short300 skew1m tail46"}; SEEDS=${SEEDS:-"1 2"}; JOBS=${JOBS:-16}
SRC=(rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
     rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv
     rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv
     physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
     rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
     rtl/hdc/v41x/ot_dsrom_su_add6.sv
     rtl/chip/ot_chip_v41x_ckv_stream_merge.sv rtl/chip/ot_chip_v41x_ckv_pc_fetch.sv
     rtl/dsrom_sys/s81_ph/svc/q/ot_s81_svcq_selfetch.sv rtl/dsrom_sys/s81_ph/svc/q/ot_s81_svcq_rows.sv
     rtl/dsrom_sys/s81_ph/svc/q/ot_s81_svcq_attn.sv rtl/dsrom_sys/s81_ph/svc/q/tb_s81_svcq_attn.sv)
HIER=rtl/dsrom_sys/s81_ph/svc/q/svcq_hierarchy.vlt
mkdir -p "$B"
for cfg in "$@"; do
  read -r DIE ST DEF <<<"$cfg"; DEF=${DEF:-}
  tag=d${DIE}s${ST}${DEF:+_$DEF}; o=$B/$tag
  if [ ! -x "$o/obj/Vtb" ]; then
    mkdir -p "$o"
    "$VL" --cc --exe --build --top-module tb_s81_svcq_attn --prefix Vtb -Mdir "$o/obj" -j "$JOBS" -Wno-fatal -Wno-WIDTH \
      -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 1 --unroll-limit 131072 \
      -MAKEFLAGS OPT_SLOW=-O0 --hierarchical "$HIER" -GDIE=$DIE -GST=$ST ${ENGDEF:+-D$ENGDEF} ${DEF:+-D$DEF} \
      "${SRC[@]}" rtl/test/hdc_v41_harness.cpp -CFLAGS -O1 >"$o/build.log" 2>&1 || { echo "$tag BUILD FAIL"; tail -20 "$o/build.log"; continue; }
  fi
  for c in $CASES; do for s in $SEEDS; do
    "$o/obj/Vtb" +dir="$VEC/$c" +seed=$s >"$o/run_${c}_s$s.log" 2>&1 || true
    echo "$tag $c s$s: $(grep -h SVCQATTN "$o/run_${c}_s$s.log" | tail -1)"
  done; done
done
