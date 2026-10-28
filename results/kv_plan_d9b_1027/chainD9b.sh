#!/bin/bash
# DIE-KV-2 D9b: die_trial kit -> c39 continuous mesh rebuild (D5/D9a chain recipe) -> combo die GRT TT+FF (50 it, -critical_nets_percentage 0)
set -e; M=/srv/opentallas-scratch2/claude/kv-plan-d9b-1027; W=$M/main/tools/die_plan; B=$M/clk/q9b; PL=$M/pd9b/hm_r26q9b.json; D5=/srv/opentallas-scratch2/claude/kv-plan-d5-1027
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/pylib:$W
cd $M; mkdir -p clk
echo KIT_START $(date -Is)
python3 $W/die_trial.py kit $PL --out $M/kitD9b > $M/kitD9b.log 2>&1
echo KIT_DONE $(date -Is)
python3 $W/die_clock_mesh.py build $PL --out $B --nx 32 --ny 71 --m 2 --rep-um 450 --ndr 4w --max-move 500 --hop-max 405 --reserve-cell-sites --lattice-spec $D5/clk/lat_q5c39_ref.json --track-file $M/kitD9b/grt/tracks.tcl --delta-id KV-PLAN-DELTA-9B > $M/clk/q9b_build.log 2>&1
python3 -c "import json;m=json.load(open(\"$B/mesh.json\"));mt=m[\"meta\"];print(\"BUILD\",{k:mt.get(k) for k in (\"unplaced\",\"clock_hard_keepout_violations\",\"clock_cell_overlap_pairs\",\"node_move_max_um\",\"htree_wire_mm\")},\"unplaced\",len(m[\"unplaced\"]))"
grep -h "shield ties\|metal shorts" $M/clk/q9b_build.log | tail -n 2 || true
python3 $W/die_clock_mesh.py combo $B --kit $M/kitD9b --plan $PL 2>&1 | tail -n 3
grep -n "congestion_iterations\|critical_nets" $B/combo.tcl | head -4
MEM=48 bash $B/run_combo.sh
for c in TT FF; do echo GRT $c; grep -A12 "Final congestion" $B/combo_$c.log | tail -n 10; grep "extra iteration" $B/combo_$c.log | tail -n 1; grep EXIT $B/combo_$c.log; done
echo GRT_DONE $(date -Is)
