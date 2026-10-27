#!/bin/bash
set -eu
src=$(git rev-parse --show-toplevel)
out=${1:?scratchout}
mkdir -p "$out"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
iverilog -g2012 -s tb_quarter_reset -o "$out/sim" "$src/results/hbm_quarter_reset_codex/tb_quarter_reset.sv" "$src/rtl/lib/ot_rst_relay.sv" "$src/rtl/lib/ot_rst_delivered3.sv"
vvp "$out/sim" > "$out/positive.log"
if vvp "$out/sim" +MUT_EARLY > "$out/mutant.log";then echo MUTANT_ESCAPED;exit 1;else echo MUTANT_CAUGHT;fi
cat "$out/positive.log"
