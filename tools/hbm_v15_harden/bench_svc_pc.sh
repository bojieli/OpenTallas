#!/usr/bin/env bash
# ot_hbm_svc_static_pc exact bench, or mutant (physical SRAM read slot corrupted) -- HBM-V15-HARDEN 10-15
set -euo pipefail
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
mem=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
src=$d/ot_hbm_svc_static_pc.sv
if [ "$mut" = 1 ]; then
  sed 's/{bank_q,slot_q}:{read_bank,read_slot}/{bank_q,slot_q ^ 6\x27d1}:{read_bank,read_slot ^ 6\x27d1}/' $src > "$out/mut.sv"
  cmp -s "$out/mut.sv" $src && { echo 'mutant not applied'; exit 3; }; src=$out/mut.sv
fi
iverilog -g2012 -s tb_hbm_svc_static_pc -o "$out/sim.vvp" "$mem" "$src" $d/tb_hbm_svc_static_pc.sv
vvp "$out/sim.vvp" > "$out/sim.log" 2>&1 || { cat "$out/sim.log"; exit 1; }
cat "$out/sim.log"; grep -q 'STATIC_PC PASS' "$out/sim.log"
