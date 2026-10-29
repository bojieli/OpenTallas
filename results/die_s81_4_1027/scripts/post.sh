#!/bin/bash
# DIE-S81-4 post-GRT: proof (KV-3 mkproof recipe) -> main die_sta_related (related pairs, --cppr-lca, clk_aocv table,
# shared droop, class data droop, TT setup / FF hold, core latency 250 TT / 202.5 FF) at x1.00 and OWNER 12.15 spice scale.
set -u
WT=/srv/opentallas-scratch2/claude/wt/die-s81-4; O=/srv/opentallas-scratch2/claude/die-s81-4; R=$WT/results/die_s81_4_1027/scripts
PL=/srv/opentallas-scratch2/claude/die-s81-3/die_plan_r98.json; MAP=/srv/opentallas-scratch2/claude/die-s81-3/map98.json
mkdir -p $O/proof
for C in TT FF; do python3 $R/trial_tap_arrivals.py $O/clk/tree.json $O/out_$C/arr_$C.txt $C $O/proof/tap_arrivals_$C.json; done
python3 - $O/clk/tree.json $MAP $O/proof <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-S81-4: tap table only (no mesh); die_trial link_htree region trees",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
python3 $R/spice_scale_proof.py $O/proof $O/proof_spice TT=1.0485,FF=1.0552
for V in proof proof_spice; do
  python3 $WT/tools/die_plan/die_sta_related.py $O/$V --plan $PL --out $O/sta_$V --cppr-lca --clock-ocv table --clock-droop shared \
    --droop-regions $O/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers HB4 --landing-window-ps 416.5 > $O/sta_$V.log 2>&1
  echo STA_RC $V $?
  grep -E "pairs|SUMMARY" $O/sta_$V.log | cut -c1-300
done
# count-aligned crossings on the MEASURED tree: main landed_phase_ocv -> MESO-RECONCILE-2 count_align_plan (32e8cbb164,
# archive in $O/mr2, not on main yet) at x1.00 and the OWNER 12.15 spice scales (single --scale: 1.0485 TT, 1.0552 FF).
mkdir -p $O/lpo; ln -sfn ../clk $O/lpo/clk; ln -sfn ../out_TT $O/lpo/out_TT; ln -sfn ../out_FF $O/lpo/out_FF
python3 $WT/tools/s81_head/landed_phase_ocv.py $PL $O/lpo --tools $WT/tools/die_plan --out $O/lpo.json > $O/lpo.log 2>&1; echo LPO_RC $?
for S in 1.0 1.0485 1.0552; do
  python3 $O/mr2/tools/die_plan/count_align_plan.py $O/lpo.json --scale $S --mc-chips 500 --out $O/ca_s$S.json > $O/ca_s$S.log 2>&1; echo CA_RC $S $?
  tail -c 1500 $O/ca_s$S.log; echo
done
echo POST_DONE $(date)
