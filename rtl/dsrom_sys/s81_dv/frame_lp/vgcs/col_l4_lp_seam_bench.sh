#!/usr/bin/env bash
# S81-P6 10-23: lockstep bench col_<M>_l4 (flat reference) vs the BANDED SEAM twin vgcs/col_<M>_l4_lp_rf3r.sv
# (frame_seam_pipe.py of vgch: band-seam landings -> ot_pl_seam_w/r at plan width) with the lp testbench + mutants 1 2 4.
# M=h9 (default; tb vgc/) or M=h10 (tb vg/).
# REF=vgch runs the same bench on the unmodified banded twin (baseline).  Run on the FLEET (ot-run), never on localhost.
#   bash rtl/dsrom_sys/s81_dv/frame_lp/vgcs/col_h9_l4_lp_bench.sh OUTDIR
set -u
cd "${LP_ROOT:-$(cd "$(dirname "$0")/../../../../.." && pwd)}"
OUT=${1:-seam_bench_out}; mkdir -p "$OUT"; rc=0; V=${REF:-vgcs}; M=${M:-h9}; TBD=$([ "$M" = h9 ] && echo vgc || echo vg)
DUT0="rtl/dsrom_sys/s81_dv/frame_lp/$V/col_${M}_l4_lp_rf3r.sv"
# sources: the frame bench file list (tools/s81_dv/frame_bench.f, the same module versions the frame bench builds) + the
# flat frame, the landing / seam primitives, the DUT and the generated lockstep tb.  DUT / SEAM_SV override = bench mutants
# (a twin copy with one seam re-timed, or a re-timed ot_pl_seam): the lockstep must FAIL.
DUT=${DUT:-$DUT0}
SRCS="-f tools/s81_dv/frame_bench.f rtl/dsrom_sys/s81_dv/frame_l4/col_${M}_l4.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/lib/ot_reset_sync.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv ${SEAM_SV:-rtl/common/landed_parent/ot_pl_seam.sv} $DUT rtl/dsrom_sys/s81_dv/frame_lp/$TBD/tb_col_${M}_l4_lp.sv"
for m in ${MUTS:-0 1 2 4}; do
  if [ "${SIM:-verilator}" = verilator ]; then
    ${VERILATOR:-$([ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && echo ~/.local/opentallas-tools/verilator-5.050/bin/verilator || echo verilator)} --binary -j ${VL_JOBS:-8} --build-jobs ${VL_JOBS:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -Wno-WIDTH -Wno-MULTIDRIVEN -DDSFD_PQ_STATIC_X2 -DDSFD_PQ_HAS_BF_X2 -O1 \
      --top-module tb_col_${M}_l4_lp -GMUT=$m $SRCS -Mdir "$OUT/obj$m" > "$OUT/build_$m.log" 2>&1 \
      && "$OUT/obj$m/Vtb_col_${M}_l4_lp" > "$OUT/mut$m.log" 2>&1
  else
    iverilog -g2012 -I. -o "$OUT/sim$m" -s tb_col_${M}_l4_lp -Ptb_col_${M}_l4_lp.MUT=$m $SRCS > "$OUT/build_$m.log" 2>&1 \
      && vvp -n "$OUT/sim$m" > "$OUT/mut$m.log" 2>&1
  fi
  r=$(grep -o 'LP_LOCKSTEP [A-Z]*' "$OUT/mut$m.log" 2>/dev/null | head -1)
  echo "$M $V MUT $m: ${r:-NO_RESULT (see $OUT/build_$m.log)} $(grep -c LAND_FAULT "$OUT/mut$m.log" 2>/dev/null) land_faults"
  if [ $m -eq 0 ]; then [ "$r" = "LP_LOCKSTEP PASS" ] || rc=1; else [ "$r" = "LP_LOCKSTEP FAIL" ] || rc=1; fi
done
echo "BENCH_EXIT $rc"; exit $rc
