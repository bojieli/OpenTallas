#!/bin/bash
set -euo pipefail
out=$(realpath -m "$1"); width=${2:-280}; phase=${3:-61}; reverse=${4:-0}; mut=${5:-0}; mode=${6:-0}
mkdir -p "$out"
cd "$(dirname "$0")/../.."
iverilog -g2012 -s tb_sram_cdc -Ptb_sram_cdc.W="$width" -Ptb_sram_cdc.PHASE="$phase" -Ptb_sram_cdc.REVERSE="$reverse" -Ptb_sram_cdc.MUT="$mut" -Ptb_sram_cdc.MODE="$mode" -o "$out/sim.vvp" physical/hbm_native_sram_cdc_1014/tb_sram_cdc.sv physical/hbm_native_sram_cdc_1014/ot_hbm_native_sram_cdc.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
vvp -n "$out/sim.vvp" > "$out/simulation.log" 2>&1 || { cat "$out/simulation.log"; exit 1; }
cat "$out/simulation.log"
grep -q '^SRAM_CDC.*PASS' "$out/simulation.log"
