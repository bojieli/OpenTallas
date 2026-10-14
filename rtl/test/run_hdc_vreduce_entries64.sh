#!/bin/bash
set -e
out=$1; kind=${2:-exact}
mkdir -p "$out"
extra=(); if [ "$kind" = mutant ]; then extra+=(-DOT_VRED_REGION_MUT);fi
iverilog -g2012 "${extra[@]}" -s tb_hdc_vreduce_entries64 -o "$out/bench.vvp" rtl/test/tb_hdc_vreduce_entries64.sv rtl/physical/ot_hdc_vreduce_entries64.sv rtl/hdc/ot_hdc_vreduce.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_delay.sv >"$out/compile.log" 2>&1
set +e
vvp "$out/bench.vvp" >"$out/run.log" 2>&1
rc=$?
cat "$out/run.log"
exit "$rc"
