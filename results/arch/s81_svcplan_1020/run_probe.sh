#!/bin/bash
# usage: run_probe.sh DROPFC(e.g. 3R,4L) ROW0 TAG  (9 Codex probe specs on the column-reduced inventory; expect pass, failures recorded)
set -uo pipefail; cd "$(dirname "$0")"
export OT_SVCPLAN_DROPFC=$1 OT_SVCPLAN_ROW0=$2 OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH
python3 capacity_cols.py run --spec probes.json --fixtures-root /srv/opentallas-scratch/claude/s81-calpipe/fixtures --die-src /srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref --out out/probe_$3 --jobs 9 --dedup > probe_$3.log 2>&1; echo "PROBE_RC $?" >> probe_$3.log
