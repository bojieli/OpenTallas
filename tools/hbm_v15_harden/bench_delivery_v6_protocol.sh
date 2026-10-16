#!/bin/bash
# Additive typed-contract proof; preserves every-bit historical failure receipts.
set -euo pipefail
out=${1:?out}; mut=${2:-0}; cyc=${CYCLES:-20000}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
m=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
cp "$d/split/ot_hbm_svc_static_vm_delivery_split.sv" "$out/split.sv"
cp "$d/split/ot_hbm_svc_static_vm_delivery_split_native.sv" "$out/native.sv"
case "$mut" in
 0);;
 1) sed -i 's/({256{out_group==2.d0}}&macro_data\[0+:256\])/({256{out_group==2\x27d0}}\&macro_data[256+:256])/' "$out/split.sv";;
 2) sed -i 's/\.r_addr_in({rb,rs})/.r_addr_in({rb,rs ^ 6\x27d1})/' "$out/split.sv";;
 3) sed -i 's/^  rst_s<=rst_n;/  rst_s<=rst_s2; rst_s2<=rst_n;/; s/^ reg rst_s;/ reg rst_s,rst_s2;/' "$out/split.sv";;
 4) sed -i 's/^ wire full0_q=.*/ wire full0_q=status_live \&\& (\&full0_all), full1_q=status_live \&\& (\&full1_all), pcbad_q=status_live \&\& (|pcbad_all);/' "$out/split.sv";;
 5) sed -i 's/\.clk_cap(clk_lane\[b\])/.clk_cap(1\x27b0)/' "$out/native.sv";;
 6) sed -i 's/\.clk(clk_lane\[b\])/.clk(1\x27b0)/' "$out/native.sv";;
 7) sed -i 's/\.clk_cap(clk_lane\[b\])/.clk_cap(clk_lane[(b+1)%8])/' "$out/native.sv";;
 *) exit 3;;
esac
if [ "$mut" != 0 ];then
 if cmp -s "$out/split.sv" "$d/split/ot_hbm_svc_static_vm_delivery_split.sv" && cmp -s "$out/native.sv" "$d/split/ot_hbm_svc_static_vm_delivery_split_native.sv";then echo MUTANT_NOT_APPLIED;exit 3;fi
fi
iverilog -g2012 -s tb_hbm_svc_vmdel_v6_clock_ownership -o "$out/clock.vvp" "$m" "$out/split.sv" "$out/native.sv" "$d/split/tb_hbm_svc_vmdel_v6_clock_ownership.sv" > "$out/clock.build.log" 2>&1
vvp "$out/clock.vvp" > "$out/clock.log" 2>&1 || { cat "$out/clock.log";exit 1; }
cat "$out/clock.log"
iverilog -g2012 -s tb_hbm_svc_vmdel_v6_protocol_equiv -Ptb_hbm_svc_vmdel_v6_protocol_equiv.CYCLES="$cyc" -Ptb_hbm_svc_vmdel_v6_protocol_equiv.LAT=2 -Ptb_hbm_svc_vmdel_v6_protocol_equiv.SLAT=2 -o "$out/protocol.vvp" "$m" "$d/ot_hbm_svc_static_landing.sv" "$d/ot_hbm_svc_static_vm_delivery.sv" "$out/split.sv" "$d/split/tb_hbm_svc_vmdel_v6_protocol_equiv.sv" > "$out/protocol.build.log" 2>&1
for seed in 11 23;do
 vvp "$out/protocol.vvp" +seed="$seed" > "$out/protocol$seed.log" 2>&1 || { cat "$out/protocol$seed.log";exit 1; }
 cat "$out/protocol$seed.log";grep -q 'V6_PROTOCOL PASS' "$out/protocol$seed.log"
done
echo "DELIVERY_V6_PROTOCOL_GATE PASS mutant=$mut"
