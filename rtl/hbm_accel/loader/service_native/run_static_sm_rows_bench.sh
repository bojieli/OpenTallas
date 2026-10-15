#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb_hbm_svc_static_sm_rows -o "$out/positive.vvp" "$mem" "$d/ot_hbm_svc_static_sm_rows.sv" "$d/tb_hbm_svc_static_sm_rows.sv"
vvp "$out/positive.vvp" > "$out/positive.log"
grep -q 'STATIC_SM_ROWS PASS' "$out/positive.log"
# Read a wrong row only in the fifth (scale) SRAM.
sed "s/\.r_addr_in(read_addr)/.r_addr_in(p==4 ? (read_addr ^ 7'd1) : read_addr)/" "$d/ot_hbm_svc_static_sm_rows.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_static_sm_rows.sv"; then echo 'mutant not applied';exit 1;fi
iverilog -g2012 -s tb_hbm_svc_static_sm_rows -o "$out/mutant.vvp" "$mem" "$out/mutant.sv" "$d/tb_hbm_svc_static_sm_rows.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log"; then echo 'mutant unexpectedly passed';exit 1;fi
grep -q 'row payload/tag mismatch' "$out/mutant.log"
cat "$out/positive.log"
echo 'STATIC_SM_ROWS_MUTANT rejected real fifth SRAM scale-address corruption'
