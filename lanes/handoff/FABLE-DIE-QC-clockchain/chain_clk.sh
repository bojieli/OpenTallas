#!/bin/bash
# FABLE-DIE-QC 11-17 chain_clk.sh: host-portable QC die clock proof (= FABLE-DIE-QC-R chain_n.sh / QC-PLAN-R3 chain_n3clk.sh, same steps).
# die_trial kit (comb feed, per-type region tree OT_CLK_DME_TEMPLATE=2) -> combo die GRT 50 it TT+FF -> exact-length clock SPEF
# readout -> tap arrivals -> die_sta_related (TAP-OFFSET-GATE, kitoffs.json, kitwin.json) -> LPO + count_align_plan C/D + bind + STA.
# usage: [R=lane dir] [E=event tree] [P=plan.json] [MB=inputs dir with maps/ m/] [TA=extra ro mount] chain_clk.sh NAME
# Inputs (MB) come from lanes/handoff/FABLE-DIE-QC-clockchain/ (coord); for a plan with new partition names run
# clockchain_inputs.py PLAN MB NEW_MB first.  Read: $D/CHAIN.log, $D/reg/sta.log (TAP-OFFSET-GATE), $D/reg/kitoffs.json.
set -u; export PYTHONDONTWRITEBYTECODE=1; cd /
R=${R:-/srv/opentallas-scratch2/claude/fable-die-qc-clk}; B=$R/chain; MB=${MB:-$R/in}; M=$MB/maps; SMB=${SMB:-$R/src5}
E=${E:?event tree}; TA=${TA:-$E}
S=$SMB/tools/die_plan; TI=$SMB/tools; SM=$SMB/tools/die_plan; export OT_DIE_PLAN_TOOLS=$S
P=${P:?plan json}; PD=$(dirname $P)
D=$B/qc/${1:?name}; mkdir -p $D; MK=$M/mk_combo_kv.py
MAP=$M/regions_s3d.json; FEED=${FEED_JSON:-$MB/m/feed_comb_fw_3.json}; CAL=$M/inv2_stage_cal_s28dme.json; LE=${LE:-15}
C=$(cat $M/c_regions.txt); SU=$(cat $M/su_regions.txt); OTH=$(cat $M/early_other_regions.txt)
IMG=openroad/orfs:latest; LIB=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; N=fdqr$(basename $D)
log(){ echo "$1 $(date "+%F %T")" >> $D/CHAIN.log; }
KARGS="--clock-cell inv2 --rep-um 250 --tree-site-legal --tree-site-slide --kit-workers 8 --tree-form link_htree --region-trees $MAP --feed $FEED --leaf-um 200 --tree-opt region_stub=1 --tree-opt dme_feed_centroid=1 --region-dme delay --region-dme-only $C,$SU,$OTH --region-dme-early 1.0 --region-dme-early-ff 0.87 --region-dme-stage-cal $CAL --region-dme-workers 24 --region-dme-snake $SU,$C --region-dme-early-merge-only $C --cell-paths"
for f in $MAP $FEED $CAL $MK $M/edge_readout_patch.py $M/c_regions.txt $M/su_regions.txt $M/early_other_regions.txt $S/die_trial.py $S/clock_spef.py; do [ -s $f ] || { log "FAIL_INPUT $f"; exit 3; }; done
log "START clock proof $1 (FABLE-DIE-QC chain_clk) host $(hostname) plan $P sha $(sha256sum $P | cut -c1-12) tree $E tools $SMB template=2 feed $(sha256sum $FEED | cut -c1-12) map $(sha256sum $MAP | cut -c1-12) cal $(sha256sum $CAL | cut -c1-12) LE $LE"
if [ ! -s $D/kit/grt/route.v ]; then
docker run --rm --name $N-kit -e OT_CLK_DME_TEMPLATE=2 --memory=96g --memory-swap=96g --cpus=24 -u 1000:1000 -v $B:$B -v $SMB:$SMB:ro -v $MB:$MB:ro -v $E:$E:ro -v $TA:$TA:ro -v $PD:$PD:ro $IMG bash -lc \
   "cd $E && python3 -B $S/die_trial.py kit $P --out $D/kit $KARGS > $D/kit.log 2>&1"
