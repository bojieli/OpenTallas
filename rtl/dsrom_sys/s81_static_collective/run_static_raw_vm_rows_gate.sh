#!/usr/bin/env bash
set -euo pipefail
base=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(cd "$base/../../.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
src=("$base/s81_static_raw_vm_rows.sv" "$root/rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_bank128.sv" "$root/physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v")
verilator --lint-only -Wall --top-module s81_static_raw_vm_rows "${src[@]}"
iverilog -g2012 -s tb_s81_static_raw_vm_rows -o "$work/good" "${src[@]}" "$base/tb_s81_static_raw_vm_rows.sv"
vvp "$work/good"
iverilog -g2012 -s tb_s81_static_raw_vm_rows -Ptb_s81_static_raw_vm_rows.REGISTER_VM_WRITES=0 -o "$work/parent-pin" "${src[@]}" "$base/tb_s81_static_raw_vm_rows.sv"
vvp "$work/parent-pin"
echo 'PASS combinational bridge tuples plus parent final pin flop preserve exact write edge' 
iverilog -g2012 -s tb_s81_static_raw_vm_rows -Ptb_s81_static_raw_vm_rows.MUT=1 -o "$work/bad" "${src[@]}" "$base/tb_s81_static_raw_vm_rows.sv"
if vvp "$work/bad" > "$work/mutant.log" 2>&1;then echo 'FAIL actual stored-payload mutant survived';exit 1;fi
if ! grep -q 'actual SRAM553bit roundtrip record0' "$work/mutant.log";then cat "$work/mutant.log";exit 1;fi
cat "$work/mutant.log"
echo 'PASS actual DUT raw stored-payload bit mutant rejected'
sha256sum "${src[@]}" "$base/tb_s81_static_raw_vm_rows.sv"
