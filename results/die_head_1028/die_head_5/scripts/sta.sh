#!/bin/bash
# DIE-HEAD-5: real-netlist GRT (grt/) -> proof (tree_path) -> landed OCV -> spice rows -> count_align_plan/bind (castart) -> die STA
set -u
W=/srv/opentallas-scratch2/claude/wt/die-head-1; C5=/srv/opentallas-scratch2/claude/die-head-5; G=$C5/grt; T=${TOOLS:-$C5/castart/tools/die_plan}; O=${OUT:-$C5/sta}
J=$W/physical/die_plan/s81_head/die_plan_root_sp5.json; MAP=/srv/opentallas-scratch2/claude/die-head-3/part/map_part.json
mkdir -p $O; cd $W; echo START $(date) code $(git rev-parse --short HEAD) tools $T host $(hostname)
[ -s $C5/proof/tap_arrivals_TT.json ] || python3 tools/s81_head/head_mk_proof_lca.py $G $MAP $C5/proof > $C5/mk_proof.log 2>&1 || { echo PROOF_FAIL; tail -3 $C5/mk_proof.log; exit 1; }
[ -s $C5/landed_ocv.json ] || python3 tools/s81_head/landed_phase_ocv.py $G/plan_rs_fb1.json $G --tools $W/tools/die_plan --out $C5/landed_ocv.json > $C5/landed_ocv.log 2>&1 || { echo OCV_FAIL; tail -3 $C5/landed_ocv.log; exit 1; }
python3 /srv/opentallas-scratch2/claude/nc-headpart/scripts/spice_scale.py $C5/landed_ocv.json $O/ocv_spice.json
cd $T
python3 count_align_plan.py $O/ocv_spice.json --mc-chips 2000 --start-skew 57.5,89.7 --out $O/plan.json > $O/plan.log 2>&1; echo plan rc=$?
python3 -c "import json;s=json.load(open(/plan.json))[summary];print({k:s.get(k) for k in (depth4,depth8,fail,worst_margin_lo_ps,worst_margin_lo_port,worst_margin_hi_ps,worst_margin_hi_port,tree_edges_fall,tree_edges_ambiguous,lat_hist,start_skew_limit_min_ps,mc)})"
python3 count_align_bind.py $O/plan.json --out $O/bind.json > $O/bind.log 2>&1; echo bind rc=$?; tail -2 $O/bind.log
python3 die_sta_related.py $C5/proof --plan $J --out $O/sta --corner TT --corner FF --core-latency-ff 202.5 --droop-regions $C5/proof/droop_regions.json --count-align $O/bind.json --clock-cal spice --cppr-lca > $O/sta.log 2>&1; echo sta rc=$?
grep -E "COUNT-ALIGN|^SUMMARY" $O/sta.log | cut -c1-1500
echo END $(date)
