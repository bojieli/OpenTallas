#!/usr/bin/env bash
# Eight real related clock entries; pulse ownership + same-edge full output equivalence.
set -euo pipefail
out=${1:?output};mut=${2:-0};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
cp "$d/split/ot_hbm_svc_static_vm_delivery_split_native.sv" "$out/native.sv"
case "$mut" in
 0);;
 1) sed -i 's/clk_lane\[b\]/clk_lane[0]/g' "$out/native.sv";;
 2) sed -i 's/clk_lane\[b\]/clk_lane[(b+1)%8]/g' "$out/native.sv";;
 *) exit 3;;
esac
if [ "$mut" != 0 ];then ! cmp -s "$out/native.sv" "$d/split/ot_hbm_svc_static_vm_delivery_split_native.sv";fi
iverilog -g2012 -s tb_hbm_svc_vmdel_clock_ownership -o "$out/clock.vvp" "$mem" "$d/split/ot_hbm_svc_static_vm_delivery_split.sv" "$out/native.sv" "$d/split/tb_hbm_svc_vmdel_clock_ownership.sv"
vvp "$out/clock.vvp" > "$out/clock.log" 2>&1 || { cat "$out/clock.log";exit 1; }
cat "$out/clock.log";grep -q 'DELIVERY_CLOCK_OWNERSHIP PASS' "$out/clock.log"
# The native parent differs only in the clock ABI, so the complete prior equivalence bench runs with all eight
# related clocks coincident. Independent pulses above prove this is not a collapsed common-root implementation.
sed -e 's/ot_hbm_svc_static_vm_delivery_split dut(.clk(clk)/ot_hbm_svc_static_vm_delivery_split_native dut(.clk_lane({8{clk}})/' "$d/split/tb_hbm_svc_vmdel_split_equiv.sv" > "$out/eq.sv"
iverilog -g2012 -s tb_hbm_svc_vmdel_split_equiv -Ptb_hbm_svc_vmdel_split_equiv.CYCLES=20000 -Ptb_hbm_svc_vmdel_split_equiv.LAT=2 -o "$out/eq.vvp" "$mem" "$d/ot_hbm_svc_static_landing.sv" "$d/ot_hbm_svc_static_vm_delivery.sv" "$d/split/ot_hbm_svc_static_vm_delivery_split.sv" "$out/native.sv" "$out/eq.sv"
for seed in 11 23;do vvp "$out/eq.vvp" +seed=$seed > "$out/eq$seed.log" 2>&1;cat "$out/eq$seed.log";grep -q 'SPLIT_EQUIV PASS' "$out/eq$seed.log";done
echo DELIVERY_NATIVE_CLOCK_BENCH_PASS
