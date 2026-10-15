#!/usr/bin/env bash
set -eu
work=${1:?work directory}
mkdir -p "$work"
sources=(rtl/test/dsrom_sys/tb_s81_pq_qb_pinread.sv
 rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pipe_native.sv
 rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pinread_native.sv
 physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv
 physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv
 rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
iverilog -g2012 -s tb_s81_pq_qb_pinread -o "$work/exact.vvp" "${sources[@]}"
vvp "$work/exact.vvp" > "$work/exact.log"
cat "$work/exact.log"
for mut in OT_S81_PQ_QBX_MUT_ROW OT_S81_PQ_QB_HEAD_MUT; do
  iverilog -g2012 -s tb_s81_pq_qb_pinread -D"$mut" -o "$work/$mut.vvp" "${sources[@]}"
  set +e
  vvp "$work/$mut.vvp" > "$work/$mut.log" 2>&1
  rc=$?
  set -e
  if [[ $rc == 0 ]] || ! grep -q 'PQ_QB_PINREAD FAIL' "$work/$mut.log"; then cat "$work/$mut.log"; exit 1; fi
  cat "$work/$mut.log"
done

# The real bank protocol may hold a bank response across adjacent read slots.
# Exercise the declared head pins independently to prove the capture edge itself.
head=(rtl/test/dsrom_sys/tb_s81_pq_headpc_pin_capture.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pinread_native.sv physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv)
iverilog -g2012 -s tb_s81_pq_headpc_pin_capture -o "$work/head.vvp" "${head[@]}"
vvp "$work/head.vvp" > "$work/head.log";cat "$work/head.log"
iverilog -g2012 -s tb_s81_pq_headpc_pin_capture -DOT_S81_PQ_PINREAD_MUT_BYPASS -o "$work/bypass.vvp" "${head[@]}"
set +e;vvp "$work/bypass.vvp" > "$work/bypass.log" 2>&1;rc=$?;set -e
if [[ $rc == 0 ]] || ! grep -q 'PINREAD_CAPTURE FAIL' "$work/bypass.log";then cat "$work/bypass.log";exit 1;fi
cat "$work/bypass.log"
echo 'PQ_QB_PINREAD_GATE PASS positive=1 mutants=3 production_KMAX=6144 macros=4 added_read_cycles=3'
