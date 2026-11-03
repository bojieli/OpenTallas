#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for c in TT FF; do
 OT_CORNER="$c" OT_POSTCTS_GRT=1 ODB=/work/sc_route_probe.odb openroad -exit /work/postcts_gate.tcl > "/work/sc_route_readout_${c}.log" 2>&1
done
python3 - <<'"'"'CHECK'"'"'
import json,math
from pathlib import Path
out={"scope":"READONLY_TT_FF_DIAGNOSTIC_ON_HONEST_ROUTE_ONLY_PLACE","cts_credit":False,"signed_credit":False,"corners":{}}
for c in ["tt","ff"]:
 d=json.loads(Path("/work/postcts_gate_"+c+".json").read_text())
 assert d["pinreg_n"]>0 and d["parasitics"]=="global_routing",d
 assert all(math.isfinite(d[k]) for k in ["pinreg_mean_ps","setup_wns_est_ps","hold_wns_est_ps"]),d
 out["corners"][c]=d
Path("/work/sc_route_timing_readout.json").write_text(json.dumps(out,indent=2)+"\n")
print("SC_REAL_ROUTE_TIMING_MEASUREMENTS_COMPLETE")
CHECK
' > readout.log 2>&1 || r=$?
printf '%s\n' "$r" > readout.rc
exit "$r"
