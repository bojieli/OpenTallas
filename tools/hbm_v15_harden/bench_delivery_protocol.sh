#!/bin/bash
# Separate typed-protocol proof. Do not replace or relabel the historical
# every-bit comparator: its invalid-payload reset failure remains recorded.
set -euo pipefail
out=${1:?out};mut=${2:-0};lat=${LAT:-2};cyc=${CYCLES:-20000};mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
cp "$d/split/ot_hbm_svc_static_vm_delivery_split.sv" "$out/split.sv"
cp "$d/split/ot_hbm_svc_static_vm_delivery_split_native.sv" "$out/native.sv"
case "$mut" in
 0);;
 1) sed -i 's/({256{out_group==2.d0}}&macro_data\[0+:256\])/({256{out_group==2\x27d0}}\&macro_data[256+:256])/' "$out/split.sv";;
 2) sed -i 's/\.r_addr_in({rb,rs})/.r_addr_in({rb,rs ^ 6\x27d1})/' "$out/split.sv";;
 3) sed -i 's/clk_lane\[b\]/clk_lane[0]/g' "$out/native.sv";;
 4) sed -i 's/clk_lane\[b\]/clk_lane[(b+1)%8]/g' "$out/native.sv";;
 *)exit 3;;
esac
if [ "$mut" != 0 ];then
 if cmp -s "$out/split.sv" "$d/split/ot_hbm_svc_static_vm_delivery_split.sv" && cmp -s "$out/native.sv" "$d/split/ot_hbm_svc_static_vm_delivery_split_native.sv";then echo MUTANT_NOT_APPLIED;exit 3;fi
fi
iverilog -g2012 -s tb_hbm_svc_vmdel_clock_ownership -o "$out/clock.vvp" "$m" "$out/split.sv" "$out/native.sv" "$d/split/tb_hbm_svc_vmdel_clock_ownership.sv"
vvp "$out/clock.vvp" >"$out/clock.log" 2>&1 || { cat "$out/clock.log";exit 1; }
cat "$out/clock.log"
iverilog -g2012 -s tb_hbm_svc_vmdel_protocol_equiv -Ptb_hbm_svc_vmdel_protocol_equiv.CYCLES=$cyc -Ptb_hbm_svc_vmdel_protocol_equiv.LAT=$lat -o "$out/eq.vvp" "$m" "$d/ot_hbm_svc_static_landing.sv" "$d/ot_hbm_svc_static_vm_delivery.sv" "$out/split.sv" "$out/native.sv" "$d/split/tb_hbm_svc_vmdel_protocol_equiv.sv"
for seed in 11 23;do
 vvp "$out/eq.vvp" +seed=$seed >"$out/eq$seed.log" 2>&1 || { cat "$out/eq$seed.log";exit 1; }
 cat "$out/eq$seed.log"
 grep -q 'DELIVERY_PROTOCOL PASS' "$out/eq$seed.log"
done
echo DELIVERY_PROTOCOL_BENCH_PASS
