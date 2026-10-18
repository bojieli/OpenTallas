#!/usr/bin/env bash
# HBMA-VMDEL 10-17: exact bench of the v6 vmdel lane (single clock root; plain pin flops on every input incl. rst_n,
# synchronous body reset from the rst_n pin flop; cross-lane status reduced after its pin flops; bank_id strap captured
# at its pin).  Interface LAT=2 / cross-lane STATUS_LAT=2 unchanged, 0 added cycles.
#  1. production delivery bench (tb_hbm_svc_static_vm_delivery, LAT=2 SLAT=2) on the split;
#  2. typed protocol lockstep vs the monolithic reference #(STATUS_LAT=2): control + dq metadata every cycle, all 256
#     payload bits on every valid beat (seeds 11, 23; 20k cycles, resets + protocol violations);
#  3. per-lane clock ownership (native wrapper, one clock per lane);
#  4. invalid-payload non-interference at the actual VM bank consumer (main 782dca30d policy).
#  The every-bit comparator (bench_delivery_split.sh) differs only in valid=0 payload after a reset asserted while a
#  lane is reading (synchronous reset: the SRAM read of the assertion edge is not cancelled); it is not the qualifier.
# MUT=1 group select swapped; 2 SRAM read slot corrupted; 3 body reset released one edge late; 4 status pin flops
# bypassed (STATUS_LAT 1); 5 all lanes on lane 0's clock.
set -euo pipefail
out=${1:?out}; mut=${2:-0}; cyc=${CYCLES:-20000}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sp=$d/split/ot_hbm_svc_static_vm_delivery_split.sv; np=$d/split/ot_hbm_svc_static_vm_delivery_split_native.sv
cp $sp "$out/split.sv"; cp $np "$out/native.sv"
case "$mut" in
 0) ;;
 1) sed -i 's/({256{out_group==2.d0}}&macro_data\[0+:256\])/({256{out_group==2\x27d0}}\&macro_data[256+:256])/' "$out/split.sv";;
 2) sed -i 's/\.r_addr_in({rb,rs})/.r_addr_in({rb,rs ^ 6\x27d1})/' "$out/split.sv";;
 3) sed -i 's/^  rst_s<=rst_n;/  rst_s<=rst_s2; rst_s2<=rst_n;/; s/^ reg rst_s;/ reg rst_s,rst_s2;/' "$out/split.sv";;
 4) sed -i 's/^ wire full0_q=.*/ wire full0_q=status_live \&\& (\&full0_all), full1_q=status_live \&\& (\&full1_all), pcbad_q=status_live \&\& (|pcbad_all);/' "$out/split.sv";;
 5) sed -i 's/clk_lane\[b\]/clk_lane[0]/g' "$out/native.sv";;
 *) exit 3;;
esac
if [ "$mut" != 0 ] && cmp -s "$out/split.sv" $sp && cmp -s "$out/native.sv" $np; then echo 'mutant not applied'; exit 3; fi
sed 's/module ot_hbm_svc_static_vm_delivery_split /module ot_hbm_svc_static_vm_delivery /' "$out/split.sv" > "$out/as_delivery.sv"
iverilog -g2012 -s tb_hbm_svc_static_vm_delivery -Ptb_hbm_svc_static_vm_delivery.LAT=2 -Ptb_hbm_svc_static_vm_delivery.SLAT=2 -o "$out/vm.vvp" "$mem" "$out/as_delivery.sv" $d/tb_hbm_svc_static_vm_delivery.sv
vvp "$out/vm.vvp" > "$out/vm.log" 2>&1 || { cat "$out/vm.log"; exit 1; }
cat "$out/vm.log"; grep -q 'STATIC_VM_DELIVERY PASS' "$out/vm.log"
iverilog -g2012 -s tb_hbm_svc_vmdel_v6_protocol_equiv -Ptb_hbm_svc_vmdel_v6_protocol_equiv.CYCLES=$cyc -Ptb_hbm_svc_vmdel_v6_protocol_equiv.LAT=2 -Ptb_hbm_svc_vmdel_v6_protocol_equiv.SLAT=2 -o "$out/eq.vvp" "$mem" $d/ot_hbm_svc_static_landing.sv $d/ot_hbm_svc_static_vm_delivery.sv "$out/split.sv" $d/split/tb_hbm_svc_vmdel_v6_protocol_equiv.sv
for s in 11 23; do vvp "$out/eq.vvp" +seed=$s > "$out/eq$s.log" 2>&1 || { tail -3 "$out/eq$s.log"; exit 1; }; cat "$out/eq$s.log"; grep -q 'V6_PROTOCOL PASS' "$out/eq$s.log"; done
iverilog -g2012 -s tb_hbm_svc_vmdel_v6_clock_ownership -o "$out/clock.vvp" "$mem" "$out/split.sv" "$out/native.sv" $d/split/tb_hbm_svc_vmdel_v6_clock_ownership.sv
vvp "$out/clock.vvp" > "$out/clock.log" 2>&1 || { cat "$out/clock.log"; exit 1; }
cat "$out/clock.log"; grep -q 'V6_CLOCK_OWNERSHIP PASS' "$out/clock.log"
bash tools/hbm_v15_harden/bench_vm_delivery_invalid_payload.sh "$out/inv" 0
echo "DELIVERY_V6_BENCH PASS mut=$mut"
