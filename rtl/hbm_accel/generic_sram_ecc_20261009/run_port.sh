#!/bin/bash
set -eu
out=$(readlink -m "$1");mkdir -p "$out"
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb_port -o "$out/port.vvp" rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv "$M" rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/generic_sram_ecc_20261009/tb_port.sv > "$out/build.log" 2>&1
/usr/bin/time -v vvp "$out/port.vvp" > "$out/port.log" 2> "$out/time.txt"
grep -q 'PAYLOAD_PORT PASS' "$out/port.log"
