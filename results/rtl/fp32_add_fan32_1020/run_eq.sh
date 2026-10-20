#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../../.."
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
D=out_eq
mkdir -p "$D"
verilator --version > "$D/verilator.version"
verilator --binary --timing --top-module tb_fp32_add_fan32 -Wno-fatal -Wno-WIDTH -j 4 --Mdir "$D/obj" rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_fan32.sv rtl/test/hdc/tb_fp32_add_fan32.sv > "$D/build.log" 2>&1
"$D/obj/Vtb_fp32_add_fan32" > "$D/run.log" 2>&1
cat "$D/run.log"
