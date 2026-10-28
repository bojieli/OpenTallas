#!/bin/bash
# DIE-S81-16 go15 = THE one S81 build on plan_s11 (COORD 13:5x): plan_s10 + bf_col pin fix + _gb ROM master + rom/bf early
# taps re-derived (285 TT UNCHECKED, no CORES-EARLY-2 views yet) + delta_signed_view_pins; tools = claude/die-s81-16-1028
# (main aec2b2f + approved S81-14 merge mode, RM169, onemodel-2/3, CLK-INV-CAL-1, S81-15 --cell-paths, S81-16 join budget).
# Clock = go14 recipe (inv2, region DME delay on all 398 regions, early as DME sink delay = merge mode at 1.78/1.53, snake
# all, dme_feed_centroid, feed sb6, bays) + --cell-paths.  "branched slew legs": merge mode has no hang stars (the go13
# slew cells sat on star hang legs); no separate leg-branch tool (counted as legs >450 um + slew cells, see README).
# Post: GRT TT/FF, readout both edges, duty/MPW, proof, intra die STA declared + PER REGION, view (fail closed), render,
# CA width/phase on the cell-path tree.
set -u
W=/srv/opentallas-scratch2/claude/wt/die-s81-16; MT=$W/tools/die_plan; O=/srv/opentallas-scratch2/claude/die-s81-16/go15
G14=/srv/opentallas-scratch2/claude/die-s81-14/go14; S14=/srv/opentallas-scratch2/claude/wt/die-s81-14/results/die_s81_14_1028/scripts
R=/srv/opentallas-scratch2/claude/die-s81-16/go15/s12/results/die_s81_12_1028/scripts;  # git archive 1347b6f6fb (DIE-S81-12)
 SC=$W/results/die_s81_16_1028/scripts
PL=/srv/opentallas-scratch2/claude/die-s81-16/plan/plan_s11.json; ST=$O/go15.status
echo "START $(date) host $(hostname) code $(git -C $W rev-parse --short HEAD) dirty $(git -C $W status --porcelain tools | wc -l) plan $(sha256sum $PL | cut -c1-12)" > $ST
REG=$(python3 -c "import json;print(','.join(sorted(set(json.load(open('$G14/map398.json'))['part_region'].values()))))")
/usr/bin/time -v python3 $MT/die_trial.py kit $PL --out $O/kit --leaf-um 200 --rep-um 250 --tree-form link_htree --feed $G14/feed_sb6.json \
  --region-trees $G14/map398.json --tree-site-legal --tree-site-slide --region-dme delay --region-dme-only $REG \
  --region-dme-early 1.78 --region-dme-early-ff 1.53 --region-dme-early-mode merge --region-dme-snake all --clock-cell inv2 \
  --tree-opt dme_feed_centroid=1 --cell-paths > $O/kit.log 2>&1
echo "KIT_RC $? $(date)" >> $ST; grep -E "Maximum resident|Elapsed" $O/kit.log >> $ST
[ -f $O/kit/clock/tree.json ] || exit 1
python3 - $O/kit/clock/tree.json >> $ST <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); s = json.dumps(t)
print("JOIN_FALLBACKS", s.count('"join_fallbacks"'))
PY
python3 $MT/clock_body_bays.py $PL $O/kit/clock/tree.json --out $O/bays > $O/bays.log 2>&1; echo "BAYS_RC $? $(date)" >> $ST
sed "s#/srv/opentallas-scratch2/claude/die-s81-14/go14#$O#" $G14/overlay14.py > $O/overlay15.py
python3 $O/overlay15.py > $O/overlay.log 2>&1; echo "OVERLAY_RC $? $(date)" >> $ST
mkdir -p $O/clk; cp $O/kit/clock/{ctree.v,ctree.tcl,tree.json} $O/clk/ || exit 1; cp $O/clk/ctree.tcl $O/clk/ctree_ck89.tcl
for C in TT FF; do
  mkdir -p $O/out_$C
  CORNER=$C ADJ=0.75 python3 $R/mk_combo_dcm.py $O/kit $O/clk $O/out_$C > $O/mk_$C.log 2>&1 || { echo MK_FAIL $C >> $ST; exit 1; }
  python3 $G14/patch_combo_inv.py $O/clk/ctree.v $O/out_$C/combo.tcl >> $O/mk_$C.log 2>&1 || { echo PATCH_FAIL $C >> $ST; exit 1; }
  python3 $MT/die_trial.py readout $O/clk/ctree.v --prefix ck_ --cells 'ck_*' --tap-slew --period 833.333 > $O/readout_$C.tcl || { echo READOUT_FAIL $C >> $ST; exit 1; }
  python3 $G14/splice_readout.py $O/out_$C/combo.tcl $O/readout_$C.tcl >> $O/mk_$C.log 2>&1 || { echo SPLICE_FAIL $C >> $ST; exit 1; }
  docker run -d --name dies81-16-$C --memory=56g --memory-swap=56g --cpus=8 -e CORNER=$C -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v $O/kit:/work:ro -v $O/out_$C:/out openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$C.log 2>&1; echo EXIT \$? >> /out/combo_$C.log; chown -R $(id -u):$(id -g) /out"
