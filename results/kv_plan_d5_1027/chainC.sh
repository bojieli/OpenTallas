#!/bin/bash
# KV-PLAN-DELTA-5 PG c39 (COORD ruling): mesh rebuild on hm_r26q5c39 (PG-aware, strap axes = q5c mesh) -> combo GRT (TT+FF, -critical_nets_percentage 0) -> post -> MC -> die STA
set -e; M=/srv/opentallas-scratch2/claude/kv-plan-d5-1027; W=/srv/opentallas-scratch2/claude/kv-plan-d5-1027/main/tools/die_plan; B=$M/clk/q5c39; PL=$M/q5c_pd/hm_r26q5c39.json
export PYTHONPATH=/srv/opentallas-scratch2/claude/clock-kv-r19-1027/in/pylib:$W
python3 $W/die_clock_mesh.py build $PL --out $B --nx 32 --ny 71 --m 2 --rep-um 450 --ndr 4w --max-move 500 --hop-max 405 --reserve-cell-sites --lattice-spec $M/clk/lat_q5c39_ref.json --track-file $M/kitC/grt/tracks.tcl --delta-id KV-PLAN-DELTA-5-C39 > $M/clk/q5c39_build.log 2>&1
python3 -c "import json;m=json.load(open(\"$B/mesh.json\"));mt=m[\"meta\"];print(\"BUILD\",{k:mt.get(k) for k in (\"unplaced\",\"clock_hard_keepout_violations\",\"clock_cell_overlap_pairs\",\"node_move_max_um\",\"htree_wire_mm\")},\"unplaced\",len(m[\"unplaced\"]))"
python3 $W/die_clock_mesh.py combo $B --kit $M/kitC --plan $PL 2>&1 | tail -n 3
MEM=48 bash $B/run_combo.sh
for c in TT FF; do echo GRT $c; grep -A12 "Final congestion" $B/combo_$c.log | tail -n 10; grep "extra iteration" $B/combo_$c.log | tail -n 1; done
echo GRT_DONE $(date -Is)
python3 $W/die_clock_mesh.py meshvias $B
bash $W/die_clock_mesh_post.sh $B $PL > $M/clk/q5c39_post.log 2>&1
python3 $W/die_clock_mesh.py report $B --plan $PL --aocv-fold --aocv-mesh-walk > $M/clk/q5c39_report.log 2>&1
echo POST_DONE $(date -Is)
cd $M; python3 $W/kv_r18/mesh_rec18.py $B mc/rec_q5c39.json > mc/rec_q5c39.log 2>&1
for C in TT FF; do python3 $W/kv_r18/mesh_mc18.py mc/rec_q5c39.json --thev /srv/opentallas-scratch2/claude/clock-kv-r17-1027/thev_qc_m2.json --corner $C --samples 24 --routed $B/mesh_$C.json --out mc/q5c39_$C.json --qc $W/kv_r7 > mc/q5c39_$C.log 2>&1 & done; wait
grep -h SUMMARY mc/q5c39_*.log; echo MC_DONE $(date -Is)
