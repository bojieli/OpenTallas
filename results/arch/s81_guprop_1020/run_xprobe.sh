#!/bin/bash
# DRIVE-S81-GUPROP 10-20: expert-only actual-allocator capacity probes (DENSE2 run_probe.sh env, GU_PROP=1, the quantised
# GU_PROP placement of this branch).  usage: run_xprobe.sh DROPFC TAG
set -uo pipefail; cd "$(dirname "$0")"
export OT_SVCPLAN_DROPFC=$1 OT_SVCPLAN_ROW0=1 OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 OT_XS_GU_PROP=1 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH OT_XS_DENSE_SPLIT2 OT_XS_DENSE_SPLIT2_ROWS
python3 -c "import json; json.dump([dict(id=f'exp_n{n}', experts=n, dense_layer=None, dense_split2='X') for n in (1, 2, 3, 64)], open('xprobe_$2.json', 'w'), indent=1)"
python3 capacity_cols.py run --spec xprobe_$2.json --fixtures-root fixtures --die-src dieref --out out/xprobe_$2 --jobs 16 --dedup > xprobe_$2.log 2>&1; echo "PROBE_RC $?" >> xprobe_$2.log
tail -2 xprobe_$2.log
