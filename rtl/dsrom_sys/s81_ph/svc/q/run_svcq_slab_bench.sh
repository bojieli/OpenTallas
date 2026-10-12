#!/usr/bin/env bash
# CLAUDE s81-svcq-1011: build + run the SLAB exact gate (tb_s81_svcq_slab) on the tools/v41_ckv_sel_attn_vectors.py
# golden vectors.  Usage (repo root, fleet host, under ot-heavy): run_svcq_slab_bench.sh BUILD VEC "DIE ST [DEFINE]" ...
set -euo pipefail
B=$1; VEC=$2; shift 2
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
CASES=${CASES:-"full1m short300 skew1m tail46"}; SEEDS=${SEEDS:-"1 2"}; JOBS=${JOBS:-16}
Q=rtl/dsrom_sys/s81_ph/svc/q
IDX_SRCS=${IDX_SRCS-"rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv rtl/hdc/v41x/ot_hdc_v41x_idx_score_quarter.sv rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv rtl/hdc/v41x/ot_hdc_v41x_idx_ring_ranges.sv"}
SRC=(rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
     rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv
     rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv
     physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
     rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
     rtl/hdc/v41x/ot_dsrom_su_add6.sv
     rtl/chip/ot_chip_v41x_ckv_stream_merge.sv rtl/chip/ot_chip_v41x_ckv_pc_fetch.sv
     rtl/chip/ot_dsrom_window_stream_la.sv rtl/chip/window_owner_safe/ot_chip_v41x_window_attn_source_owner_safe.sv
     rtl/chip/window_owner_safe/ot_chip_v41x_window_kv_prefetch_owner_safe.sv rtl/chip/ot_chip_v41x_window_refill_schedule.sv
     rtl/chip/ot_chip_v41x_window_retention.sv rtl/chip/ot_chip_v41x_window_row_codec.sv rtl/chip/ot_chip_v41x_window_stage4.sv
     rtl/chip/ot_chip_v41x_window_stream.sv rtl/chip/ot_chip_v41x_attn_row_merge.sv
     rtl/dsrom_sys/s81_window_la/ot_dsrom_window_stream_la_s81.sv rtl/dsrom_sys/s81_window_la/ot_dsrom_window_la_stage.sv
     rtl/dsrom_sys/s81_window_la/ot_dsrom_window_attn_source_la.sv
     rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_writer_pipeline.sv rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_stage_pipeline.sv
     rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_source_pipeline.sv rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_row_merge_pipeline.sv
     ${IDX_SRCS:-}
     $Q/ot_s81_svcq_selfetch.sv $Q/ot_s81_svcq_rows.sv $Q/ot_s81_svcq_attn.sv $Q/ot_s81_svcq_pcarb.sv $Q/ot_s81_svcq_idx.sv
     $Q/ot_s81_svcq_slab.sv $Q/tb_s81_svcq_slab.sv)
HIER=rtl/dsrom_sys/s81_ph/svc/q/svcq_hierarchy.vlt
mkdir -p "$B"
for cfg in "$@"; do
  read -r DIE ST DEF <<<"$cfg"; DEF=${DEF:-}
  tag=d${DIE}s${ST}${DEF:+_$DEF}; o=$B/$tag
  if [ ! -x "$o/obj/Vtb" ]; then
    mkdir -p "$o"
    "$VL" --cc --exe --build --top-module tb_s81_svcq_slab --prefix Vtb -Mdir "$o/obj" -j "$JOBS" -Wno-fatal -Wno-WIDTH \
      -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 1 --unroll-limit 131072 \
      -MAKEFLAGS OPT_SLOW=-O0 --hierarchical "$HIER" -GDIE=$DIE -GST=$ST ${ENGDEF:+-D$ENGDEF} ${DEF:+-D$DEF} \
      "${SRC[@]}" rtl/test/hdc_v41_harness.cpp -CFLAGS -O1 >"$o/build.log" 2>&1 || { echo "$tag BUILD FAIL"; tail -20 "$o/build.log"; continue; }
  fi
  for c in $CASES; do for s in $SEEDS; do
    "$o/obj/Vtb" +dir="$VEC/$c" +seed=$s >"$o/run_${c}_s$s.log" 2>&1 || true
    echo "$tag $c s$s: $(grep -h SVCQSLAB "$o/run_${c}_s$s.log" | tail -1)"
  done; done
done
