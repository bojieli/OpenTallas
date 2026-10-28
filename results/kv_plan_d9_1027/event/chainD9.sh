#!/bin/bash
# KV-PLAN-DELTA-9a: die_trial kit -> c39 continuous mesh rebuild (D5 chainC recipe) -> combo die GRT TT+FF (50 it, -critical_nets_percentage 0)
set -e; M=/srv/opentallas-scratch2/claude/kv-plan-d9-1027; W=$M/main/tools/die_plan; B=$M/clk/q9; PL=$M/pd9/hm_r26q9.json; D5=/srv/opentallas-scratch2/claude/kv-plan-d5-1027
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/pylib:$W
cd $M; mkdir -p clk
echo KIT_START $(date -Is)
python3 $W/die_trial.py kit $PL --out $M/kitD9 > $M/kitD9.log 2>&1
echo KIT_DONE $(date -Is)
python3 $W/die_clock_mesh.py build $PL --out $B --nx 32 --ny 71 --m 2 --rep-um 450 --ndr 4w --max-move 500 --hop-max 405 --reserve-cell-sites --lattice-spec $D5/clk/lat_q5c39_ref.json --track-file $M/kitD9/grt/tracks.tcl --delta-id KV-PLAN-DELTA-9A > $M/clk/q9_build.log 2>&1
python3 -c "import json;m=json.load(open(\"$B/mesh.json\"));mt=m[\"meta\"];print(\"BUILD\",{k:mt.get(k) for k in (\"unplaced\",\"clock_hard_keepout_violations\",\"clock_cell_overlap_pairs\",\"node_move_max_um\",\"htree_wire_mm\")},\"unplaced\",len(m[\"unplaced\"]))"
python3 $W/die_clock_mesh.py combo $B --kit $M/kitD9 --plan $PL 2>&1 | tail -n 3
grep -n "congestion_iterations\|critical_nets" $B/combo.tcl | head -4
MEM=48 bash $B/run_combo.sh
for c in TT FF; do echo GRT $c; grep -A12 "Final congestion" $B/combo_$c.log | tail -n 10; grep "extra iteration" $B/combo_$c.log | tail -n 1; done
echo GRT_DONE $(date -Is)
