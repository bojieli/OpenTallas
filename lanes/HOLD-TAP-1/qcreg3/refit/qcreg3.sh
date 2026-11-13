#!/bin/bash
# qcreg3.sh RUNDIR : HOLD-TAP-1 (COORD 11-13 ~12:0x) third QC regional chain on s28 = QC-CLKGATE-1 qcreg2.sh + gate2.sh with
#  (1) the stage / wire-leg calibration REFIT on s28dme's routed legs (inv2_stage_cal_s28dme.json);
#  (2) early core-tap delivery also in the 36 sl_*_fe / su_l0 / su_l1 regions (hang mode), c_* merge mode as before, ratios 1.0 / 0.87;
#  (3) both-edge routed arrival readout (T/F/N/M) so the START tree can use the fall edge; --cell-paths for start retime nodes;
#  (4) crossing plans with DEPTH <= 16 (COORD ruling) and start-retime-up / start-lift variants; bind; die STA.
# ADVISORY, DO_NOT_COUNT.  Tools: QC-CLKGATE-1's tree (main 4a5e3dcf7e + s28 overlay), read-only.
set -u; export PYTHONDONTWRITEBYTECODE=1
B=$1; L=/srv/opentallas-scratch2/claude/qc-clkgate-1; H=/srv/opentallas-scratch2/claude/hold-tap-1/qcreg/refit
W=/srv/opentallas-scratch2/claude/wt/qc-clkgate-1; S=$W/tools/die_plan; TI=$W/tools; MK=$L/mk_combo_kv.py
P=$W/physical/die_plan/qwen_compute/plan_of_record/zz_gates_ev2st.json
MAP=$L/maps/regions_plain.json; FEED=$L/maps/feed_plain_fwd.json; CAL=$H/inv2_stage_cal_s28dme.json
C=$(cat $L/maps/c_regions.txt); SU=$(cat $L/maps/su_regions.txt); OTH=$(cat $H/early_other_regions.txt)
IMG=openroad/orfs:latest; LIB=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
N=ht1qc3$(basename $B); mkdir -p $B
log(){ echo "$1 $(date "+%F %T")" >> $B/CHAIN.log; }
KARGS="--clock-cell inv2 --rep-um 250 --tree-site-legal --tree-site-slide --kit-workers 8 --tree-form link_htree --region-trees $MAP --feed $FEED --leaf-um 200 --tree-opt region_stub=1 --tree-opt dme_feed_centroid=1 --region-dme delay --region-dme-only $C,$SU,$OTH --region-dme-early 1.0 --region-dme-early-ff 0.87 --region-dme-stage-cal $CAL --region-dme-workers 24 --region-dme-snake $SU,$C --region-dme-early-merge-only $C --cell-paths"
log "START plan sha $(sha256sum $P | cut -c1-16) map $(sha256sum $MAP | cut -c1-12) feed $(sha256sum $FEED | cut -c1-12) cal $(sha256sum $CAL | cut -c1-12) dme c_* 192 + su_c 12 + early-other 36"
docker run --rm --name $N-kit --memory=96g --memory-swap=96g --cpus=24 -u 1000:1000 -v $B:$B -v $L:$L:ro -v $H:$H:ro -v $W:$W:ro $IMG bash -lc \
   "cd $W && python3 -B $S/die_trial.py kit $P --out $B/kit $KARGS > $B/kit.log 2>&1"
