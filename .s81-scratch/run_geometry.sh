#!/bin/bash
set -eu
R=/srv/opentallas-scratch2/scratch/claude/s81-rerun/v8j_c75bdf95f_min
D=$1
cd "$R/src"
export OT_S81_Q_LEF=results/rtl/dsrom_qz_20261004/Z20/Z20c/routed_element.lef.gz
ARGS=(--gen r8 --rev r9 --elem-h 198.72 --cc-reach-um 215 --vch-interleave --link-fix --corr-interleave --hop-fix --meso-d8 --cfifo-v2 --hc-xface --link-split --sel-xstg --geometry-fix --die "$D")
if [ "$D" != head ]; then ARGS+=(--pairs 2050); fi
# Guard keeps measured memory headroom; no time/size/virtual-memory limits.
python3 - <<'CHECK'
import os
m={k:int(v.split()[0]) for k,v in (s.split(':',1) for s in open('/proc/meminfo'))}
assert m['MemAvailable']/2**20 >= 8+max(32,m['MemTotal']/2**20*.1)
assert os.getloadavg()[0]+3 <= 384
CHECK
set +e
/srv/opentallas-scratch/admit.sh 8 -- python3 -u tools/dsrom_s81_geometry_gate.py "${ARGS[@]}" --source-commit c75bdf95f3ed52916df1eeda1e83ec2ec0c45430 --output "$R/$D" --emit-cases > "$R/$D.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$R/$D.rc"
exit "$rc"
