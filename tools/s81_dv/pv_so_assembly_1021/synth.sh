#!/usr/bin/env bash
set -euo pipefail
O=${1:?outdir};mkdir -p "$O"
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
cat > "$O/synth.ys" <<EOF
read_verilog -lib physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1_bb.v
read_verilog -sv -DSYNTHESIS rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_ingress.sv tools/s81_dv/pv_so_assembly_1021/cost_top.sv
hierarchy -top pvso_cost_top
synth -top pvso_cost_top -noabc
tee -o $O/stat.json stat -json
EOF
"$Y" -Q -T -s "$O/synth.ys" > "$O/synth.log" 2>&1