log "KIT $? $(tail -n 1 $B/kit.log | cut -c1-200)"
K=$B/kit
[ -s $K/clock/tree.json ] && [ -s $K/grt/route.v ] || { log FAIL_KIT; exit 2; }
grt(){ local O=$B/reg/grt_$1; mkdir -p $O/clk
  cp $K/clock/ctree.v $K/clock/tree.json $O/clk/; cp $K/clock/ctree.tcl $O/clk/ctree_ck89.tcl
  CORNER=$1 ADJ=0.75 ADJ7=0 python3 -I $MK $K $O/clk $O > $O/mk.log 2>&1 || return 1
  python3 -B $H/edge_readout_patch.py $S $K/clock/ctree.v $O/combo.tcl $1 >> $O/mk.log 2>&1 || return 1
  docker run --rm --name $N-reg-$1 --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$1 \
    -e LIBDIR=$LIB -v $K:/work:ro -v $O:/out $IMG \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$1.log 2>&1; echo EXIT \$? >> /out/combo_$1.log; chown -R 1000:1000 /out"; }
grt TT & grt FF & wait
for X in TT FF; do log "REG_GRT_$X $(tail -n 1 $B/reg/grt_$X/mk.log | cut -c1-80) $(grep -h -E "EXIT|GRT-0018|Maximum resident" $B/reg/grt_$X/combo_$X.log | tr "\n" " ") ovf $(grep -A14 "Final congestion report" $B/reg/grt_$X/combo_$X.log | grep "^Total" | tr -s " ")"; done
mkdir -p $B/reg/proof
for X in TT FF; do python3 -s -B $S/trial_tap_arrivals.py $K/clock/tree.json $B/reg/grt_$X/arr_$X.txt $X $B/reg/proof/tap_arrivals_$X.json --physical-paths > $B/reg/tta_$X.log 2>&1; log "REG_TTA_$X $? $(tail -n 1 $B/reg/tta_$X.log | cut -c1-200)"; done
# ---- gate (gate2.sh form) ----
R=$B/gate; RG=$B/reg; PR=$RG/proof; mkdir -p $R/run
ln -sfn $K/clock $R/run/clk; for X in TT FF; do ln -sfn $RG/grt_$X $R/run/out_$X; done
python3 -I $TI/s81_head/landed_phase_ocv.py $P $R/run --tools $S --clock-cell inv2 --out $R/lpo.json > $R/lpo.log 2>&1; log "LPO $? $(tail -n 2 $R/lpo.log | tr "\n" " " | cut -c1-300)"
F="--sta-proof $PR --sta-plan $P --sta-cppr-lca --sta-clock-cell inv2 --start-tree clock --start-clean width --max-depth 16 --mc-chips 300"
python3 $S/count_align_plan.py $R/lpo.json $F --out $R/ca_C.json > $R/ca_C.log 2>&1 &
python3 $S/count_align_plan.py $R/lpo.json $F --start-retime-up --out $R/ca_D.json > $R/ca_D.log 2>&1 &
python3 $S/count_align_plan.py $R/lpo.json $F --start-retime-up --start-lift --out $R/ca_E.json > $R/ca_E.log 2>&1 &
wait
SEL=""; BEST=999999
for V in C D E; do
  SM=$(python3 -I -c "
import json,collections;d=json.load(open('$R/ca_$V.json'));c=d['crossings'];s=d['summary']
ok=[x for x in c if x.get('rtl')]; f=len(c)-len(ok); dep=collections.Counter(x.get('depth') for x in ok)
amb=len(s.get('tree_edges_ambiguous') or [])
print(f'crossings {len(c)} FAIL {f} depth {dict(dep)} worst_lo {s.get(\"worst_margin_lo_ps\")} worst_hi {s.get(\"worst_margin_hi_ps\")} start_edges {s.get(\"tree_edges\")} clean {s.get(\"tree_edges_clean\")} AMB {amb} fall {s.get(\"tree_edges_fall\")} mc {s.get(\"mc\")}')
" 2>&1); log "CA_$V $SM"
  A=$(echo "$SM" | sed -n "s/.* FAIL 0 .* AMB \([0-9]*\) .*/\1/p")
  if [ -n "$A" ] && [ "$A" -lt "$BEST" ]; then BEST=$A; SEL=$V; fi
done
[ -n "$SEL" ] || { log NO_PLAN_WITHOUT_FAIL; SEL=none; }
if [ "$SEL" != none ]; then
  python3 $S/count_align_bind.py $R/ca_$SEL.json --samples 500 --out $R/bind.json > $R/bind.log 2>&1; log "BIND_$SEL $? $(tail -n 3 $R/bind.log | tr "\n" " " | cut -c1-300)"
  ( cd $S && python3 die_sta_related.py $PR --plan $P --out $R/sta --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell inv2 --count-align $R/bind.json --count-align-key part --kit-window-out $R/kitwin.json ) > $R/sta.log 2>&1; log "STA_$SEL $? $(grep -E "^proof|COUNT-ALIGN" $R/sta.log | tail -n 10 | tr "\n" " " | cut -c1-2200)"
fi
log CHAIN_DONE
