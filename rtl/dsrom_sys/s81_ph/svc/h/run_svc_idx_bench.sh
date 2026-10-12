#!/usr/bin/env bash
# CLAUDE s81die-1011/ctrl svch: build + run the index-reader TILE exact gate (tb_dsfd_svc_idx, the checks of tb_s81_svcq_idx) on the vectors of
# tools/s81_svcq/idx_vectors.py.  Usage (repo root, fleet host, under ot-heavy):
#   rtl/dsrom_sys/s81_ph/svc/h/run_svc_idx_bench.sh BUILD VEC "ST [DEFINE] : case1,case2" ...
# Env: SEEDS (default "1 2"), JOBS (default 8).
set -euo pipefail
B=$1; VEC=$2; shift 2
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SEEDS=${SEEDS:-"1 2"}; JOBS=${JOBS:-8}
SRC=(rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv rtl/hdc/v41x/ot_hdc_v41x_idx.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv rtl/hdc/v41x/ot_hdc_v41x_idx_score_quarter.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_kstream.sv rtl/hdc/v41x/ot_hdc_v41x_idx_kstream_ring.sv
     rtl/hdc/v41x/ot_hdc_v41x_idx_ring_ranges.sv rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv
     rtl/dsrom_sys/s81_ph/svc/q/ot_s81_svcq_idx.sv rtl/dsrom_sys/s81_ph/svc/h/ot_s81_svch_lane.sv rtl/dsrom_sys/s81_ph/svc/ot_s81ph_svc_io.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svc_idx.sv rtl/dsrom_sys/s81_ph/svc/h/tb_dsfd_svc_idx.sv)
mkdir -p "$B"
for cfg in "$@"; do
  spec=${cfg%%:*}; cases=${cfg#*:}; read -r ST DEF <<<"$spec"; DEF=${DEF:-}
  tag=st${ST}${DEF:+_$DEF}; o=$B/$tag
  if [ ! -x "$o/obj/Vtb" ]; then
    mkdir -p "$o"
    "$VL" --cc --exe --build --top-module tb_dsfd_svc_idx --prefix Vtb -Mdir "$o/obj" -j "$JOBS" -O3 --x-assign fast \
      --x-initial fast -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-DECLFILENAME -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
      -GST=$ST ${DEF:+-D$DEF} rtl/test/tb_hdc_v41x_idx_array.vlt "${SRC[@]}" rtl/test/hdc_v41_harness.cpp \
      -CFLAGS -O1 >"$o/build.log" 2>&1 || { echo "$tag BUILD FAIL"; tail -20 "$o/build.log"; continue; }
  fi
  for c in ${cases//,/ }; do for s in $SEEDS; do
    /usr/bin/time -v "$o/obj/Vtb" +dir="$VEC/$c" +seed=$s >"$o/run_${c}_s$s.log" 2>&1 || true
    echo "$tag $c s$s: $(grep -h SVCQIDX "$o/run_${c}_s$s.log" | tail -1) maxrss_kb=$(grep -h 'Maximum resident' "$o/run_${c}_s$s.log" | awk '{print $NF}')"
  done; done
done
