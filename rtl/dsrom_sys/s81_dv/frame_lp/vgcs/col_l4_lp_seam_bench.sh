#!/usr/bin/env bash
# S81-P6 10-23: lockstep bench col_<M>_l4 (flat reference) vs the BANDED SEAM twin vgcs/col_<M>_l4_lp_rf3r.sv
# (frame_seam_pipe.py of vgch: band-seam landings -> ot_pl_seam_w/r at plan width) with the lp testbench + mutants 1 2 4.
# M=h9 (default; tb vgc/) or M=h10 (tb vg/).  EXTRA_SRCS = extra dependency files (one list file).
# REF=vgch runs the same bench on the unmodified banded twin (baseline).  Run on the FLEET (ot-run), never on localhost.
#   bash rtl/dsrom_sys/s81_dv/frame_lp/vgcs/col_h9_l4_lp_bench.sh OUTDIR
set -u
cd "${LP_ROOT:-$(cd "$(dirname "$0")/../../../../.." && pwd)}"
OUT=${1:-seam_bench_out}; mkdir -p "$OUT"; rc=0; V=${REF:-vgcs}; M=${M:-h9}; TBD=$([ "$M" = h9 ] && echo vgc || echo vg)
DUT="rtl/dsrom_sys/s81_dv/frame_lp/$V/col_${M}_l4_lp_rf3r.sv"
SRCS="rtl/dsrom_sys/s81_dv/frame_l4/col_${M}_l4.sv rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_266ew.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_536.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_c26l.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gen18.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_v16.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLd.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfd.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_LLfu.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfd.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv rtl/v41die/ot_s81_cfg7_seq.sv rtl/v41die/ot_s81_cfg7_seq_bfp.sv rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v rtl/lib/ot_reset_sync.sv rtl/common/landed_parent/ot_pl_land.sv rtl/common/landed_parent/ot_pl_land_field_copies.sv rtl/common/landed_parent/ot_pl_land_reset_forest.sv rtl/common/landed_parent/ot_pl_seam.sv $DUT rtl/dsrom_sys/s81_dv/frame_lp/$TBD/tb_col_${M}_l4_lp.sv $(cat ${EXTRA_SRCS:-/dev/null} 2>/dev/null)"
for m in ${MUTS:-0 1 2 4}; do
  if [ "${SIM:-verilator}" = verilator ]; then
    ${VERILATOR:-verilator} --binary -j ${VL_JOBS:-8} -I. -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT -O1 \
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
