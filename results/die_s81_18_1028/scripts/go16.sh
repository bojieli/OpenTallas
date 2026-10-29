#!/bin/bash
# DIE-S81-18 go16 (COORD 21:33 ASK DEFAULT YES; DIE-S81-17 root cause): go15 recipe on plan_s11 with the two structural fixes
#   (1) region DME priced with the S81 routed inv2 stage model: --region-dme-stage-cal inv2_stage_cal_s81_go15.json
#       (fit_dme_stage_cal.py, 16604 go15 legs, TT d0 12.45 / k1 0.162 / kf 12.3, rms 7.95 vs 30.8)
#   (2) early taps without the empirical fudge: --region-dme-early 1.0 / --region-dme-early-ff 1.0 (merge mode)
# plan_s11e = plan_s11 + rom _gb taps 419/313 + bf_col 390/291 (CORES-EARLY-6 corrected PLAN, UNCHECKED; COORD 22:11 do not wait) + tap_note dropped.
# Gate STA = --clock-cal spice_edge (NUMBER-CHECK-INV-1 PASS, COORD 22:xx); spice = INFO. Skew = arrival minus planned target.
# Post: GRT TT/FF, readout, duty, proof, die STA declared + per region (spice_edge gate, spice info), CA width/phase, render,
# stage-cal REFIT on go16 routed legs (per-leg rms vs the cal it was built with).
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-18; MT=$W/tools/die_plan; B=/srv/opentallas-scratch2/claude/die-s81-18
I=$B/stage/in; O=$B/go16; PL=$I/plan_s11e.json; CAL=$I/inv2_stage_cal_s81_go15.json; ST=$O/go16.status
mkdir -p $O
echo "START $(date) host $(hostname) code $(git -C $W rev-parse --short HEAD) dirty $(git -C $W status --porcelain tools | wc -l) plan $(sha256sum $PL | cut -c1-12) cal $(sha256sum $CAL | cut -c1-12)" > $ST
REG=$(python3 -c "import json;print(','.join(sorted(set(json.load(open('$I/map398.json'))['part_region'].values()))))")
/usr/bin/time -v python3 $MT/die_trial.py kit $PL --out $O/kit --leaf-um 200 --rep-um 250 --tree-form link_htree --feed $I/feed_sb6.json \
  --region-trees $I/map398.json --tree-site-legal --tree-site-slide --region-dme delay --region-dme-only $REG \
  --region-dme-early 1.0 --region-dme-early-ff 1.0 --region-dme-early-mode merge --region-dme-snake all --clock-cell inv2 \
  --region-dme-stage-cal $CAL --tree-opt dme_feed_centroid=1 --cell-paths > $O/kit.log 2>&1
echo "KIT_RC $? $(date)" >> $ST; grep -E "Maximum resident|Elapsed" $O/kit.log >> $ST
[ -f $O/kit/clock/tree.json ] || exit 1
python3 $MT/clock_body_bays.py $PL $O/kit/clock/tree.json --out $O/bays > $O/bays.log 2>&1; echo "BAYS_RC $? $(date)" >> $ST
sed "s#/srv/opentallas-scratch2/claude/die-s81-14/go14#$O#" $I/overlay14.py > $O/overlay16.py
python3 $O/overlay16.py > $O/overlay.log 2>&1; echo "OVERLAY_RC $? $(date)" >> $ST
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/ || exit 1; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  mkdir -p $O/out_$C
  CORNER=$C ADJ=0.75 python3 $I/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C >> $ST; exit 1; }
  python3 $I/patch_combo_inv.py $O/clk/ctree.v $O/out_$C/combo.tcl >> $O/mk_$C.log 2>&1 || { echo PATCH_FAIL $C >> $ST; exit 1; }
  python3 $MT/die_trial.py readout $O/clk/ctree.v --prefix ck_ --cells 'ck_*' --tap-slew --period 833.333 > $O/readout_$C.tcl || { echo READOUT_FAIL $C >> $ST; exit 1; }
  python3 $I/splice_readout.py $O/out_$C/combo.tcl $O/readout_$C.tcl >> $O/mk_$C.log 2>&1 || { echo SPLICE_FAIL $C >> $ST; exit 1; }
  docker run -d --name dies81-18-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-18-$C; docker rm dies81-18-$C >/dev/null; done
