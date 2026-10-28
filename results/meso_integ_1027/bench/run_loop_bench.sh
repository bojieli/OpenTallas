#!/bin/bash
# MESO-INTEG-1: lint the die-style count-aligned wiring and run the loop bench.  Usage: run_loop_bench.sh OUT [NSEED] [single|multi]
# multi (DIE-KV-3/CAORIGIN): regions with several landed partitions, one origin each + intra-region start relays.
set -eu
here=$(cd "$(dirname "$0")" && pwd); repo=$(git -C "$here" rev-parse --show-toplevel)
out=${1:?usage: run_loop_bench.sh OUT [NSEED] [single|multi] [mutant_noshift]}; mkdir -p "$out"; cd "$out"
python3 "$here/gen_loop.py" "$repo" . "${3:-single}" ${4:-}
cp "$repo"/rtl/common/{ot_meso_fifo.sv,ot_dp_clk_landing.sv,ot_dp_clk_landing_ca.sv} "$here/tb_ca_loop.cpp" .
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Wno-UNUSEDPARAM --top-module tb_ca_loop tb_ca_loop.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv > lint.log 2>&1 && echo "LINT clean" || { echo "LINT FAIL"; tail -20 lint.log; }
verilator --cc --exe --build -j 8 -Wno-fatal -Wno-lint --top-module tb_ca_loop tb_ca_loop.sv ot_dp_clk_landing_ca.sv ot_dp_clk_landing.sv ot_meso_fifo.sv tb_ca_loop.cpp --Mdir o_loop > build.log 2>&1
o_loop/Vtb_ca_loop "${2:-200}"
