#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb_hbm_svc_static_pc -o "$out/positive.vvp" "$mem" "$d/ot_hbm_svc_static_pc.sv" "$d/tb_hbm_svc_static_pc.sv"
vvp "$out/positive.vvp" > "$out/positive.log"
grep -q 'STATIC_PC PASS' "$out/positive.log"
# Corrupt the physical SRAM read slot, including writeback reads.
sed 's/{bank_q,slot_q}:{read_bank,read_slot}/{bank_q,slot_q ^ 6\x27d1}:{read_bank,read_slot ^ 6\x27d1}/' "$d/ot_hbm_svc_static_pc.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_static_pc.sv"; then echo 'mutant not applied';exit 1;fi
iverilog -g2012 -s tb_hbm_svc_static_pc -o "$out/mutant.vvp" "$mem" "$out/mutant.sv" "$d/tb_hbm_svc_static_pc.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log"; then echo 'mutant unexpectedly passed';exit 1;fi
grep -q 'payload read mismatch' "$out/mutant.log"
cat "$out/positive.log"
echo 'STATIC_PC_MUTANT rejected real SRAM read slot corruption'
