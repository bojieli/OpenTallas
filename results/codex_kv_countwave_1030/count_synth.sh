#!/bin/bash
set -euo pipefail
count_kit=$(pwd)
count_type=$(basename "$count_kit")
count_name="codex-count-${count_type}-$(date +%s)"
docker run --rm --name "$count_name" --memory=48g --cpus=8 -v "$count_kit:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl
python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json
count_design=$(sed -n "s/^export DESIGN_NICKNAME = //p" /work/config.mk)
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 "/work/run/results/asap7/$count_design/base/1_2_yosys.v"
echo COUNT_ONLY_SYNTH_COMPLETE
' > count_synth.log 2>&1
