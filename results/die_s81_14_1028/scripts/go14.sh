#!/bin/bash
# DIE-S81-14 go14: S81 inverter (inv2) die clock with early core taps as DME SINK DELAY (--region-dme-early-mode merge,
# opt-in on claude/die-s81-14-merge-1028) at the S81-measured early ratio TT 1.78 / FF 1.53 (DIE-S81-13 early_ratio.py),
# instead of the DIE-QC-8 upper-node hangs (star legs, mis-delivery).  Everything else = go13 (feed sb6, region DME delay on
# all 398 regions, snake all, dme_feed_centroid, site legal+slide, bays overlay, combo GRT 50 it TT+FF).
# Post: duty both edges + MPW (taps), rise proof, intra die STA with the CLK-INV-CAL-1 rows (--clock-cell inv2 declared),
# Readout = shared FLOW-ONEMODEL-2 die_trial.py readout (both edges at every tap + tree node, polarity-resolved; COORD 12:xx),
# proof = its trial_tap_arrivals on the full arr (no grep -v ^F).
# + labelled what-if crediting the declared core insertion, edge/slew stats.  NOT in go14: (ii) node split, F1, CA (onemodel-2).
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-14; MT=$W/tools/die_plan; O=/srv/opentallas-scratch2/claude/die-s81-14/go14
R=/srv/opentallas-scratch2/claude/wt/die-s81-13/results/die_s81_12_1028/scripts; CT=/srv/opentallas-scratch2/claude/die-s81-14/cal_tools/tools/die_plan
RS=$W/results/die_s81_14_1028/scripts; OM=/srv/opentallas-scratch2/claude/die-s81-14/om2_tools/tools/die_plan   # FLOW-ONEMODEL-2 @3e95a78976 (approved)
PL=/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json; ST=$O/go14.status
echo "START $(date) host $(hostname) code $(git -C $W rev-parse --short HEAD) dirty $(git -C $W status --porcelain tools | wc -l)" > $ST
REG=$(python3 -c "import json;print(','.join(sorted(set(json.load(open('$O/map398.json'))['part_region'].values()))))")
python3 $MT/die_trial.py kit $PL --out $O/kit --leaf-um 200 --rep-um 250 --tree-form link_htree --feed $O/feed_sb6.json \
  --region-trees $O/map398.json --tree-site-legal --tree-site-slide --region-dme delay --region-dme-only $REG \
  --region-dme-early 1.78 --region-dme-early-ff 1.53 --region-dme-early-mode merge --region-dme-snake all --clock-cell inv2 \
  --tree-opt dme_feed_centroid=1 > $O/kit.log 2>&1
echo "KIT_RC $? $(date)" >> $ST; tail -3 $O/kit.log >> $ST
[ -f $O/kit/clock/tree.json ] || exit 1
python3 $MT/clock_body_bays.py $PL $O/kit/clock/tree.json --out $O/bays > $O/bays.log 2>&1; echo "BAYS_RC $? $(date)" >> $ST
python3 $O/overlay14.py > $O/overlay.log 2>&1; echo "OVERLAY_RC $? $(date)" >> $ST
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/ || exit 1; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  mkdir -p $O/out_$C
  CORNER=$C ADJ=0.75 python3 $R/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C >> $ST; exit 1; }
  python3 $O/patch_combo_inv.py $O/clk/ctree.v $O/out_$C/combo.tcl >> $O/mk_$C.log 2>&1 || { echo PATCH_FAIL $C >> $ST; exit 1; }
  python3 $OM/die_trial.py readout $O/clk/ctree.v --prefix ck_ --cells 'ck_*' --tap-slew --period 833.333 > $O/readout_$C.tcl || { echo READOUT_FAIL $C >> $ST; exit 1; }
  python3 $O/splice_readout.py $O/out_$C/combo.tcl $O/readout_$C.tcl >> $O/mk_$C.log 2>&1 || { echo SPLICE_FAIL $C >> $ST; exit 1; }
  docker run -d --name dies81-14-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-14-$C; docker rm dies81-14-$C >/dev/null; done
echo "GRT_DONE $(date)" >> $ST
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10 >> $ST; tail -2 $O/out_$C/combo_$C.log >> $ST; done
for C in TT FF; do python3 $O/duty_compat.py $O/out_$C/arr_$C.txt $O/out_$C/arr_${C}_duty.txt; done
python3 /srv/opentallas-scratch2/claude/die-qc11-1028/duty_eval.py $O/out_TT/arr_TT_duty.txt $O/out_FF/arr_FF_duty.txt $O/duty14.json > $O/duty.log 2>&1; echo "DUTY_RC $? $(date)" >> $ST
mkdir -p $O/proof
for C in TT FF; do python3 $OM/trial_tap_arrivals.py $O/clk/tree.json $O/out_$C/arr_$C.txt $C $O/proof/tap_arrivals_$C.json >> $ST 2>&1 || { echo PROOF_FAIL >> $ST; exit 1; }; done
python3 - $O/clk/tree.json $O/map398.json $O/proof <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-S81-14 go14: tap table only (no mesh); die_trial link_htree + region DME merge-early, inv2, feed sb6",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
python3 $CT/die_sta_related.py $O/proof --plan $PL --out $O/sta_intra --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2 > $O/sta_intra.log 2>&1; echo "sta_intra rc $?" >> $ST
grep -E "intra " $O/sta_intra.log | cut -c1-300 >> $ST
mkdir -p $O/proof_corelat; cp $O/proof/{droop_regions,mesh}.json $O/proof_corelat/
python3 $RS/corelat.py $O/proof $O/proof_corelat $CT >> $ST 2>&1
python3 $CT/die_sta_related.py $O/proof_corelat --plan $PL --out $O/sta_intra_corelat --corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $O/proof_corelat/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2 > $O/sta_intra_corelat.log 2>&1; echo "sta_intra_corelat (WHAT-IF) rc $?" >> $ST
grep -E "intra " $O/sta_intra_corelat.log | cut -c1-300 >> $ST
(cd $O && python3 $RS/overshoot.py > overshoot14.txt 2>&1; python3 $RS/edge_stats.py $O > edge_stats14.txt 2>&1)
echo "DONE $(date)" >> $ST
