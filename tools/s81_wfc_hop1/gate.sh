#!/bin/bash
# Exact A2F HOP1=1, READ_PIPE=4 WFC profile: RPE2 => RLAT15 / PAD2.
set -euo pipefail
OUT=$1;DEF=${2:-};mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
iverilog -g2012 ${DEF:+-D$DEF} -s tb_wfc_pipeline -Ptb_wfc_pipeline.RLAT=15 -Ptb_wfc_pipeline.PAD=2 -o "$OUT/pipeline15_2" "$V/dsfd_vm_static_wfc.sv" "$V/ot_s81_vm_fault_transports.sv" "$V/ot_s81_vm_x34.sv" "$V/ot_s81_vm_x43.sv" tools/s81_vm/wfc_pipeline_ref_r5.sv tools/s81_vm/wfc_pipeline_bench.sv
for seed in 1 2;do vvp -n "$OUT/pipeline15_2" +seed="$seed";done
iverilog -g2012 ${DEF:+-D$DEF} -s tb_wfc_fault_epoch -o "$OUT/fault_epoch" "$V/dsfd_vm_static_wfc.sv" "$V/ot_s81_vm_fault_transports.sv" "$V/ot_s81_vm_x34.sv" "$V/ot_s81_vm_x43.sv" tools/s81_vm/wfc_fault_epoch_bench.sv
vvp -n "$OUT/fault_epoch"
echo 'WFC_HOP1_PIPELINE_GATE PASS'
