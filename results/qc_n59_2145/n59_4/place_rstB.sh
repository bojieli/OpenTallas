#!/bin/bash
# PATH-QC-N59-4 place-only TRIAL (no CTS/route): current3 kit (codex/n59-2145@2df5f26ff, plan b1 54a1aeb5, same mapped
# FULL resynthesis with ot_rst_copies (n59_canon_rst.tcl): NOT covered by the running LEC; needs its own LEC before any adoption.
set -euo pipefail
R=/srv/opentallas-scratch2/claude/path-qc-n59-4/rstB
K=$R/kit
python3 - "$R" <<'VERIFY'
import hashlib,json,sys
from pathlib import Path
r=Path(sys.argv[1]);expected=json.load(open(r/'source_hashes.json'))
for n,h in expected.items():assert hashlib.sha256((r/'kit/rtl'/n).read_bytes()).hexdigest()==h,n
VERIFY
sudo docker run --rm --name pathqc-n59-4-rstB -v "$K:/work" openroad/orfs:latest bash -lc '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
 cd /OpenROAD-flow-scripts/flow
 python3 -I /work/adder_map_dontuse.py gen --platform-dir /OpenROAD-flow-scripts/flow/platforms/asap7 --out /work/adder_map_dontuse.v
 M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 REMOVE_ABC_BUFFERS=1"
 $M place
 '
# geometry collector (same Codex tool) right after DPL
cp /srv/opentallas-scratch2/claude/codex-n59-2145-current3/{geometry_cones.py,summarize_geometry.py,station_moves_v2.json} $R/
sudo docker run --rm -v "$R:/work" openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit -python /work/geometry_cones.py /work/kit/run/results/asap7/dp_native59/base/3_place.odb /work/all_geometry.json --all
python3 $R/summarize_geometry.py $R/all_geometry.json $R/station_moves_v2.json $R/all_geometry.summary.json
python3 /srv/opentallas-scratch2/claude/path-qc-n59-4/classify.py $R/all_geometry.json 30 > $R/classify.txt
