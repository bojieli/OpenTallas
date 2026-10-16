#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=$1; DEF=${2:-}; mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
for LAT in 13 15; do
 for SEED in 0 1 2 3; do
  iverilog -g2012 ${DEF:+-D$DEF} -s tb -Ptb.RLAT="$LAT" -Ptb.SEED="$SEED" -o "$OUT/sim_${LAT}_${SEED}" "$V/ot_s81_vm_x43.sv" "$V/ot_s81_vm_x34.sv" "$V/ot_s81_vm_fault_transports.sv" "$V/dsfd_vm_xio_request.sv" "$V/dsfd_vm_xio_return.sv" "$V/dsfd_vm_xio_serial.sv" "$V/dsfd_vm_xio_fault_join.sv" "$V/dsfd_vm_static_xio.sv" tools/s81_vm/xio_ref_legacy.sv tools/s81_vm/tb_xio_partition_0253.sv
  vvp -n "$OUT/sim_${LAT}_${SEED}"
 done
done
echo 'XIO_PARTITION_GATE PASS'
