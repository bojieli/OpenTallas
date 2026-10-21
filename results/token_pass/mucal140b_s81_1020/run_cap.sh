#!/bin/bash
# S81-MUCAL140B: exact allocator capacity of the rebalanced 140-stage map (same root/fixtures/env as f122_140)
set -uo pipefail
D=/srv/opentallas-scratch/claude/s81-mucal140b; R=/srv/opentallas-scratch/claude/codex-s81-stage124-1020/root
export OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH
FIX=/srv/opentallas-scratch/claude/s81-calpipe/fixtures; DIE=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
cd $R; rc=0
python3 tools/s81_dv/layer_prog/xs_capacity.py run --spec $D/specs_rb140.json --fixtures-root $FIX --die-src $DIE --out $D/out/rb140 --jobs 24 --dedup --expect pass > $D/rb140.exact.log 2>&1 || rc=$?
echo "EXACT_RC $rc" >> $D/rb140.exact.log
python3 tools/s81_dv/layer_prog/xs_stage_map.py merge --map $D/stage_map_rb140.json --runs $D/out/rb140/summary.json --out $D/stage_map_rb140.merged.json > $D/rb140.merge.log 2>&1 || true
tail -1 $D/rb140.merge.log
