#!/bin/bash
set -euo pipefail
r=/srv/opentallas-scratch2/claude/codex-s81-owner-0359/clock_body
w=/srv/opentallas-scratch2/claude/wt/codex-s81-owner-1028-0359
p=/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json
mkdir -p "$r/proof_body" "$r/routed/clk" "$r/routed/out_TT" "$r/routed/out_FF"
cp /srv/opentallas-scratch2/claude/die-s81-7/proof_G/mesh.json /srv/opentallas-scratch2/claude/die-s81-7/proof_G/droop_regions.json "$r/proof_body/"
cp "$r/clock_G_body/tree.json" "$r/routed/clk/tree.json"
for c in TT FF; do
 test -s "$r/route_$c/arr_$c.txt"
 cp "$r/route_$c/arr_$c.txt" "$r/routed/out_$c/arr_$c.txt"
 python3 "$w/tools/die_plan/trial_tap_arrivals.py" "$r/clock_G_body/tree.json" "$r/route_$c/arr_$c.txt" "$c" "$r/proof_body/tap_arrivals_$c.json"
done
python3 "$w/tools/s81_head/landed_phase_ocv.py" "$p" "$r/routed" --tools "$w/tools/die_plan" --out "$r/routed/lpo.json" > "$r/routed/lpo.log"
for scale in 1.0485 1.0552; do
 python3 "$w/tools/die_plan/count_align_plan.py" "$r/routed/lpo.json" --scale "$scale" --sta-proof "$r/proof_body" --sta-plan "$p" --sta-clock-cal spice --sta-cppr-lca --out "$r/routed/ca_$scale.json" > "$r/routed/ca_$scale.log"
done
python3 "$w/tools/die_plan/die_sta_related.py" "$r/proof_body" --plan "$p" --out "$r/sta_body_spice" --core-latency-ff 202.5 --cppr-lca --clock-ocv table --clock-cal spice --clock-droop shared --droop-regions "$r/proof_body/droop_regions.json" > "$r/sta_body_spice.log"
