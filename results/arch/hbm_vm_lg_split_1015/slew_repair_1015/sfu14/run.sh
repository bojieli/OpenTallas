#!/bin/bash
set -euo pipefail
base=/srv/opentallas-scratch/codex/lg-sfu14-slew-repair-1015
src=/srv/opentallas-scratch/codex/lg-sfu14-native-route-1015/src
export PATH="$src/../bin:$PATH"
docker run --rm -v "$src:/src:ro" -v "$base/work:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'trap "chmod -R a+rwX /work >/dev/null 2>&1 || true" EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts; python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 finish' > "$base/route.log" 2>&1
cd "$src"
python3 tools/w18/corner_sta_ref.py --orfs-dir "$base/work" --extra-sdc "$src/physical/ref_tile/vm_lg_bank_sfu14_static_1015/signoff.sdc" --output "$base/corner_sta.json" > "$base/corner_sta.log" 2>&1
python3 /tmp/check_lg_slew_upstream_1015.py "$base"
