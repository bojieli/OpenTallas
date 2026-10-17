#!/bin/bash
set -euo pipefail
OUT=$1;DEF=${2:-};mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
iverilog -g2012 ${DEF:+-D$DEF} -s tb_seq_hf -o "$OUT/sim" "$V/dsfd_vm_seq_static.sv" "$V/dsfd_vm_seq_tile.sv" tools/s81_seq_hf/ref3.sv tools/s81_seq_hf/bench.sv
for seed in ${SEEDS:-1 2 3};do vvp -n "$OUT/sim" +seed="$seed";done
