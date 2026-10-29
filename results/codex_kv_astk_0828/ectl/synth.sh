#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-astk-0828/$1/kit
docker run --rm --name codex-kv-0828-$1-synth --cpus 8 --memory 48g --memory-swap 48g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/rtl_lint.py /work > /work/rtl_lint.log 2>&1
python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 synth > /work/synth.log 2>&1
N=$(ls /work/run/results/asap7/*/base/1_2_yosys.v | head -1)
python3 -I /work/core_preflight.py /work "$N" --out /work/face_guard.json > /work/face_guard.log 2>&1
'
