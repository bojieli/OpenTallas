#!/bin/bash
set -euo pipefail
K=$(pwd)/phys/slw_stm_v3
IMAGE=openroad/orfs:asap7lock
NAME=codex-stm-count-$$
printf "image %s %s start %s host %s\n" "$IMAGE" "$(docker image inspect --format "{{.Id}}" "$IMAGE")" "$(date -Is)" "$(hostname)" > "$K/count_image.txt"
rc=0
docker run --rm --name "$NAME" --cpus=2 --memory=16g --memory-swap=16g -v "$K":/work -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc 'set -e; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl; python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v --report /work/adder_map_dontuse.json; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 synth' > "$K/native_synth.log" 2>&1 || rc=$?
printf "end %s rc %s\n" "$(date -Is)" "$rc" >> "$K/count_image.txt"
exit "$rc"
