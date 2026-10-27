#!/bin/bash
# usage: run_build.sh TAG LATTICE   (CLOCK-KV-R15, intel1)
set -e; R=/srv/opentallas-scratch2/claude/clock-kv-r15-1026; cd $R
T=/srv/opentallas-scratch2/claude/wt/clock-kv-r15/tools/die_plan; export PYTHONPATH=$R/in/pylib:$T
python3 $T/die_clock_mesh.py build in/hm_r12.json --out $1 --nx 32 --ny 71 --m 2 --rep-um 450 --ndr 4w --max-move 500 --hop-max 600 --reserve-cell-sites --lattice-spec $2 --track-file $R/in/kit/grt/tracks.tcl --delta-id D-KV-CLK-R15 > $1.log 2>&1 || { tail -20 $1.log; exit 1; }
python3 -c "
import json;m=json.load(open(\"$1/mesh.json\"));mt=m[\"meta\"];print({k:mt[k] for k in (\"node_move_max_um\",\"htree_wire_mm\",\"mesh_wire_mm\",\"clock_hard_keepout_violations\",\"clock_cell_overlap_pairs\",\"strap_cover\") if k in mt}); print(\"unplaced\",len(m[\"unplaced\"]),m[\"unplaced\"][:3])"
python3 $R/in/census_pd.py in/hm_r12.json $1/mesh.json $T $1_census.json | head -1