echo "GRT_DONE $(date)" >> $ST
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10 >> $ST; tail -2 $O/out_$C/combo_$C.log >> $ST; done
for C in TT FF; do python3 $I/duty_compat.py $O/out_$C/arr_$C.txt $O/out_$C/arr_${C}_duty.txt; done
python3 $I/duty_eval.py $O/out_TT/arr_TT_duty.txt $O/out_FF/arr_FF_duty.txt $O/duty16.json > $O/duty.log 2>&1; echo "DUTY_RC $? $(date)" >> $ST
# stage-cal REFIT on the go16 routed legs (rms vs the cal the tree was built with)
python3 $MT/fit_dme_stage_cal.py --tree $O/kit/clock/tree.json --arr-prefix $O/out --tap-from $CAL --even-legs --built-with $CAL \
  -o $O/inv2_stage_cal_s81_go16.json > $O/refit.log 2>&1; echo "REFIT_RC $?" >> $ST; cat $O/refit.log >> $ST
mkdir -p $O/proof
for C in TT FF; do python3 $MT/trial_tap_arrivals.py $O/clk/tree.json $O/out_$C/arr_$C.txt $C $O/proof/tap_arrivals_$C.json >> $ST 2>&1 || { echo PROOF_FAIL >> $ST; exit 1; }; done
python3 - $O/clk/tree.json $I/map398.json $O/proof <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-S81-18 go16: tap table only (no mesh); die_trial link_htree + region DME merge-early 1.0 + S81 inv2 stage-cal + cell paths, inv2, feed sb6, plan_s11e",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
for CAL_MODE in spice_edge spice; do
  STA="--corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal $CAL_MODE --clock-cell inv2"
  python3 $I/per_region_hold.py $MT $I/map398.json $O/per_region_${CAL_MODE}.json -- $O/proof --plan $PL --out $O/sta_${CAL_MODE} $STA --core-insertion declared > $O/sta_${CAL_MODE}.log 2>&1; echo "sta declared+per-region $CAL_MODE rc $?" >> $ST
  grep -E "intra |PER-REGION" $O/sta_${CAL_MODE}.log | cut -c1-300 >> $ST
done
STA="--corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice_edge --clock-cell inv2"
python3 $MT/die_sta_related.py $O/proof --plan $PL --out $O/sta_view $STA --core-insertion view > $O/sta_view.log 2>&1; echo "sta view rc $? (fail-closed expected without signed early-core views)" >> $ST
grep -E "intra |missing" $O/sta_view.log | cut -c1-300 | head -4 >> $ST
python3 $I/ctree_pil.py $O/clk/tree.json $PL $O/ctree16.png > $O/render.log 2>&1; echo "RENDER_RC $?" >> $ST
python3 $I/edge_stats.py $O > $O/edge_stats16.txt 2>&1
mkdir -p $O/lpo; ln -sfn $O/clk $O/lpo/clk; ln -sfn $O/out_TT $O/lpo/out_TT; ln -sfn $O/out_FF $O/lpo/out_FF
python3 $W/tools/s81_head/landed_phase_ocv.py $PL $O/lpo --tools $MT --out $O/lpo.json > $O/lpo.log 2>&1; echo "LPO_RC $?" >> $ST
PR=$O/proof; X=$O/lpo.json
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice_edge --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv2"
for M in width phase; do
  D=$O/ca_$M; mkdir -p $D; UP=""; [ $M = width ] && UP="--start-retime-up --start-retime-max 8"
  python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean $M $UP --mc-chips 300 --out $D/plan.json > $D/plan.log 2>&1; echo "CA plan $M rc $?" >> $ST
  python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --start-tree clock --start-clean $M $UP --out $D/bind.json > $D/bind.log 2>&1; echo "CA bind $M rc $?" >> $ST
  [ -f $D/bind.json ] && { python3 $MT/die_sta_related.py $PR --plan $PL --out $D/sta $STA --core-insertion declared --count-align $D/bind.json --count-align-key region > $D/sta.log 2>&1; echo "CA sta $M rc $?" >> $ST; grep -E "COUNT-ALIGN|START" $D/sta.log | cut -c1-300 >> $ST; }
done
echo "DONE $(date)" >> $ST
