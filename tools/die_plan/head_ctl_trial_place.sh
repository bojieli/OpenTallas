#!/bin/bash
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-head-ctl-2249
K=$R/hd_ctl
docker run --rm --name codex-head-ctl-place-2249 --memory=48g --memory-swap=48g --cpus=8 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 -I /work/native_bb.py /OpenROAD-flow-scripts/flow/scripts/synth_preamble.tcl --physical-synth /OpenROAD-flow-scripts/flow/scripts/synth.tcl; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place" > "$R/place.log" 2>&1