log "KIT $? $(tail -n 1 $D/kit.log | cut -c1-300) | $(grep -h "template:" $D/kit.log | tail -n 1)"
fi
K=$D/kit; [ -s $K/clock/tree.json ] && [ -s $K/grt/route.v ] || { log FAIL_KIT; exit 2; }
grt(){ local O=$D/reg/grt_$1; mkdir -p $O/clk
  cp $K/clock/ctree.v $K/clock/tree.json $O/clk/; cp $K/clock/ctree.tcl $O/clk/ctree_ck89.tcl
  CORNER=$1 ADJ=0.75 ADJ7=0 python3 -I $MK $K $O/clk $O > $O/mk.log 2>&1 || return 1
  python3 -B $M/edge_readout_patch.py $S $K/clock/ctree.v $O/combo.tcl $1 >> $O/mk.log 2>&1 || return 1
  docker run --rm --name $N-reg-$1 --memory=48g --memory-swap=48g --cpus=8 -e CORNER=$1 -e LIBDIR=$LIB -v $K:/work:ro -v $O:/out $IMG \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; /usr/bin/time -v openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$1.log 2>&1; echo EXIT \$? >> /out/combo_$1.log; chown -R 1000:1000 /out"; }
spef(){ local O=$D/reg/spef_$1 G=$D/reg/grt_$1; mkdir -p $O; ln -f $G/combo.v $O/combo.v; ln -f $D/reg/clock.spef $O/clock.spef
  python3 -I - <<PY || return 1
t=open("$G/combo.tcl").read()
a=t.index("if {[catch {global_route"); b=t.index("source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl")
t=t[:a]+t[b:]
assert t.count("estimate_parasitics -global_routing")==1
open("$O/combo.tcl","w").write(t.replace("estimate_parasitics -global_routing","read_spef /out/clock.spef\nreport_parasitic_annotation"))
PY
  docker run --rm --name $N-spef-$1 --memory=40g --memory-swap=40g --cpus=8 -e CORNER=$1 -e LIBDIR=$LIB -v $K:/work:ro -v $O:/out $IMG \
    bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 8 -exit /out/combo.tcl > /out/combo_$1.log 2>&1; echo EXIT \$? >> /out/combo_$1.log; chown -R 1000:1000 /out"; }
if [ ! -s $D/reg/spef_FF/arr_FF.txt ]; then
grt TT & grt FF & wait
for X in TT FF; do log "REG_GRT_$X $(grep -h -E "EXIT|GRT-0018|Maximum resident" $D/reg/grt_$X/combo_$X.log | tr "\n" " ") ovf $(grep -A14 "Final congestion report" $D/reg/grt_$X/combo_$X.log | grep "^Total" | tr -s " ")"; done
python3 -I $R/bin/detour2.py $K $D/reg/grt_TT/route_TT.guide > $D/reg/detour.log 2>&1; log "DETOUR $? $(tail -n 2 $D/reg/detour.log | tr "\n" " " | cut -c1-300)"
python3 -I $S/clock_spef.py $K/clock/ctree.v $K/clock/tree.json $D/reg/clock.spef --pin-escape-um $LE > $D/reg/spef.log 2>&1; log "SPEF $? $(tail -n 1 $D/reg/spef.log)"
spef TT & spef FF & wait
for X in TT FF; do log "REG_SPEF_$X $(grep -h -E "EXIT|unannotated" $D/reg/spef_$X/combo_$X.log | tr "\n" " ")"; done
fi
mkdir -p $D/reg/proof $D/reg/proof_grt
for X in TT FF; do python3 -s -B $S/trial_tap_arrivals.py $K/clock/tree.json $D/reg/grt_$X/arr_$X.txt $X $D/reg/proof_grt/tap_arrivals_$X.json --physical-paths > $D/reg/ttag_$X.log 2>&1
  python3 -s -B $S/trial_tap_arrivals.py $K/clock/tree.json $D/reg/spef_$X/arr_$X.txt $X $D/reg/proof/tap_arrivals_$X.json --physical-paths > $D/reg/tta_$X.log 2>&1; log "REG_TTA_$X $? $(tail -n 1 $D/reg/tta_$X.log | cut -c1-200)"; done
python3 -I $R/bin/tol.py $P $D/reg/proof_grt $D/reg/proof > $D/reg/tol.log 2>&1; log "TOL $(grep -v worst $D/reg/tol.log | tr "\n" " " | cut -c1-700)"
( cd $SM && nice python3 -s -B die_sta_related.py $D/reg/proof --plan $P --out $D/reg/sta --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell inv2 --kit-window-out $D/reg/kitwin.json --kit-offset-out $D/reg/kitoffs.json ) > $D/reg/sta.log 2>&1
log "REG_STA $? $(grep -E "^proof|TAP-OFFSET-GATE" $D/reg/sta.log | grep -v RESIGN | tr "\n" " " | cut -c1-1500)"
log REG_DONE
R2=$D/gate; PR=$D/reg/proof; mkdir -p $R2/run
ln -sfn $K/clock $R2/run/clk; for X in TT FF; do ln -sfn $D/reg/spef_$X $R2/run/out_$X; done
python3 -I $TI/s81_head/landed_phase_ocv.py $P $R2/run --tools $SM --clock-cell inv2 --out $R2/lpo.json > $R2/lpo.log 2>&1; log "LPO $? $(tail -n 2 $R2/lpo.log | tr "\n" " " | cut -c1-300)"
F="--sta-proof $PR --sta-plan $P --sta-cppr-lca --sta-clock-cell inv2 --start-tree clock --start-clean width --max-depth 16 --mc-chips 300"
python3 $SM/count_align_plan.py $R2/lpo.json $F --out $R2/ca_C.json > $R2/ca_C.log 2>&1 &
python3 $SM/count_align_plan.py $R2/lpo.json $F --start-retime-up --out $R2/ca_D.json > $R2/ca_D.log 2>&1 &
wait
SEL=""; BEST=999999
for V in C D; do
  SMY=$(python3 -I -c "
import json,collections;d=json.load(open('$R2/ca_$V.json'));c=d['crossings'];s=d['summary']
ok=[x for x in c if x.get('rtl')]; f=len(c)-len(ok); dep=collections.Counter(x.get('depth') for x in ok)
amb=len(s.get('tree_edges_ambiguous') or [])
print(f'crossings {len(c)} FAIL {f} depth {dict(dep)} worst_lo {s.get(\"worst_margin_lo_ps\")} worst_hi {s.get(\"worst_margin_hi_ps\")} start_edges {s.get(\"tree_edges\")} clean {s.get(\"tree_edges_clean\")} AMB {amb} fall {s.get(\"tree_edges_fall\")} mc {s.get(\"mc\")}')
" 2>&1); log "CA_$V $SMY"
  A=$(echo "$SMY" | sed -n "s/.* FAIL 0 .* AMB \([0-9]*\) .*/\1/p")
  if [ -n "$A" ] && [ "$A" -lt "$BEST" ]; then BEST=$A; SEL=$V; fi
done
[ -n "$SEL" ] || { log NO_PLAN_WITHOUT_FAIL; SEL=none; }
if [ "$SEL" != none ]; then
  python3 $SM/count_align_bind.py $R2/ca_$SEL.json --samples 500 --out $R2/bind.json > $R2/bind.log 2>&1; log "BIND_$SEL $? $(tail -n 3 $R2/bind.log | tr "\n" " " | cut -c1-300)"
  ( cd $SM && python3 die_sta_related.py $PR --plan $P --out $R2/sta --corner TT --corner FF --core-insertion declared --cppr-lca --clock-cell inv2 --count-align $R2/bind.json --count-align-key part --kit-window-out $R2/kitwin.json --kit-offset-out $R2/kitoffs.json ) > $R2/sta.log 2>&1; log "STA_$SEL $? $(grep -E "^proof|COUNT-ALIGN|TAP-OFFSET-GATE" $R2/sta.log | grep -v RESIGN | tail -n 12 | tr "\n" " " | cut -c1-2500)"
fi
log CHAIN_DONE
