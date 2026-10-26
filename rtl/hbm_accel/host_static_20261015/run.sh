#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}
macro=${2:?real SRAM macro model}
mkdir -p "$out"
for mut in 0 1 2; do
  rows=4; [[ "$mut" != 0 ]] || rows=1024
  iverilog -g2012 -s tb_hbm_host_static_ingress -Ptb_hbm_host_static_ingress.MUT="$mut" -Ptb_hbm_host_static_ingress.ROWS="$rows" -o "$out/m$mut" rtl/hbm_accel/host_static_20261015/{ot_hbm_host_static_ingress,ot_hbm_program_block_ready,tb_hbm_host_static_ingress}.sv rtl/hbm_accel/generic/vm/static/{ot_static_program_target,ot_vms_calendar_static}.sv "$macro" > "$out/build$mut.log" 2>&1
  if vvp "$out/m$mut" > "$out/run$mut.log" 2>&1; then
    [[ "$mut" == 0 ]] || { cat "$out/run$mut.log"; exit 1; }
    grep -q '^HBM_HOST_STATIC_PASS' "$out/run$mut.log"
  else
    [[ "$mut" != 0 ]] || { cat "$out/run$mut.log"; exit 1; }
    if [[ "$mut" == 1 ]]; then grep -q 'HOST_STATIC data/ordinal mismatch' "$out/run$mut.log";
    else grep -q 'HOST_STATIC wrong AXI response 0 a=f30' "$out/run$mut.log"; fi
  fi
  cat "$out/run$mut.log"
done
iverilog -g2012 -s tb_hbm_host_static_ingress -Ptb_hbm_host_static_ingress.ROWS=4 -Ptb_hbm_host_static_ingress.READY_MUT=1 -o "$out/ready_mut" rtl/hbm_accel/host_static_20261015/{ot_hbm_host_static_ingress,ot_hbm_program_block_ready,tb_hbm_host_static_ingress}.sv rtl/hbm_accel/generic/vm/static/{ot_static_program_target,ot_vms_calendar_static}.sv "$macro" > "$out/build_ready_mut.log" 2>&1
if vvp "$out/ready_mut" > "$out/run_ready_mut.log" 2>&1; then exit 1; fi
grep -q 'HOST_STATIC unloaded range falsely ready' "$out/run_ready_mut.log"
cat "$out/run_ready_mut.log"
