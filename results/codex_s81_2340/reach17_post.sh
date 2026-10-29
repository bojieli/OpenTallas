#!/bin/bash
set -eu
b=/srv/opentallas-scratch2/claude/codex-s81-2340/reach17
src=/srv/opentallas-scratch2/claude/die-s81-18
mt=/srv/opentallas-scratch2/claude/wt/die-s81-18/tools/die_plan
pl=$src/stage/in/plan_s11e.json
mkdir -p "$b/proof"
for c in TT FF; do python3 "$mt/trial_tap_arrivals.py" "$b/clk/tree.json" "$b/out_$c/arr_$c.txt" "$c" "$b/proof/tap_arrivals_$c.json" > "$b/proof/export_$c.log" 2>&1; done
cp "$src/go16/proof/mesh.json" "$src/go16/proof/droop_regions.json" "$b/proof/"
sta=(--corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions "$b/proof/droop_regions.json" --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice_edge --clock-cell inv2)
python3 "$src/stage/in/per_region_hold.py" "$mt" "$src/stage/in/map398.json" "$b/per_region.json" -- "$b/proof" --plan "$pl" --out "$b/sta_declared" "${sta[@]}" --core-insertion declared > "$b/sta_declared.log" 2>&1
python3 "$mt/die_sta_related.py" "$b/proof" --plan "$pl" --out "$b/sta_view" "${sta[@]}" --core-insertion view > "$b/sta_view.log" 2>&1
mkdir -p "$b/lpo"
ln -s "$b/clk" "$b/lpo/clk"; ln -s "$b/out_TT" "$b/lpo/out_TT"; ln -s "$b/out_FF" "$b/lpo/out_FF"
python3 /srv/opentallas-scratch2/claude/wt/die-s81-18/tools/s81_head/landed_phase_ocv.py "$pl" "$b/lpo" --tools "$mt" --out "$b/lpo.json" > "$b/lpo.log" 2>&1
flags=(--sta-proof "$b/proof" --sta-plan "$pl" --sta-clock-cal spice_edge --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions "$b/proof/droop_regions.json" --sta-core-latency-ff 202.5 --sta-clock-cell inv2)
mkdir -p "$b/ca_width"
python3 "$mt/count_align_plan.py" "$b/lpo.json" "${flags[@]}" --start-tree clock --start-clean width --start-retime-up --start-retime-max 8 --out "$b/ca_width/plan.json" > "$b/ca_width/plan.log" 2>&1
printf 'POST_DONE %s\n' "$(date)" >> "$b/status"
