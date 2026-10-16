#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output directory}; mode=${2:-gold}
mkdir -p "$out"
defs=()
case "$mode" in
  gold) ;;
  valid) defs+=(-DS81_NATIVE_DIAG_MUT_VALID);;
  slot) defs+=(-DS81_NATIVE_DIAG_MUT_SLOT);;
  drop) defs+=(-DS81_NATIVE_DIAG_MUT_DROP);;
  extra) defs+=(-DS81_NATIVE_DIAG_MUT_EXTRA);;
  *) exit 2;;
esac
iverilog -g2012 "${defs[@]}" -s tb -o "$out/tb" \
  tools/s81_vm/native_valid_diag_bench.sv \
  rtl/dsrom_sys/s81_ph/vm/dsfd_vm_native_valid_diag.sv \
  rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_suhc_return_map.sv
vvp "$out/tb"
