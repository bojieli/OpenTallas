#!/bin/bash
# DENSE2 10-20: actual-allocator probes on the column-reduced inventory.  usage: run_probe.sh DROPFC ROW0 R TAG [COMPACT_TAILS(0) [GU_PROP(0)]]
#   98 frames = DROPFC 3R,4L ROW0 1 ; 84 frames = DROPFC 1R,3R,4L,6L ROW0 1  (SVCPLAN capacity_cols.py inventories)
set -uo pipefail; cd "$(dirname "$0")"
export OT_SVCPLAN_DROPFC=$1 OT_SVCPLAN_ROW0=$2 OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=${5:-0} OT_XS_KSLOT=1 OT_XS_GU_PROP=${6:-0} PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH OT_XS_DENSE_SPLIT2 OT_XS_DENSE_SPLIT2_ROWS
python3 mk_probe.py $3 probe_$4.json
python3 capacity_cols.py run --spec probe_$4.json --fixtures-root fixtures --die-src dieref --out out/probe_$4 --jobs 16 --dedup > probe_$4.log 2>&1; echo "PROBE_RC $?" >> probe_$4.log
tail -2 probe_$4.log
