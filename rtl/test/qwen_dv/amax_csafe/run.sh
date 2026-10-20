#!/bin/bash
set -euo pipefail
source=${2:-generated/qfd_dv_amax_mu_csafe.sv}
out=$1
mkdir -p "$out"
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
for pair in 1:0 4:0 4:1 4:2 4:3 4:4 4:5; do
 nu=${pair%:*};mut=${pair#*:};tag=n${nu}m${mut}
 verilator --binary --timing -j 2 -Wno-fatal --top-module tb -GNU="$nu" -GMUT="$mut" --Mdir "$out/$tag" rtl/test/qwen_dv/amax_csafe/tb.sv rtl/qwen_dv/mu/qfd_dv_amax_mu.sv "$source" > "$out/$tag.build.log" 2>&1
 "$out/$tag/Vtb" > "$out/$tag.run.log" 2>&1
 cat "$out/$tag.run.log"
done
