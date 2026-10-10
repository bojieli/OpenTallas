#!/bin/bash
# Smallest vehicle containing the BOOT_END drain and static-request checks.
set -euo pipefail
SRC=$1; OUT=$2
mkdir -p "$OUT"
iverilog -g2012 -s tb_s81_boot_visibility -o "$OUT/tb" \
  "$SRC/rtl/dsrom_sys/s81_ctrl/ot_s81_boot_seq.sv" \
  "$SRC/rtl/dsrom_sys/s81_ctrl/test/tb_s81_boot_visibility.sv"
vvp "$OUT/tb" | tee "$OUT/boot_visibility.log"
grep -q 'errors=0 PASS$' "$OUT/boot_visibility.log"
