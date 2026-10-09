#!/bin/bash
set -euo pipefail
SRC=${SRC:-$(pwd)};OUT=$1;mkdir -p "$OUT"
S=("$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_vm_adapter.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_vm_read_share.sv"
 "$SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_vm_read_share.sv"
 "$SRC/rtl/dsrom_sys/s81_ph/vm/ot_s81ph_vm_mem.sv"
 "$SRC/physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v")
sha256sum "${S[@]}" > "$OUT/source.sha256"
iverilog -g2012 -s tb_s81_vm_read_share -o "$OUT/base.vvp" "${S[@]}" > "$OUT/build.log" 2>&1
for bad in 0 1 2;do vvp "$OUT/base.vvp" +bad=$bad > "$OUT/bad$bad.log" 2>&1;done
