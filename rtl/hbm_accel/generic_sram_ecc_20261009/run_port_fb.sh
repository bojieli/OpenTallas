#!/bin/bash
# hardcore-1010 group B: ot_hcoll_port FALLBACK (FB 1, PAYLOAD_ECC 0) transaction-level bench (tb_port_fb.sv).
#   run_port_fb.sh <outdir> [MUTANT]   MUTANT: OT_HCOLL_FB_MUT_SLICE | OT_HCOLL_FB_MUT_CREDIT | OT_HCOLL_FB_MUT_BS (must FAIL)
set -u
out=$(readlink -m "$1"); mut=${2:-}; mkdir -p "$out"
M=physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
tag=${mut:-pos}
iverilog -g2012 ${mut:+-D$mut} -s tb_port_fb -o "$out/$tag.vvp" rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv "$M" \
  rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/generic_sram_ecc_20261009/tb_port_fb.sv \
  > "$out/$tag.build.log" 2>&1 || { echo "BUILD FAIL"; cat "$out/$tag.build.log"; exit 2; }
vvp -n "$out/$tag.vvp" > "$out/$tag.log" 2>&1; rc=$?
tail -4 "$out/$tag.log"
grep -q 'HCOLL_PORT_FB PASS' "$out/$tag.log" && [ $rc = 0 ] && exit 0
exit 1
