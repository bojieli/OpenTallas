#!/bin/bash
set -eu
k=/srv/opentallas-scratch2/claude/codex-qca0/kdif-v2
trap 'sudo chown -R "$(id -u):$(id -g)" "$k"' EXIT
"$HOME/.local/opentallas-tools/bin/verilator" --lint-only --top-module ot_kdif_miter -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-UNUSEDSIGNAL -Werror-WIDTH -Werror-SELRANGE "$k/kdif.sv" > "$k/lint.log" 2>&1
sudo docker run --rm --cpus 1 --memory 2g --memory-swap 2g -v "$k":/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
set -eu
yosys -p "read_verilog -sv kdif.sv; hierarchy -top ot_kdif_miter; prep -top ot_kdif_miter -flatten; opt; sat -verify -prove eq 1 -show-inputs" > formal_eq.log 2>&1
set +e
yosys -p "read_verilog -sv kdif.sv; chparam -set MUT 1 ot_kdif_miter; prep -top ot_kdif_miter -flatten; opt; sat -verify -prove eq 1 -show-inputs -dump_vcd mutant.vcd" > formal_mutant.log 2>&1
mr=$?
set -e
test "$mr" != 0
grep -q "proof did fail" formal_mutant.log
for n in reference candidate; do
 yosys -p "read_verilog -sv kdif.sv; hierarchy -top ot_kdif_$n; synth -top ot_kdif_$n; abc -g simple; clean; stat; ltp -noff" > mapped_$n.log 2>&1
done
' > "$k/run.log" 2>&1
