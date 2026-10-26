#!/bin/bash
# DENSE2 10-20: exact pinned capacity of one spec chunk of a split map on the column-reduced inventory.
# usage: run_cap.sh DROPFC ROW0 SPECS OUTNAME [COMPACT_TAILS(0) [GU_PROP(0)]]
set -uo pipefail; cd "$(dirname "$0")"
export OT_SVCPLAN_DROPFC=$1 OT_SVCPLAN_ROW0=$2 OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=${5:-0} OT_XS_KSLOT=1 OT_XS_GU_PROP=${6:-0} PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH OT_XS_DENSE_SPLIT2 OT_XS_DENSE_SPLIT2_ROWS
python3 capacity_cols.py run --spec $3 --fixtures-root fixtures --die-src dieref --out out/$4 --jobs 16 --dedup --expect pass > $4.exact.log 2>&1; echo "EXACT_RC $?" >> $4.exact.log
tail -1 $4.exact.log
