#!/bin/bash
set -euo pipefail
r=0
docker run --rm --name codex-qc-l7-readout-0250 --cpus 2 --memory 16g --memory-swap 16g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for c in TT FF; do
 OT_CORNER="$c" OT_POSTCTS_GRT=1 ODB=/work/final_5_1_grt.odb openroad -exit /work/postcts_gate.tcl > "/work/final_grt_${c}.log" 2>&1
done
python3 - <<'"'"'CHECK'"'"'
import json,math
from pathlib import Path
out={"scope":"READONLY_ACTUAL_FINAL_5_1_GRT_TT_FF_DIAGNOSTIC","tool_family":"p-qc99172ad","source_qualified":False,"signed_credit":False,"DRT_credit":False,"corners":{}}
for c in ["tt","ff"]:
 d=json.loads(Path("/work/postcts_gate_"+c+".json").read_text())
 assert d["pinreg_n"]>0 and d["parasitics"]=="global_routing",d
 assert all(math.isfinite(d[k]) for k in ["pinreg_mean_ps","setup_wns_est_ps","hold_wns_est_ps"]),d
 out["corners"][c]=d
Path("/work/final_grt_timing_readout.json").write_text(json.dumps(out,indent=2)+"\n")
print("L7_ACTUAL_FINAL_GRT_TIMING_MEASUREMENTS_COMPLETE")
CHECK
' > readout.log 2>&1 || r=$?
printf '%s\n' "$r" > readout.rc
exit "$r"
