#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
O=${1:?output}; variant=${2:-base}; mkdir -p "$O"
R=rtl/dsrom_sys/s81_ph
args=()
case "$variant" in base) ;; local)args+=(-DOT_VM_RETURN_BANK8_MUT_LOCAL);; *)exit 2;;esac
iverilog -g2012 "${args[@]}" -s tb_dsfd_vm_static_return_bank8 -o "$O/sim" "$R/vm/dsfd_vm_static_return.sv" "$R/vm/dsfd_vm_static_return_bank8.sv" "$R/vm/dsfd_vm_static_return32_lanes.sv" "$R/test/tb_dsfd_vm_static_return_bank8.sv"
vvp -n "$O/sim" +seed=1 > "$O/run.log"
cat "$O/run.log"
grep -q '^RETURN_BANK8 PASS$' "$O/run.log"
