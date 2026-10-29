#!/bin/bash
# Run through ot-run; requires the project Yosys/ABC toolchain in PATH.
set -euo pipefail
p=$(dirname "$(readlink -f "$0")")
out=${1:?usage: replay.sh NEW_OUTPUT_DIRECTORY}
mkdir -p "$out/inputs" "$out/proof" "$out/eqbase"
tar -xzf "$p/inputs.tar.gz" -C "$out/inputs"
export K13_INPUT="$out/inputs" K13_OUT="$out/proof" K13_EQOUT="$out/eqbase"
export K13_EQSTEPS=5 OT_LEC_RESET_CYCLES=64
python3 "$p/rest_target5.py" | tee "$out/proof.log"
python3 "$p/eqbase.py" | tee "$out/eqbase.log"
