#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory}; macro=${2:?SRAM model}; mut=${3:-0}; rmut=${4:-0}; rows=${5:-1024}
mkdir -p "$out"
iverilog -g2012 -s tb_hbm_host_static_ingress -Ptb_hbm_host_static_ingress.MUT="$mut" -Ptb_hbm_host_static_ingress.READY_MUT="$rmut" -Ptb_hbm_host_static_ingress.ROWS="$rows" -o "$out/sim" rtl/hbm_accel/host_static_20261015/{ot_hbm_host_static_ingress,ot_hbm_program_block_ready,tb_hbm_host_static_ingress}.sv rtl/hbm_accel/generic/vm/static/{ot_static_program_target,ot_vms_calendar_static}.sv "$macro" > "$out/build.log" 2>&1
vvp "$out/sim"
