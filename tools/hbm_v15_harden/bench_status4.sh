#!/usr/bin/env bash
# status4 exact bench (MUT=0) or mutant (MUT=1: drop quadrant 3 from the error OR) -- HBM-V15-HARDEN 10-15
set -euo pipefail
out=${1:?out}; mut=${2:-0}; mkdir -p "$out"
d=rtl/hbm_accel/generic/vm/static
src=$d/ot_vms_status4_static.sv
if [ "$mut" = 1 ]; then sed 's/|pin_q\[75:73\]//' $src > "$out/mut.sv"; cmp -s "$out/mut.sv" $src && { echo 'mutant not applied'; exit 3; }; src=$out/mut.sv; fi
iverilog -g2012 -s tb_vms_status4_static -o "$out/sim.vvp" "$src" $d/tb_vms_status4_static.sv
vvp "$out/sim.vvp" | tee "$out/sim.log"
grep -q 'VMS_STATIC_STATUS4 PASS' "$out/sim.log"
