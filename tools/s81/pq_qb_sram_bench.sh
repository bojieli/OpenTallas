#!/usr/bin/env bash
set -eu
work=${1:?work directory}
mkdir -p "$work"
sources=(rtl/test/dsrom_sys/tb_s81_pq_qb_sram.sv
  rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_sram.sv
  physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv
  physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv
  rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
iverilog -g2012 -s tb_s81_pq_qb_sram -o "$work/exact.vvp" "${sources[@]}"
vvp "$work/exact.vvp" > "$work/exact.log"
cat "$work/exact.log"
iverilog -g2012 -s tb_s81_pq_qb_sram -DOT_S81_PQ_QB_MUT_ROW -o "$work/mut.vvp" "${sources[@]}"
set +e
vvp "$work/mut.vvp" > "$work/mut.log" 2>&1
rc=$?
set -e
if [[ $rc == 0 ]] || ! rg -q 'PQ_QB_SRAM FAIL' "$work/mut.log"; then cat "$work/mut.log"; exit 1; fi
cat "$work/mut.log"
echo 'PQ_QB_SRAM_GATE PASS positive=1 mutant_row=FAIL production_KMAX=6144 macros=4'
