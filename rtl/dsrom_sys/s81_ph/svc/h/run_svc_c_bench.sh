#!/usr/bin/env bash
# CLAUDE s81die-1011/ctrl svch: lint the hierarchical slab tiles, or build + run the slab-PIN exact gate tb_dsfd_svc_c
# (dsfd_svc_c driven through its pins: j descriptor, q, ad / od / xd out, the 32 PC faces with the HBM model) on the
# tools/v41_ckv_sel_attn_vectors.py golden vectors (same cases / checks as tb_s81_svcq_slab).
# Usage (repo root, fleet host, under admit.sh):
#   run_svc_c_bench.sh lint
#   run_svc_c_bench.sh BUILD VEC "DIE ST [DEFINE]" ...        (ENGDEF=SVCQ_ENG_FG3 for the buildable engine latencies)
set -euo pipefail
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
CASES=${CASES:-"full1m short300 skew1m tail46"}; SEEDS=${SEEDS:-"1 2"}; JOBS=${JOBS:-16}
SRAM_MACRO=${SRAM_MACRO:-0}
NATIVE_FP32_PV=${NATIVE_FP32_PV:-0}
case "$SRAM_MACRO" in 0|1) ;; *) echo "SRAM_MACRO must be 0 or 1" >&2; exit 2;; esac
case "$NATIVE_FP32_PV" in 0|1) ;; *) echo "NATIVE_FP32_PV must be 0 or 1" >&2; exit 2;; esac
if [ "$NATIVE_FP32_PV" = 1 ]; then : "${EREAL:?actual SU FP32 e-file directory required}"; fi
S=rtl/dsrom_sys/s81_ph/svc; Q=$S/q; HH=$S/h
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
     rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_score_quarter.sv rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_ring_ranges.sv
     $Q/ot_s81_svcq_selfetch.sv $Q/ot_s81_svcq_rows.sv $Q/ot_s81_svcq_idx.sv
     $HH/ot_s81_svch_lane.sv $HH/ot_s81_svch_pcsvc.sv $HH/dsfd_svch_pcs.sv $HH/ot_s81_svch_comb.sv $HH/ot_s81_svch_attq.sv $HH/ot_s81_svch_home.sv
     $S/dsfd_svc_quad.sv $S/dsfd_svc_idx.sv
     rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv $S/ot_s81ph_svc_io.sv rtl/common/ot_fwd_link_stage.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
     $S/ot_s81ph_svc_io_tiles.sv $S/dsfd_svcio_job.sv $S/dsfd_svc_pc.sv
     $S/ot_s81_svc_probability_pack.sv $S/ot_s81_svc_probability_frame.sv $S/dsfd_svc_c.sv)
HIER=${HIER:-$HH/svch_hierarchy.vlt}
if [ "${1:-}" = lint ]; then
  for top in "dsfd_svch_pcs" "dsfd_svch_rly" "dsfd_svc_quad -GQID=0" "dsfd_svc_quad -GQID=1" "dsfd_svc_quad -GQID=2" "dsfd_svc_quad -GQID=3" "dsfd_svc_idx" "dsfd_svc_c"; do
    set -- $top
    "$VL" --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM -Wno-PINCONNECTEMPTY -Wno-WIDTH \
      -Wno-TIMESCALEMOD -Wno-VARHIDDEN -Wno-UNDRIVEN -Wno-MULTIDRIVEN -Wno-GENUNNAMED -Wno-SYNCASYNCNET \
      --top-module "$@" ${ENGDEF:+-D$ENGDEF} "${SRC[@]}" > "lint_${1}${2:+_${2#-G}}.log" 2>&1 \
      && echo "LINT $* rc=0 warn=$(grep -c '%Warning' lint_${1}${2:+_${2#-G}}.log)" || { echo "LINT $* FAIL"; grep -m8 '%Error' "lint_${1}${2:+_${2#-G}}.log"; }
  done
  exit 0
fi
B=$1; VEC=$2; shift 2
mkdir -p "$B"
for cfg in "$@"; do
  read -r DIE ST DEF <<<"$cfg"; DEF=${DEF:-}
  tag=d${DIE}s${ST}${DEF:+_$DEF}; [ "$SRAM_MACRO" = 0 ] || tag=${tag}_sram1; o=$B/$tag
  [ "$NATIVE_FP32_PV" = 0 ] || { tag=${tag}_nativepv; o=$B/$tag; }
  if [ ! -x "$o/obj/Vtb" ]; then
    mkdir -p "$o"
    "$VL" --cc --exe --build --top-module tb_dsfd_svc_c --prefix Vtb -Mdir "$o/obj" -j "$JOBS" -Wno-fatal -Wno-WIDTH \
      -Wno-TIMESCALEMOD --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 1 --unroll-limit 131072 \
      -MAKEFLAGS OPT_SLOW=-O0 --hierarchical "$HIER" -GDIE=$DIE -GST=$ST -GSRAM_MACRO=$SRAM_MACRO -GNATIVE_FP32_PV=$NATIVE_FP32_PV ${ENGDEF:+-D$ENGDEF} ${DEF:+-D$DEF} \
      "${SRC[@]}" $HH/tb_dsfd_svc_c.sv rtl/test/hdc_v41_harness.cpp -CFLAGS -O1 >"$o/build.log" 2>&1 || { echo "$tag BUILD FAIL"; tail -20 "$o/build.log"; continue; }
  fi
  for c in $CASES; do for s in $SEEDS; do
    trace=$o/trace_${c}_s$s; mkdir -p "$trace"
    extra=(); [ "$NATIVE_FP32_PV" = 0 ] || extra+=("+e_file=$EREAL/$c/native_e.hex")
    "$o/obj/Vtb" +dir="$VEC/$c" +seed=$s +trace="$trace" "${extra[@]}" >"$o/run_${c}_s$s.log" 2>&1 || true
    echo "$tag $c s$s: $(grep -h SVCC "$o/run_${c}_s$s.log" | tail -1)"
  done; done
done
