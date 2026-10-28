#!/bin/bash
# DIE-S81-12 post-GRT on the BUILT local-form clock (sb5 feed, link_htree): proof (S81-4 recipe) -> main landed_phase_ocv ->
# count_align_plan/bind with START-TREE-1 --start-tree clock (--start-clean width = release target, and phase) on the CA-OCV-1
# model (spice, cppr-lca, clock_variation=table, shared droop) -> die_sta_related with the bind (start-port recheck incl.).
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-12; MT=$W/tools/die_plan; R=/srv/opentallas-scratch2/claude/wt/die-s81-12/results/die_s81_12_1028/scripts; O=/srv/opentallas-scratch2/claude/die-s81-12; PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json; MAP=$O/map398.json
echo START $(date) code $(git -C $W rev-parse --short HEAD)
mkdir -p $O/proof
for C in TT FF; do python3 $R/trial_tap_arrivals.py $O/clk/tree.json $O/out_$C/arr_$C.txt $C $O/proof/tap_arrivals_$C.json || exit 1; done
python3 - $O/clk/tree.json $MAP $O/proof <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-S81-12: tap table only (no mesh); die_trial link_htree on the re-treed local feed sb5",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
mkdir -p $O/lpo; ln -sfn ../clk $O/lpo/clk; ln -sfn ../out_TT $O/lpo/out_TT; ln -sfn ../out_FF $O/lpo/out_FF
python3 $W/tools/s81_head/landed_phase_ocv.py $PL $O/lpo --tools $MT --out $O/lpo.json > $O/lpo.log 2>&1; echo LPO_RC $?
PR=$O/proof; X=$O/lpo.json
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
for M in width phase; do
  G=$O/ca_$M; mkdir -p $G
  python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean $M --mc-chips 300 --out $G/plan.json > $G/plan.log 2>&1; echo "plan $M rc $?"
  python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --start-tree clock --start-clean $M --out $G/bind.json > $G/bind.log 2>&1; echo "bind $M rc $?"
  python3 $MT/die_sta_related.py $PR --plan $PL --out $G/sta --corner TT --corner FF --clock-ocv table --clock-droop shared     --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice     --count-align $G/bind.json --count-align-key region > $G/sta.log 2>&1; echo "sta $M rc $?"; grep -E "COUNT-ALIGN|START|intra " $G/sta.log | cut -c1-400
done
python3 $MT/count_align_plan.py $X $F --mc-chips 300 --out $O/ca_data_plan.json > $O/ca_data_plan.log 2>&1; echo "plan data-start rc $?"
echo DONE $(date)
