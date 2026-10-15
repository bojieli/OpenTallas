#!/usr/bin/env bash
set -eu
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:-/tmp/qfd-up4-faces-bench}
mkdir -p "$out"
iverilog -g2012 -s tb -o "$out/positive.vvp" "$root/rtl/physical/ot_qwen_band_lanes_slots.sv" "$root/rtl/test/qwen_split/tb_qfd_upper_faces.sv"
vvp "$out/positive.vvp" > "$out/positive.log" 2>&1
iverilog -g2012 -s tb -DMUT=1 -o "$out/mutant.vvp" "$root/rtl/physical/ot_qwen_band_lanes_slots.sv" "$root/rtl/test/qwen_split/tb_qfd_upper_faces.sv"
if vvp "$out/mutant.vvp" > "$out/mutant.log" 2>&1; then
    echo 'UPPER_FACES MUTANT SURVIVED';exit 1
fi
cat "$out/positive.log"
echo 'UPPER_FACES fault-drop mutant rejected'
