#!/bin/bash
# DIE-S81-13: --start-clean width with --start-retime-up on the DIE-S81-12 built arrivals (sb5 link_htree), plan + bind + die STA recheck
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-13; MT=$W/tools/die_plan; S=/srv/opentallas-scratch2/claude/die-s81-12; O=/srv/opentallas-scratch2/claude/die-s81-13; PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json
TAG=${1:-up}; RMAX=${2:-8}
echo START $(date) code $(git -C $W rev-parse --short HEAD) dirty $(git -C $W status --porcelain tools | wc -l)
PR=$S/proof; X=$S/lpo.json
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
G=$O/ca_$TAG; mkdir -p $G
python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean width --start-retime-up --start-retime-max $RMAX --mc-chips 300 --out $G/plan.json > $G/plan.log 2>&1; echo "plan rc $?"
python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --start-tree clock --start-clean width --start-retime-up --start-retime-max $RMAX --out $G/bind.json > $G/bind.log 2>&1; echo "bind rc $?"
python3 $MT/die_sta_related.py $PR --plan $PL --out $G/sta --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $G/bind.json --count-align-key region > $G/sta.log 2>&1; echo "sta rc $?"; grep -E "COUNT-ALIGN|START|intra " $G/sta.log | cut -c1-400
echo DONE $(date)
