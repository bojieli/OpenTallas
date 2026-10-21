#!/bin/bash
# LEAD9-S81 10-20: full exact capacity on the 122-frame dieref at N stages (pinned, no rotation), merge + table.
set -euo pipefail
N=$1; D=$(cd "$(dirname "$0")" && pwd); cd "$D"
export OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH
python3 mk_specs122.py $N > f122_$N.specs.log 2>&1
FIX=/srv/opentallas-scratch/claude/s81-calpipe/fixtures; DIE=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
cd root; rc=0
python3 tools/s81_dv/layer_prog/xs_capacity.py run --spec ../specs_f122_$N.json --fixtures-root $FIX --die-src $DIE --out ../out/f122_$N --jobs 16 --dedup --expect pass > ../f122_$N.exact.log 2>&1 || rc=$?
echo "EXACT_RC $rc" >> ../f122_$N.exact.log
python3 tools/s81_dv/layer_prog/xs_stage_map.py merge --map ../stage_map_f122_$N.json --runs ../out/f122_$N/summary.json > ../f122_$N.merge.log 2>&1 || true
python3 tools/s81_dv/layer_prog/xs_stage_map.py table --map ../stage_map_f122_$N.json > ../stage_table_f122_$N.md || true
tail -1 ../f122_$N.merge.log
