#!/bin/bash
# DIE-KV-12 post-GRT chain on kit_<T> (DIE-KV-11 post_rt.sh + st_rt.sh recipe, main tools at the KV-12 worktree, START-TREE-1
# 91c2e9fec3 git archive in die-kv-11-1028/st1, no fork): arrivals -> proof -> landed_phase_ocv -> ca_spice -> count_align_bind
# --from-ocv --start-tree clock (K with OCV: clock-ocv table, spice, cppr-lca, shared droop, FF 202.5) phase + width -> main
# die_sta_related gate (region key, HB4).
set -u
T=$1; R=/srv/opentallas-scratch2/claude/die-kv-14-1028; W=/srv/opentallas-scratch2/claude/wt/die-kv-14/tools
S=/srv/opentallas-scratch2/claude/wt/die-kv-14/tools/die_plan
L=/srv/opentallas-scratch2/claude/die-kv-2-1027/l128; PL=/srv/opentallas-scratch2/claude/die-kv-4-1027/pd9c/hm_r26q9c.json
LK=/srv/opentallas-scratch2/claude/land-kv-1027; K5=/srv/opentallas-scratch2/claude/die-kv-5-1027
cd $R || exit 1; P=$R/proof_$T; mkdir -p $P
for C in TT FF; do python3 $LK/trial_tap_arrivals.py clk_$T/tree.json out_${T}_$C/arr_$C.txt $C $P/tap_arrivals_$C.json; done
python3 - clk_$T/tree.json $L/land128_regions.json $P <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-KV-12: tap table only (no mesh); die_trial link_htree inverter region trees on the re-tree feed",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
echo PROOF_DONE $(date -Is)
mkdir -p lpo_$T; ln -sfn ../clk_$T lpo_$T/clk; ln -sfn ../out_${T}_TT lpo_$T/out_TT; ln -sfn ../out_${T}_FF lpo_$T/out_FF
python3 $W/s81_head/landed_phase_ocv.py $PL lpo_$T --tools $W/die_plan --clock-cell inv --out lpo_$T.json > lpo_$T.log 2>&1; echo LPO_RC $? $(date -Is)
mkdir -p ca_$T; cd ca_$T; cp $K5/split/ca_spice.py .; cp $W/die_plan/count_align_plan.py .
python3 -I ca_spice.py $R/lpo_$T.json $L/land128_regions.json ${T}_spice 1.0485 1.0552 --mc 2000 2>&1 | tail -n 2
STA="--sta-proof $P --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $P/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv"
for M in width phase; do
  python3 $S/count_align_bind.py ${T}_spice_xing_lpo.json --from-ocv --parts ocv $STA --start-tree clock --start-clean $M --samples 500 --out st_${M}_bind_parts.json > st_${M}_bind.log 2>&1; echo BIND_${M}_RC $? $(date -Is)
done
for M in width phase; do
  mkdir -p $R/sta_${T}_$M; cp -r /srv/opentallas-scratch2/claude/die-kv-6-1028/sta_region/regchar $R/sta_${T}_$M/ 2>/dev/null
  python3 $S/die_sta_related.py $P --plan $PL --out $R/sta_${T}_$M --clock-cal spice --cppr-lca --count-align $R/ca_$T/st_${M}_bind_parts.json --count-align-key region --clock-ocv table --clock-droop shared --droop-regions $P/droop_regions.json --hold-buffers HB4 --core-latency-ff 202.5 --clock-cell inv > $R/sta_${T}_$M.log 2>&1; echo STA_${M}_RC $? $(date -Is)
done
echo CA_DONE $(date -Is)
