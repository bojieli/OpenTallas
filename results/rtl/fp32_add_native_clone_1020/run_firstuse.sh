#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
G=$PWD/graph; A=results/rtl/fp32_add_native_clone_1020
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
mkdir -p "$G/first_use"
sha256sum "$G/cells.v" "$G/native.v" "$A/first_use_tb.sv" > "$G/first_use/identity.sha256"
"$VL" --binary --timing --x-initial unique --x-assign unique -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_fp32_add_fan32_firstuse -Mdir "$G/first_use/obj" -o sim "$G/native.v" "$G/cells.v" "$A/wrapper.sv" rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv "$A/first_use_tb.sv" > "$G/first_use/build.log" 2>&1
for seed in 1 2 3 15 51; do
 "$G/first_use/obj/sim" +verilator+rand+reset+2 +verilator+seed+$seed > "$G/first_use/seed$seed.log" 2>&1
 tail -3 "$G/first_use/seed$seed.log"
done
