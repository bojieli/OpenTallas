#!/bin/bash
# DIE-S81-13 rebuild of the S81 local form: feed sb6 (sb5 + phy_hbm hard macro as feed LEAF) + main/QC-11 die_trial opt-ins:
#   --clock-cell inv2 (DIE-QC-11, duty), --region-dme delay on ALL regions with early core-tap hang (QC-8/9) + snake all
#   (in-region balance, item 3), --tree-opt dme_feed_centroid=1 (feed ends at the tap centroid, off the PHY macro slots,
#   item 4), --tree-site-legal --tree-site-slide; then clock_body_bays overlay, die GRT incl clock 50 it TT+FF with
#   fall arrivals, duty_eval, proof -> landed_phase_ocv -> CA width with --start-retime-up -> bind -> die STA.
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-13; MT=$W/tools/die_plan; O=/srv/opentallas-scratch2/claude/die-s81-13; R=$W/results/die_s81_12_1028/scripts
PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json; B=/srv/opentallas-scratch2/claude/die-s81-8/gate_sspice/bind.json
P5=/srv/opentallas-scratch2/claude/die-s81-5/plan_s5.json; ST=$O/go13.status
echo "START $(date) host $(hostname) code $(git -C $W rev-parse --short HEAD) dirty $(git -C $W status --porcelain tools | wc -l)" > $ST
python3 $R/mkfeed.py $W $P5 $B $O/sb6.json $O/feed_sb6.json $O/map398.json > $O/mkfeed.log 2>&1 || { echo MKFEED_FAIL >> $ST; exit 1; }
REG=$(python3 -c "import json;print(','.join(sorted(set(json.load(open('$O/map398.json'))['part_region'].values()))))")
python3 $MT/die_trial.py kit $PL --out $O/kit --leaf-um 200 --rep-um 250 --tree-form link_htree --feed $O/feed_sb6.json \
  --region-trees $O/map398.json --tree-site-legal --tree-site-slide --region-dme delay --region-dme-only $REG \
  --region-dme-early 1.48 --region-dme-early-ff 1.28 --region-dme-snake all --clock-cell inv2 --tree-opt dme_feed_centroid=1 > $O/kit.log 2>&1
echo "KIT_RC $? $(date)" >> $ST; tail -3 $O/kit.log >> $ST
[ -f $O/kit/clock/tree.json ] || exit 1
python3 $MT/clock_body_bays.py $PL $O/kit/clock/tree.json --out $O/bays > $O/bays.log 2>&1; echo "BAYS_RC $? $(date)" >> $ST
python3 $O/overlay13.py > $O/overlay.log 2>&1; echo "OVERLAY_RC $? $(date)" >> $ST
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/ || exit 1; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  mkdir -p $O/out_$C
  CORNER=$C ADJ=0.75 python3 $R/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C >> $ST; exit 1; }
  python3 $O/patch_combo_inv.py $O/clk/ctree.v $O/out_$C/combo.tcl >> $O/mk_$C.log 2>&1 || { echo PATCH_FAIL $C >> $ST; exit 1; }
  docker run -d --name dies81-13-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-13-$C; docker rm dies81-13-$C >/dev/null; done
echo "GRT_DONE $(date)" >> $ST
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10 >> $ST; tail -2 $O/out_$C/combo_$C.log >> $ST; done
python3 /srv/opentallas-scratch2/claude/die-qc11-1028/duty_eval.py $O/out_TT/arr_TT.txt $O/out_FF/arr_FF.txt $O/duty13.json > $O/duty.log 2>&1; echo "DUTY_RC $? $(date)" >> $ST
# post: proof -> lpo -> CA width (--start-retime-up) + phase -> bind -> die STA (DIE-S81-12 post.sh form)
mkdir -p $O/proof
for C in TT FF; do grep -v "^F " $O/out_$C/arr_$C.txt > $O/out_$C/arr_${C}_rise.txt; python3 $R/trial_tap_arrivals.py $O/clk/tree.json $O/out_$C/arr_${C}_rise.txt $C $O/proof/tap_arrivals_$C.json >> $ST 2>&1 || { echo PROOF_FAIL >> $ST; exit 1; }; done
python3 - $O/clk/tree.json $O/map398.json $O/proof <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-S81-13: tap table only (no mesh); die_trial link_htree + region DME, inv2, feed sb6",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
mkdir -p $O/lpo; ln -sfn ../clk $O/lpo/clk; ln -sfn ../out_TT $O/lpo/out_TT; ln -sfn ../out_FF $O/lpo/out_FF
python3 $W/tools/s81_head/landed_phase_ocv.py $PL $O/lpo --tools $MT --out $O/lpo.json > $O/lpo.log 2>&1; echo "LPO_RC $?" >> $ST
PR=$O/proof; X=$O/lpo.json
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5"
for M in width phase; do
  G=$O/b13_$M; mkdir -p $G; UP=""; [ $M = width ] && UP="--start-retime-up"
  python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean $M $UP --mc-chips 300 --out $G/plan.json > $G/plan.log 2>&1; echo "plan $M rc $?" >> $ST
  python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --start-tree clock --start-clean $M $UP --out $G/bind.json > $G/bind.log 2>&1; echo "bind $M rc $?" >> $ST
  [ -f $G/bind.json ] && { python3 $MT/die_sta_related.py $PR --plan $PL --out $G/sta --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --count-align $G/bind.json --count-align-key region > $G/sta.log 2>&1; echo "sta $M rc $?" >> $ST; grep -E "COUNT-ALIGN|START|intra " $G/sta.log | cut -c1-400 >> $ST; }
done
# die STA without CA (intra / FF hold only) when no bind passes
python3 $MT/die_sta_related.py $PR --plan $PL --out $O/sta_intra --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $PR/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice > $O/sta_intra.log 2>&1; echo "sta_intra rc $?" >> $ST
echo "DONE $(date)" >> $ST
