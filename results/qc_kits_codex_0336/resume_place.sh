#!/bin/bash
set -euo pipefail
K=${1:?kit};MEM=${2:-48};CPUS=${3:-8}
python3 -I "$K/kit_preflight.py" "$K" --out "$K/physical_identity_preflight.json"
python3 - "$K/REUSE_NATIVE_EQ.json" <<'PY'
import sys,json
r=json.load(open(sys.argv[1]));assert r['old_files']==r['new_files']==10 and not r['different'] and r['same_pins'];assert r['native_compare_points']['differs']==0 and r['native_compare_points']['undecided']==0
PY
NAME=codex-collphy-place-$$
docker run --rm --name "$NAME" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -v "$K/fixed_macro_stage.tcl":/OpenROAD-flow-scripts/flow/scripts/macro_place.tcl:ro -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES='"$CPUS"' -o /work/run/results/asap7/dp_coll_ucie/base/1_2_yosys.v -o /work/run/results/asap7/dp_coll_ucie/base/1_2_yosys.sdc -o /work/run/results/asap7/dp_coll_ucie/base/1_synth.odb -o /work/run/results/asap7/dp_coll_ucie/base/1_synth.sdc place'
