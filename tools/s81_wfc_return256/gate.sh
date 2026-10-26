#!/bin/bash
set -euo pipefail
OUT=$1;DEF=${2:-};mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
iverilog -g2012 ${DEF:+-D$DEF} -s tb_return256 -o "$OUT/sim" "$V/dsfd_vm_static_wfc.sv" "$V/dsfd_vm_wfc_return256.sv" "$V/dsfd_vm_native_valid_diag.sv" tools/s81_wfc_return256/bench.sv
for seed in ${SEEDS:-1 2 3};do vvp -n "$OUT/sim" +seed="$seed";done
