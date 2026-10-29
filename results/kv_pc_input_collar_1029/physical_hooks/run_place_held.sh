#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-pc-collar-1029/kits/pc_place1
# Gate is copied only after terminal ordinary mapped RTL/netlist proof PASS.
python3 - "$K/lec_admission.json" <<'PYGATE'
import json,sys
x=json.load(open(sys.argv[1]))
assert x.get('ordinary_mapped_lec')=='PASS'
assert x.get('review_scope')=='ONE_PLACE_ONLY'
PYGATE
sudo docker run --rm --cpus=8 --memory=32g --memory-swap=32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8 place' > "$K/place_only.log" 2>&1
