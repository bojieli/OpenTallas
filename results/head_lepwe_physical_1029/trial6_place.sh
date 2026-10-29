#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-head-lepwe/trial_v6
# Reuse the identical synthesized netlist; only the reviewed physical plan changes.
docker run --rm --name codex-lepwe-trial6-place --cpus=8 --memory=16g --memory-swap=16g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make -o /work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/3_2_place_iop.odb -o /work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/2_floorplan.odb -o /work/run/results/asap7/hbc_ot_s81hd_lep_pair/base/1_synth.odb DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place' > "$K/place.log" 2>&1