done
for C in TT FF; do docker wait dies81-16-$C; docker rm dies81-16-$C >/dev/null; done
echo "GRT_DONE $(date)" >> $ST
for C in TT FF; do grep -E "^(M[1-9]|Total) " $O/out_$C/combo_$C.log | tail -10 >> $ST; tail -2 $O/out_$C/combo_$C.log >> $ST; done
for C in TT FF; do python3 $G14/duty_compat.py $O/out_$C/arr_$C.txt $O/out_$C/arr_${C}_duty.txt; done
python3 /srv/opentallas-scratch2/claude/die-qc11-1028/duty_eval.py $O/out_TT/arr_TT_duty.txt $O/out_FF/arr_FF_duty.txt $O/duty15.json > $O/duty.log 2>&1; echo "DUTY_RC $? $(date)" >> $ST
mkdir -p $O/proof
for C in TT FF; do python3 $MT/trial_tap_arrivals.py $O/clk/tree.json $O/out_$C/arr_$C.txt $C $O/proof/tap_arrivals_$C.json >> $ST 2>&1 || { echo PROOF_FAIL >> $ST; exit 1; }; done
python3 - $O/clk/tree.json $G14/map398.json $O/proof <<"PY"
import json, sys
t = json.load(open(sys.argv[1])); reg = json.load(open(sys.argv[2]))["part_region"]; o = sys.argv[3]
json.dump(dict(note="DIE-S81-16 go15: tap table only (no mesh); die_trial link_htree + region DME merge-early + cell paths, inv2, feed sb6, plan_s11",
               taps=[dict(port=x["port"], part=x["part"], xy=x["xy"]) for x in t["taps"]]), open(o + "/mesh.json", "w"))
json.dump({x["port"]: "grp:" + reg[x["part"]] for x in t["taps"]}, open(o + "/droop_regions.json", "w"))
PY
STA="--corner TT --corner FF --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --core-latency-ff 202.5 --hold-buffers none --cppr-lca --clock-cal spice --clock-cell inv2"
python3 $SC/per_region_hold.py $MT $G14/map398.json $O/per_region_declared.json -- $O/proof --plan $PL --out $O/sta_declared $STA --core-insertion declared > $O/sta_declared.log 2>&1; echo "sta declared+per-region rc $?" >> $ST
grep -E "intra |PER-REGION" $O/sta_declared.log | cut -c1-300 >> $ST
python3 $MT/die_sta_related.py $O/proof --plan $PL --out $O/sta_view $STA --core-insertion view > $O/sta_view.log 2>&1; echo "sta view rc $? (fail-closed expected: 0 signed early-core views)" >> $ST
grep -E "intra |missing" $O/sta_view.log | cut -c1-300 | head -4 >> $ST
python3 /srv/opentallas-scratch2/claude/die-s81-15/cp14/ctree_pil.py $O/clk/tree.json $PL $O/ctree15.png > $O/render.log 2>&1; echo "RENDER_RC $?" >> $ST
python3 $S14/edge_stats.py $O > $O/edge_stats15.txt 2>&1
mkdir -p $O/lpo; ln -sfn $O/clk $O/lpo/clk; ln -sfn $O/out_TT $O/lpo/out_TT; ln -sfn $O/out_FF $O/lpo/out_FF
python3 $W/tools/s81_head/landed_phase_ocv.py $PL $O/lpo --tools $MT --out $O/lpo.json > $O/lpo.log 2>&1; echo "LPO_RC $?" >> $ST
PR=$O/proof; X=$O/lpo.json
F="--sta-proof $PR --sta-plan $PL --sta-clock-cal spice --sta-cppr-lca --sta-clock-ocv table --sta-clock-droop shared --sta-droop-regions $PR/droop_regions.json --sta-core-latency-ff 202.5 --sta-clock-cell inv2"
for M in width phase; do
  B=$O/ca_$M; mkdir -p $B; UP=""; [ $M = width ] && UP="--start-retime-up --start-retime-max 8"
  python3 $MT/count_align_plan.py $X $F --start-tree clock --start-clean $M $UP --mc-chips 300 --out $B/plan.json > $B/plan.log 2>&1; echo "CA plan $M rc $?" >> $ST
  python3 $MT/count_align_bind.py $X --from-ocv --parts ocv --scale 1.0 --samples 2000 $F --start-tree clock --start-clean $M $UP --out $B/bind.json > $B/bind.log 2>&1; echo "CA bind $M rc $?" >> $ST
  [ -f $B/bind.json ] && { python3 $MT/die_sta_related.py $PR --plan $PL --out $B/sta $STA --core-insertion declared --count-align $B/bind.json --count-align-key region > $B/sta.log 2>&1; echo "CA sta $M rc $?" >> $ST; grep -E "COUNT-ALIGN|START" $B/sta.log | cut -c1-300 >> $ST; }
done
echo "DONE $(date)" >> $ST
