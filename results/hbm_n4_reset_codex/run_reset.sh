#!/bin/bash
set -eu
wt=$(git rev-parse --show-toplevel)
out=${1:?scratchout}
mkdir -p "$out"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
iverilog -g2012 -s tb_reset -o "$out/sim" "$wt/results/hbm_n4_reset_codex/tb_reset.sv" "$wt/rtl/hbm_next/fused/ot_hnx_fused_tree.sv" "$wt/rtl/lib/ot_rst_relay.sv"
vvp "$out/sim" > "$out/positive.log"
if vvp "$out/sim" +MUT_EARLY > "$out/mutant.log"; then echo MUTANT_ESCAPED; exit 1; else echo MUTANT_CAUGHT; fi
cat "$out/positive.log"

