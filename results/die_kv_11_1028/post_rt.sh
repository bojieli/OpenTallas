#!/bin/bash
# DIE-KV-11 post-GRT chain on kit_rt (DIE-KV-5 chain.sh steps, main tools): arrivals -> proof -> landed_phase_ocv -> ca_spice
# rows -> count_align_plan with the CA-OCV-1 STA hull (clock_variation=table, spice, cppr-lca, shared droop) -> count_align_bind
# -> main die_sta_related gate (count-align key region, clock-ocv table, HB4, FF 202.5).  Start tree = count_align_plan's own
# (START-TREE-1 fork ports not landed yet).
set -u
R=/srv/opentallas-scratch2/claude/die-kv-11-1028; T=rt; W=/srv/opentallas-scratch2/claude/wt/die-kv-6/tools
L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128; PL=/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json
LK=/srv/opentallas-scratch2/claude/land-kv-1027; K5=/srv/opentallas-scratch2/claude/die-kv-5-1027
cd $R || exit 1; mkdir -p proof$T
for C in TT FF; do python3 $LK/trial_tap_arrivals.py clk$T/tree.json out${T}_$C/arr_$C.txt $C proof$T/tap_arrivals_$C.json; done
python3 - clk$T/tree.json $L/land128_regions.json proof$T <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-KV-11: tap table only (no mesh); die_trial link_htree region trees on the re-tree feed",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
echo PROOF_DONE $(date -Is)
mkdir -p lpo$T; ln -sfn ../clk$T lpo$T/clk; ln -sfn ../out${T}_TT lpo$T/out_TT; ln -sfn ../out${T}_FF lpo$T/out_FF
python3 $W/s81_head/landed_phase_ocv.py $PL lpo$T --tools $W/die_plan --out lpo$T.json > lpo$T.log 2>&1; echo LPO_RC $? $(date -Is)
mkdir -p ca$T; cd ca$T; cp $K5/split/ca_spice.py .; cp $W/die_plan/count_align_plan.py .
python3 -I ca_spice.py $R/lpo$T.json $L/land128_regions.json ${T}_spice 1.0485 1.0552 --mc 2000 2>&1 | tail -n 2
python3 $W/die_plan/count_align_plan.py ${T}_spice_xing_lpo.json --sta-proof $R/proof$T --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $R/proof$T/droop_regions.json --sta-core-latency-ff 202.5 --mc-chips 2000 --out ${T}_ocvK_plan.json > ocvK_plan.log 2>&1; echo CAP_RC $? $(date -Is)
python3 $W/die_plan/count_align_bind.py ${T}_ocvK_plan.json --parts ocv --out ${T}_ocvK_bind_parts.json > bind.log 2>&1; echo BIND_RC $? $(date -Is)
cd $R; mkdir -p sta_table; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar sta_table/ 2>/dev/null
python3 $W/die_plan/die_sta_related.py $R/proof$T --plan $PL --out sta_table --clock-cal spice --cppr-lca --count-align $R/ca$T/${T}_ocvK_bind_parts.json --count-align-key region --clock-ocv table --clock-droop shared --droop-regions $R/proof$T/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 > sta_table.log 2>&1; echo STA_RC $? $(date -Is)
echo POST_DONE $(date -Is)
