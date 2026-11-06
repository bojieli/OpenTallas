#!/bin/bash
set -eu
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
R=/srv/opentallas-scratch2/claude/codex-kv-sd-pad-proof
cd "$R"
verilator --binary --timing -j 2 -Wno-fatal --top-module tb -DPAD=2 --Mdir "$R/obj" "$R/ot_dp_clk_landing_ca.sv" "$R/tb.sv" -o sim > build.log 2>&1
"$R/obj/sim" > proof.log 2>&1
verilator --binary --timing -j 2 -Wno-fatal --top-module tb -DPAD=1 --Mdir "$R/mutobj" "$R/ot_dp_clk_landing_ca.sv" "$R/tb.sv" -o sim > mutant_build.log 2>&1
ulimit -c 0
if "$R/mutobj/sim" > mutant.log 2>&1; then echo MUTANT_SURVIVED;exit 2;fi
cat proof.log
echo PAD1_MUTANT_CAUGHT
