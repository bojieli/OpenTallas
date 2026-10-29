#!/bin/bash
# DIE-S81-5 post-GRT for variant $1: proof -> main die_sta_related (related pairs, --cppr-lca, clk_aocv table, shared droop,
# class data droop, TT setup / FF hold, core latency 250 TT / 202.5 FF) at x1.00 and OWNER 12.15b spice scale; droop region
# = clock region = partition.  Then landed_phase_ocv (main) -> MESO-RECONCILE count_align_plan (32e8cbb164 archive) at
# x1.00 / x1.0485 / x1.0552.
set -u
V=${1:?variant}
WT=/srv/opentallas-scratch2/claude/wt/die-s81-5; O=/srv/opentallas-scratch2/claude/die-s81-5; R=$WT/results/die_s81_5_1028/scripts
PL=$O/plan_s5.json; CK=$O/clk_$V; PR=$O/proof_$V
MR=${MR:-/srv/opentallas-scratch2/claude/die-s81-4/mr2/tools/die_plan}
mkdir -p $PR
for C in TT FF; do python3 $R/trial_tap_arrivals.py $CK/tree.json $O/out_${V}_$C/arr_$C.txt $C $PR/tap_arrivals_$C.json; done
python3 - $CK/tree.json $PR <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); o = sys.argv[2]
json.dump(dict(note="DIE-S81-5: tap table only (no mesh); die_trial link_htree region = partition",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "part:" + x["part"] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
# x1.00 on main die_sta_related; GATE form = --clock-cal spice (OWNER 12.15b, MESO-RECONCILE-2 32e8cbb164 die_sta_related,
# ROOT-MERGE-88 pending -> archive copy $MR)
for M in main spice; do
  if [ $M = main ]; then T=$WT/tools/die_plan; X=""; else T=$MR; X="--clock-cal spice"; fi
  python3 $T/die_sta_related.py $PR --plan $PL --out $O/sta_${V}_$M --cppr-lca --clock-ocv table --clock-droop shared $X \
    --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers HB4 --landing-window-ps 416.5 > $O/sta_${V}_$M.log 2>&1
  echo STA_RC $M $?
  grep -E "pairs|SUMMARY" $O/sta_${V}_$M.log | cut -c1-300
done
L=$O/lpo_$V; mkdir -p $L; ln -sfn $CK $L/clk; ln -sfn $O/out_${V}_TT $L/out_TT; ln -sfn $O/out_${V}_FF $L/out_FF
python3 $WT/tools/s81_head/landed_phase_ocv.py $PL $L --tools $WT/tools/die_plan --out $O/lpo_$V.json > $O/lpo_$V.log 2>&1; echo LPO_RC $?
for S in 1.0 1.0485 1.0552; do
  python3 $MR/count_align_plan.py $O/lpo_$V.json --scale $S --mc-chips 500 --out $O/ca_${V}_s$S.json > $O/ca_${V}_s$S.log 2>&1; echo CA_RC $S $?
  tail -c 1500 $O/ca_${V}_s$S.log; echo
done
echo POST_DONE $(date)
