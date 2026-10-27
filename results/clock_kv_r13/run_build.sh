#!/bin/bash
# usage: run_build.sh TAG LATTICE
set -e; R=/srv/opentallas-scratch2/claude/clock-kv-r13-1026; cd $R
T=/srv/opentallas-scratch2/claude/wt/clock-kv-r13/tools/die_plan; export PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib:$T
python3 $T/die_clock_mesh.py build plan_r12.json --out $1 --nx 32 --ny 71 --m 2 --rep-um 450 --ndr 4w --max-move 500 --hop-max 600 --reserve-cell-sites --lattice-spec $2 --track-file /srv/opentallas-scratch2/claude/codex-kv-mesh-1026/kit/grt/tracks.tcl --delta-id D-KV-CLK-R13-UP > $1.log 2>&1 || { tail -20 $1.log; exit 1; }
python3 -c "
import json;m=json.load(open('$1/mesh.json'));mt=m['meta'];print(mt.get('upstream_slides'));print({k:mt[k] for k in ('node_move_max_um','htree_wire_mm','clock_hard_keepout_violations','clock_cell_overlap_pairs','leaf_grid') if k in mt}); print('unplaced',len(m['unplaced']),m['unplaced'][:3])"
python3 /srv/opentallas-scratch2/claude/clock-kv-r12-1026/census_pd.py plan_r12.json $1/mesh.json $T $1_census.json
