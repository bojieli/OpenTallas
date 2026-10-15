#!/usr/bin/env bash
set -eu
work=${1:?work directory}
mkdir -p "$work"
sources=(rtl/test/dsrom_sys/tb_s81_pq_qb_pipe.sv
 rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pipe_native.sv
 physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv
 physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv
 rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
iverilog -g2012 -s tb_s81_pq_qb_pipe -o "$work/exact.vvp" "${sources[@]}"
vvp "$work/exact.vvp" > "$work/exact.log"
cat "$work/exact.log"
for mut in OT_S81_PQ_QBX_MUT_ROW OT_S81_PQ_QB_HEAD_MUT; do
  iverilog -g2012 -s tb_s81_pq_qb_pipe -D"$mut" -o "$work/$mut.vvp" "${sources[@]}"
  set +e
  vvp "$work/$mut.vvp" > "$work/$mut.log" 2>&1
  rc=$?
  set -e
  if [[ $rc == 0 ]] || ! grep -q 'PQ_QB_PIPE FAIL' "$work/$mut.log"; then cat "$work/$mut.log"; exit 1; fi
  cat "$work/$mut.log"
done
echo 'PQ_QB_PIPE_GATE PASS positive=1 mutants=2 production_KMAX=6144 macros=4 added_read_cycles=2'
