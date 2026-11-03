#!/bin/bash
set -euo pipefail
r=0
docker run --rm --cpus 1 --memory 8g --memory-swap 8g -v "$PWD":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc '
set -e
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
ODB=$(find /work/run/results/asap7 -path "*/base/4_cts.odb" -print -quit)
test -n "$ODB"
for c in TT FF; do
 OT_CORNER="$c" ODB="$ODB" openroad -exit /work/postcts_gate.tcl > "/work/postcts_native_${c}.log" 2>&1
done
python3 - <<'"'"'PY'"'"'
import json,math
from pathlib import Path
reports=[json.loads(Path("/work/postcts_gate_"+c+".json").read_text())for c in ["tt","ff"]]
for d in reports:
 assert d["pinreg_n"]>0 and d["verdict"]=="PASS",d
 assert all(math.isfinite(d[k])for k in ["pinreg_mean_ps","setup_wns_est_ps","hold_wns_est_ps"])
print("RED_NATIVE_CTS_READOUT_PASS")
PY
' > cts_readout.log 2>&1 || r=$?
printf '%s\n' "$r" > cts_readout.rc
exit "$r"
