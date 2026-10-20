#!/bin/bash
# Exact current allocator, pinned identical physical pair subsets, 124 TP4 stages.
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
cd "$D/root"
export OT_XS_QPAIRS=12 OT_XS_PAIR_ROTATE=0 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 OT_XS_PROP=1 OT_XS_CAL_SEGMENT=1 OT_XS_APROJ_TOPO=1 OT_XS_COMPACT_TAILS=0 OT_XS_KSLOT=1 PYTHONDONTWRITEBYTECODE=1
unset OT_XS_CAP_VDEPTH
mkdir -p "$D/out"
env | sort | sed -n '/^OT_XS_/p' > "$D/options.txt"
sha256sum tools/s81_dv/layer_prog/xs_{capacity,place,flags,stage_map}.py tools/s81_dv/layer_prog/lower_xs.py tools/v41_die_images_w17w10.py > "$D/source_hashes.txt"
FIX=/srv/opentallas-scratch/claude/s81-calpipe/fixtures
DIE=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref
python3 tools/s81_dv/layer_prog/xs_capacity.py run --spec "$D/probe_specs.json" --fixtures-root "$FIX" --die-src "$DIE" --out "$D/out/pinned_probe" --jobs 16 --dedup --expect pass > "$D/probe.log" 2>&1
python3 tools/s81_dv/layer_prog/xs_stage_map.py build --stages 124 --probe "$D/out/pinned_probe/summary.json" --out "$D/stage_map_124.json" --specs "$D/specs_124.json" --plan '124 pinned identical layouts, TP4, slope measured from actual nonrotating allocator' > "$D/map.log" 2>&1
python3 - "$D/stage_map_124.json" <<'CHECK'
import json,sys
m=json.load(open(sys.argv[1])); assert m['stages_count']==124,m['stages_count']
CHECK
python3 tools/s81_dv/layer_prog/xs_capacity.py run --spec "$D/specs_124.json" --fixtures-root "$FIX" --die-src "$DIE" --out "$D/out/map124" --jobs 16 --dedup --expect pass > "$D/exact.log" 2>&1
python3 tools/s81_dv/layer_prog/xs_stage_map.py merge --map "$D/stage_map_124.json" --runs "$D/out/map124/summary.json" > "$D/merge.log" 2>&1
python3 tools/s81_dv/layer_prog/xs_stage_map.py table --map "$D/stage_map_124.json" > "$D/stage_table_124.md"
echo 'PINNED124_EXACT_PASS (capacity only; MU calendar/chain and token path integration owed)'
