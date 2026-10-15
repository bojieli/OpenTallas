#!/usr/bin/env bash
# ot_hbm_svc_static_vm_delivery exact bench (landing scoreboard + VM delivery), or one mutant:
# MUT=1 bank/group permutation of the read mux, MUT=2 real SRAM read slot corruption -- HBM-V15-HARDEN 10-15
set -euo pipefail
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
land=$d/ot_hbm_svc_static_landing.sv
case "$mut" in
 1) sed 's/(out_group\*8+b)/(out_group*8+(b ^ 1))/' $land > "$out/mut.sv";;
 2) sed 's/\.r_addr_in({rb,rs})/.r_addr_in({rb,rs ^ 6\x27d1})/' $land > "$out/mut.sv";;
esac
if [ "$mut" != 0 ]; then cmp -s "$out/mut.sv" $land && { echo 'mutant not applied'; exit 3; }; land=$out/mut.sv; fi
if [ "$mut" = 0 ]; then
  iverilog -g2012 -s tb_hbm_svc_static_landing -o "$out/land.vvp" "$mem" $land $d/tb_hbm_svc_static_landing.sv
  vvp "$out/land.vvp" > "$out/land.log" 2>&1 || { cat "$out/land.log"; exit 1; }
  cat "$out/land.log"; grep -q 'STATIC_LANDING PASS' "$out/land.log"
fi
iverilog -g2012 -s tb_hbm_svc_static_vm_delivery -o "$out/vm.vvp" "$mem" $land $d/ot_hbm_svc_static_vm_delivery.sv $d/tb_hbm_svc_static_vm_delivery.sv
vvp "$out/vm.vvp" > "$out/vm.log" 2>&1 || { cat "$out/vm.log"; exit 1; }
cat "$out/vm.log"; grep -q 'STATIC_VM_DELIVERY PASS' "$out/vm.log"
