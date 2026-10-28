#!/bin/bash
# DIE-S81-15 probe: --cell-paths on go13 (om2 both-edge arrivals): proof re-export, intra STA equality, start tree width with retime at leg repeaters
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-15; MT=$W/tools/die_plan; O=/srv/opentallas-scratch2/claude/die-s81-15/cp13
G=/srv/opentallas-scratch2/claude/flow-onemodel-2/s81g13; PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json; X=/srv/opentallas-scratch2/claude/die-s81-13/lpo.json
echo START $(date) code $(git -C $W rev-parse --short HEAD)
:  /srv/opentallas-scratch2/claude/die-s81-13/clk/tree.json $O/tree_cp.json
mkdir -p $O/proof; cp $G/proof/{mesh,droop_regions}.json $O/proof/
for P in $G/proof $O/proof; do n=$(basename $(dirname $P))_$(basename $P)
python3 $MT/die_sta_related.py $P --plan $PL --out $O/sta_$n --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $P/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2 --core-insertion declared > $O/sta_$n.log 2>&1; echo "sta $n rc $?"; grep -E "intra " $O/sta_$n.log | cut -c1-250; done
for RM in 8 32; do
F="--sta-proof $O/proof --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $O/proof/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv2"
python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean width --start-retime-up --start-retime-max $RM --out $O/plan_w$RM.json > $O/plan_w$RM.log 2>&1; echo "plan cp rm$RM rc $?"
done
F="--sta-proof $G/proof --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $G/proof/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv2"
python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean width --start-retime-up --start-retime-max 8 --out $O/plan_geo_w8.json > $O/plan_geo_w8.log 2>&1; echo "plan geo rc $?"
echo DONE $(date)
