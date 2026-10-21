#!/bin/bash
# DRIVE-S81-SVCPLAN 10-20: full exact pinned capacity on the split112 / co-located 112-frame inventory (f92ee719) at N stages,
# then merge + table + static qualifier. Same env as LEAD9 run_req122.sh (PAIR_ROTATE 0).
set -uo pipefail
N=$1; D=$(cd "$(dirname "$0")" && pwd); cd "$D"
export OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH
FIX=/srv/opentallas-scratch/claude/s81-calpipe/fixtures; DIE=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
cp stage_map_${N}_MODELONLY.json stage_map_s112_$N.json
rc=0; python3 capacity112.py run --spec specs_$N.json --fixtures-root $FIX --die-src $DIE --out out/s112_$N --jobs 16 --dedup --expect pass > s112_$N.exact.log 2>&1 || rc=$?
echo "EXACT_RC $rc" >> s112_$N.exact.log
cd root; python3 tools/s81_dv/layer_prog/xs_stage_map.py merge --map ../stage_map_s112_$N.json --runs ../out/s112_$N/summary.json > ../s112_$N.merge.log 2>&1 || true
python3 tools/s81_dv/layer_prog/xs_stage_map.py table --map ../stage_map_s112_$N.json > ../stage_table_s112_$N.md || true
cd ..; python3 /srv/opentallas-scratch/claude/codex-s81-stage124-1020/qualify_static_n.py stage_map_s112_$N.json > s112_$N.qualify.log 2>&1 || true
tail -1 s112_$N.merge.log; tail -1 s112_$N.qualify.log
