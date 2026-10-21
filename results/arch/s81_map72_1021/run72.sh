#!/bin/bash
# Actual capacity implementation campaign; all heavy work runs via ot-run.
set -uo pipefail
cd "$(dirname "$0")"
export OT_SVCPLAN_DROPFC=1R,3R,4L,6L OT_SVCPLAN_ROW0=1
export OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1
export OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 OT_XS_GU_PROP=1
export OT_XS_Q_CPR=1 OT_S81_CAP5_C=1
export PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH OT_XS_DENSE_SPLIT2 OT_XS_DENSE_SPLIT2_ROWS
if [ "$1" = probe ]; then
  python3 mk_probe.py 224 probe_f72r224gpq.json
  python3 capacity72.py run --spec probe_f72r224gpq.json --fixtures-root fixtures --die-src dieref --out out/probe_f72r224gpq --jobs 16 --dedup > probe_f72r224gpq.log 2>&1
  rc=$?; echo "PROBE_RC $rc" >> probe_f72r224gpq.log
else
  python3 capacity72.py run --spec "$1" --fixtures-root fixtures --die-src dieref --out "out/$2" --jobs 16 --dedup --expect pass > "$2.exact.log" 2>&1
  rc=$?; echo "EXACT_RC $rc" >> "$2.exact.log"
fi
exit "$rc"
