#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-astk-0828/$1/kit
docker run --rm --name codex-kv-0828-$1-lec --cpus 8 --memory 48g --memory-swap 48g -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
N=$(ls /work/run/results/asap7/*/base/1_2_yosys.v | head -1)
python3 -I /work/lec.py /work --netlist "$N" --out /work/lec > /work/lec_run.log 2>&1
'
