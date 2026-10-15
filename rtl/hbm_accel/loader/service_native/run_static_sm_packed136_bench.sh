#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
ref=rtl/gpu/ot_gpu_payload_assemble.sv
iverilog -g2012 -s tb_hbm_svc_static_sm_packed136 -o "$out/positive.vvp" "$mem" "$ref" "$d/ot_hbm_svc_static_sm_packed136.sv" "$d/tb_hbm_svc_static_sm_packed136.sv"
vvp "$out/positive.vvp" > "$out/positive.log"
grep -q 'STATIC_SM_PACKED136 PASS' "$out/positive.log"
sed "s/record_phase\*64/record_phase*64+8/" "$d/ot_hbm_svc_static_sm_packed136.sv" > "$out/mutant.sv"
if cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_static_sm_packed136.sv";then echo 'mutant not applied';exit 1;fi
iverilog -g2012 -s tb_hbm_svc_static_sm_packed136 -o "$out/mutant.vvp" "$mem" "$ref" "$out/mutant.sv" "$d/tb_hbm_svc_static_sm_packed136.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log";then echo 'mutant unexpectedly passed';exit 1;fi
grep -q 'four-phase static gather differs\|packed136 cache payload/tag mismatch' "$out/mutant.log"
cat "$out/positive.log"
echo 'STATIC_SM_PACKED136_MUTANT rejected incorrect byte phase'
