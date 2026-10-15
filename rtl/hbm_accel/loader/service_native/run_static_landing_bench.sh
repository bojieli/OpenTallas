#!/usr/bin/env bash
set -euo pipefail
out=${1:?output directory required}
mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
iverilog -g2012 -s tb_hbm_svc_static_landing -o "$out/positive.vvp" "$mem" "$d/ot_hbm_svc_static_landing.sv" "$d/tb_hbm_svc_static_landing.sv"
vvp "$out/positive.vvp" > "$out/positive.log"
grep -q 'STATIC_LANDING PASS' "$out/positive.log"
# Corrupt real SRAM read addresses; the same exact scoreboard must reject it.
sed 's/\.r_addr_in({rb,rs})/.r_addr_in({rb,rs ^ 6\x27d1})/' "$d/ot_hbm_svc_static_landing.sv" > "$out/mutant.sv"
cmp -s "$out/mutant.sv" "$d/ot_hbm_svc_static_landing.sv" && exit 1
iverilog -g2012 -s tb_hbm_svc_static_landing -o "$out/mutant.vvp" "$mem" "$out/mutant.sv" "$d/tb_hbm_svc_static_landing.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log"; then echo 'mutant unexpectedly passed';exit 1;fi
grep -q 'payload pc=' "$out/mutant.log"
cat "$out/positive.log"
echo 'STATIC_LANDING_MUTANT rejected real SRAM slot corruption'
