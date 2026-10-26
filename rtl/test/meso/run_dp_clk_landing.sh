#!/bin/bash
# Invoke through ot-run. OUT is an owned scratch directory; no repo outputs.
set -eu
repo=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
out=${1:?usage: run_dp_clk_landing.sh OUT}
mkdir -p "$out"
cp "$repo/rtl/common/ot_meso_fifo.sv" "$repo/rtl/common/ot_dp_clk_landing.sv" "$out/"
cp "$repo/rtl/test/meso/tb_dp_clk_landing.sv" "$repo/rtl/test/meso/tb_dp_clk_landing.cpp" "$out/"
cd "$out"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --cc --exe --build -j 4 -Wno-fatal --top-module tb_dp_clk_landing \
    tb_dp_clk_landing.sv ot_dp_clk_landing.sv ot_meso_fifo.sv tb_dp_clk_landing.cpp --Mdir obj > build.log 2>&1
for phase in 0 83 208 416 625 750; do obj/Vtb_dp_clk_landing "$phase"; done
verilator --cc --exe --build -j 4 -Wno-fatal -DOT_MESO_MUTANT_OFFSET --top-module tb_dp_clk_landing \
    tb_dp_clk_landing.sv ot_dp_clk_landing.sv ot_meso_fifo.sv tb_dp_clk_landing.cpp --Mdir obj_mut > build_mut.log 2>&1
if obj_mut/Vtb_dp_clk_landing 0; then echo MUTANT_SURVIVED; exit 1; else echo MUTANT_CAUGHT; fi
