#!/bin/bash
set -euo pipefail
SRC=${SRC:-$(pwd)};OUT=$1;mkdir -p "$OUT"
S=("$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_runtime_pc_lease64.sv" "$SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_runtime_pc_lease64.sv")
sha256sum "${S[@]}" > "$OUT/source.sha256"
iverilog -g2012 -s tb_s81_runtime_pc_lease64 -o "$OUT/base.vvp" "${S[@]}" > "$OUT/build.log" 2>&1
for bad in 0 1 2 3 4;do vvp "$OUT/base.vvp" +bad=$bad > "$OUT/bad$bad.log" 2>&1;done
