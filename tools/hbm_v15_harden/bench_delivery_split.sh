#!/usr/bin/env bash
# Physical split of ot_hbm_svc_static_vm_delivery (ot_hbm_svc_vmdel_bank x8 + ot_hbm_svc_vmdel_ctl):
#  MUT=0: the production delivery bench run against the SPLIT (module renamed in a scratch copy) + lockstep
#         equivalence vs the monolithic module (every output bit, every cycle, legal + violating traffic);
#  MUT=1: bank-leaf group select swapped (groups 0/1); MUT=2: bank-leaf SRAM read slot corrupted. HBM-V15-HARDEN 10-15
set -euo pipefail
out=${1:?out}; mut=${2:-0}; cyc=${CYCLES:-4000}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
sp=$d/split/ot_hbm_svc_static_vm_delivery_split.sv
cp $sp "$out/split.sv"
case "$mut" in
 1) sed -i 's/({256{out_group==2.d0}}&macro_data\[0+:256\])/({256{out_group==2\x27d0}}\&macro_data[256+:256])/' "$out/split.sv";;
 2) sed -i 's/\.r_addr_in({rb,rs})/.r_addr_in({rb,rs ^ 6\x27d1})/' "$out/split.sv";;
esac
if [ "$mut" != 0 ]; then cmp -s "$out/split.sv" $sp && { echo 'mutant not applied'; exit 3; }; fi
sed 's/module ot_hbm_svc_static_vm_delivery_split /module ot_hbm_svc_static_vm_delivery /' "$out/split.sv" > "$out/as_delivery.sv"
iverilog -g2012 -s tb_hbm_svc_static_vm_delivery -o "$out/vm.vvp" "$mem" "$out/as_delivery.sv" $d/tb_hbm_svc_static_vm_delivery.sv
vvp "$out/vm.vvp" > "$out/vm.log" 2>&1 || { cat "$out/vm.log"; exit 1; }
cat "$out/vm.log"; grep -q 'STATIC_VM_DELIVERY PASS' "$out/vm.log"
iverilog -g2012 -s tb_hbm_svc_vmdel_split_equiv -Ptb_hbm_svc_vmdel_split_equiv.CYCLES=$cyc -o "$out/eq.vvp" "$mem" $d/ot_hbm_svc_static_landing.sv $d/ot_hbm_svc_static_vm_delivery.sv "$out/split.sv" $d/split/tb_hbm_svc_vmdel_split_equiv.sv
for s in 11 23; do vvp "$out/eq.vvp" +seed=$s > "$out/eq$s.log" 2>&1 || { tail -3 "$out/eq$s.log"; exit 1; }; cat "$out/eq$s.log"; grep -q 'SPLIT_EQUIV PASS' "$out/eq$s.log"; done
echo "DELIVERY_SPLIT_BENCH PASS mut=$mut"
