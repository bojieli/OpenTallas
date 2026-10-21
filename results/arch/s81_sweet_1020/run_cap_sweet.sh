#!/bin/bash
# S81-SWEET: exact allocator capacity of the specs of the two candidate maps (s141 re-deal, s153 + heavy x3) that no earlier
# exact run (f122_140/148, req201/212, rb140 incl. its pending specs) covers monotonically; same root/fixtures/env as rb140.
set -uo pipefail
D=/srv/opentallas-scratch/claude/s81-sweet; R=/srv/opentallas-scratch/claude/codex-s81-stage124-1020/root
export OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH
FIX=/srv/opentallas-scratch/claude/s81-calpipe/fixtures; DIE=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
cd $R; rc=0
python3 tools/s81_dv/layer_prog/xs_capacity.py run --spec $D/specs_exact_sweet.json --fixtures-root $FIX --die-src $DIE --out $D/out/sweet --jobs 6 --dedup --expect pass > $D/sweet.exact.log 2>&1 || rc=$?
echo "EXACT_RC $rc" >> $D/sweet.exact.log
