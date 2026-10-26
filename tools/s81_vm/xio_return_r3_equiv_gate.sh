#!/bin/bash
# r3 dsfd_vm_xio_return cycle identity vs frozen r2 (plain pin capture flops, rn qualification after the flop).
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=$1; DEF=${2:-}; mkdir -p "$OUT"
V=rtl/dsrom_sys/s81_ph/vm
for SEED in 1 2 3 4; do
 iverilog -g2012 ${DEF:+-D$DEF} -s tb -Ptb.SEED="$SEED" -o "$OUT/sim_$SEED" tools/s81_vm/xio_return_r2_ref.sv "$V/dsfd_vm_xio_return.sv" tools/s81_vm/tb_xio_return_r3_equiv.sv
 vvp -n "$OUT/sim_$SEED"
done
iverilog -g2012 ${DEF:+-D$DEF} -s tb -o "$OUT/sim_phase" "$V/dsfd_vm_xio_return.sv" tools/s81_vm/tb_xio_return_phase_0253.sv
vvp -n "$OUT/sim_phase"
echo 'XIO_RETURN_R3_EQUIV_GATE PASS'
