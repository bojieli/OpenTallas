#!/bin/bash
# Place-only structural prototype, while exact LEC runs on the same immutable
# mapped source/netlist in parallel. No CTS/route/adoption until both gates.
set -euo pipefail
R=/srv/opentallas-scratch2/claude/codex-n59-2145-density20
K=$R/kit
# Fresh gen's RTL exactly matches the completed corrected-input synthesis.
python3 - "$R" <<'VERIFY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]);expected=json.load(open(r/'source_hashes.json'))
for n,h in expected.items():assert hashlib.sha256((r/'kit/rtl'/n).read_bytes()).hexdigest()==h,n
VERIFY
sudo docker run --rm -v "$K:/work" openroad/orfs:latest bash -lc '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 cd /OpenROAD-flow-scripts/flow
 M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 REMOVE_ABC_BUFFERS=1"
 # Same RTL, mapped checkpoint and current-plan floorplan as current2.
 # Only the strict dr_o516 physical-name resolver changed after its recorded
 # missing-anchor failure. Preserve/reuse the completed floorplan checkpoint.
 $M -o /work/run/results/asap7/dp_native59/base/1_synth.odb place
 '
