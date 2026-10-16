#!/bin/bash
set -euo pipefail
OUT=$1;DEF=${2:-};mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
for cfg in '17 0' '14 3';do
 read -r L P <<< "$cfg"
 iverilog -g2012 ${DEF:+-D$DEF} -s tb_wfc_pipeline -Ptb_wfc_pipeline.RLAT="$L" -Ptb_wfc_pipeline.PAD="$P" -o "$OUT/sim_${L}_${P}" "$V/dsfd_vm_static_wfc.sv" "$V/ot_s81_vm_x34.sv" "$V/ot_s81_vm_x43.sv" tools/s81_vm/wfc_pipeline_ref_r5.sv tools/s81_vm/wfc_pipeline_bench.sv
 for seed in 1 2;do vvp -n "$OUT/sim_${L}_${P}" +seed="$seed";done
done
echo 'WFC_PIPELINE_GATE PASS'
