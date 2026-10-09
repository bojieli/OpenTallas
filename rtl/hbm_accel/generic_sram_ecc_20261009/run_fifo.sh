#!/bin/bash
set -eu
out=$(readlink -m "$1"); mkdir -p "$out"
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb_fifo -o "$out/fifo.vvp" rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv "$M" rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/generic_sram_ecc_20261009/tb_fifo.sv > "$out/fifo.build.log" 2>&1
/usr/bin/time -v vvp "$out/fifo.vvp" > "$out/fifo.log" 2> "$out/fifo.time.txt"
grep -q 'PAYLOAD_FIFO PASS' "$out/fifo.log"
for mutant in OT_COLL_MUT_ECC_NO_CORRECT OT_COLL_MUT_ECC_UE_PUBLISH; do
 iverilog -g2012 -D"$mutant" -s tb_fifo -o "$out/$mutant.vvp" rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv "$M" rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/generic_sram_ecc_20261009/tb_fifo.sv > "$out/$mutant.build.log" 2>&1
 set +e; vvp "$out/$mutant.vvp" > "$out/$mutant.log" 2>&1; rc=$?; set -e
 [ "$rc" != 0 ]; grep -Eq 'FIFO corrupt CE|FIFO UE publication' "$out/$mutant.log"
 echo "$mutant failed as expected rc=$rc" >> "$out/mutants.txt"
done
