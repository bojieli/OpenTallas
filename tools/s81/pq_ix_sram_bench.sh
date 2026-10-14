#!/usr/bin/env bash
set -eu
work=${1:?work directory}
mkdir -p "$work"
sources=(rtl/test/dsrom_sys/tb_s81_pq_ix_sram.sv
  rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ix_sram.sv
  physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv
  physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv
  rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv
  physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
for par in 0 1; do
  iverilog -g2012 -s tb_s81_pq_ix_sram -Ptb_s81_pq_ix_sram.PAR="$par" -o "$work/par$par.vvp" "${sources[@]}"
  vvp "$work/par$par.vvp" > "$work/par$par.log"
  cat "$work/par$par.log"
done
iverilog -g2012 -s tb_s81_pq_ix_sram -DOT_S81_PQ_IX_MUT_ROW -o "$work/mut.vvp" "${sources[@]}"
set +e
vvp "$work/mut.vvp" > "$work/mut.log" 2>&1
rc=$?
set -e
if [[ $rc == 0 ]] || ! grep -q 'PQ_IX_SRAM FAIL' "$work/mut.log"; then
  cat "$work/mut.log"
  exit 1
fi
cat "$work/mut.log"
echo 'PQ_IX_SRAM_GATE PASS positive=2 mutant_row=FAIL production_KMAX=6144 macros_per_tile=8'
