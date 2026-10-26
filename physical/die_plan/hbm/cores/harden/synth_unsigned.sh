#!/bin/bash
# CORE-HBM-OTHER: synth; if OpenSTA rejects 'input signed' port decls in 1_2_yosys.v (STA-0171), drop the port signedness
# (no effect on the gate netlist) and resume the 1_synth.odb step.
K=$1; MEM=${2:-16}; D=$(cd "$(dirname "$0")" && pwd)
bash $D/run_kit.sh "$K" synth $MEM 8 && exit 0
f=$(ls "$K"/run/results/asap7/*/base/1_2_yosys.v) || exit 3
sed -i -E 's/^(\s*(input|output|wire)) signed /\1 /' "$f"
bash $D/run_kit.sh "$K" synth $MEM 8
