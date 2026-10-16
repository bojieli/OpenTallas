#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output};mode=${2:-gold};mkdir -p "$out"
defs=()
case "$mode" in
 gold);;
 serial)defs+=(-DCAP_FAULT_MUT_DROP_SERIAL);;
 core)defs+=(-DCAP_FAULT_MUT_DROP_CORE);;
 early)defs+=(-DCAP_FAULT_MUT_EARLY);;
 *)exit 2;;
esac
iverilog -g2012 "${defs[@]}" -s tb -o "$out/tb" tools/s81_vm/capture_fault_split_bench.sv \
 rtl/dsrom_sys/s81_ph/vm/dsfd_vm_capture_fault_serial.sv rtl/dsrom_sys/s81_ph/vm/dsfd_vm_native_valid_diag.sv \
 rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq_tile.sv rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq_static.sv
vvp "$out/tb"
