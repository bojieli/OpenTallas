#!/bin/bash
# L2H-GEN2D-FP 10-19 23:50: chain_d4g2d_post_fp.sh = chain_d4g2d_post_carrier2.sh on the WIDENED-CHANNEL floorplan (LEAD3-HBM 22:57:
# hb_dbk_NW/hc_NW/hb_dbk_SW/hc_SW/calendar_SW +43.2 um, hc_NE/hc_SE -43.2 um; claude/hd4g-gen2d-fp-1019).  Differences: W = wt/hd4g-gen2d-fp-1019,
# HSRC must equal its HEAD (grants/plan = GEN2c inputs + shift, so GEN uses the SAME placement inputs the forest planned on), prior run.tcl =
# the FP case_a run.tcl (PRIOR on PRH), FDS = the two real FP forests, COUT chosen per selected forest (COUTS basename=WxH), AP = post_fp_$TAG,
# remote B = gen2d_fp_$TAG, notes -> lanes/L2H-GEN2D-FP.md.
# L2H-GEN2D-RST 10-19 22:00: chain_d4g2d_post_carrier2.sh = chain_d4g2d_post_carrier.sh moved OFF ot-epyc4 (drained/HELD 18:35; ot-epyc8
# HELD 21:30): every remote step runs on RH (inputs staged there; GEN/GRT --dir on RH), synthesis src on SYNH hosts (OT_SYNTH_HOSTS),
# W = wt/hd4g-rstbound-1019 (HSRC 8670607dc = kits 5ddedcf7c with hbfd_rrl_c RTL 5ab727c0f + bounded reset router + synth host list),
# hbfd_rrl_c* SYNTH outline override from COUT (12.96x6.48 = the closed hard-view footprint for forests planned with relay_views_hard,
# 8.64x2.16 for the soft-LEF forests).  FDS = bounded forest variants (forest_var/run_var_bound.sh).
# L2H-GEN2D-RST 10-19 (LEAD2-HBM sub-lane): post-forest chain for the COMPACT CARRIER forest variants (forest_var/carr,
# carrhh = dedicated HBM reset carrier from corridor 154ae602c + compact planner for serial/stream; cplan = compact planner
# for all domains, structural fallback).  Copy of chain_d4g2d_post_rsthop.sh with: HSRC = claude/hd4g-rstcarrier-1019,
# TAG-specific AP/B dirs (two chains in parallel), hbfd_rrl_c.sv in FOREST_SRC_PATHS, 8.64x2.16 outline override for the
# hbfd_rrl_c* SYNTH views, notes -> lanes/L2H-GEN2D-RST.md, and a post-S8 die verdict (die_verdict.py) for H.GRT/H.STA/H.CLK.
# LH-RSTHOP 10-19: SIBLING of chain_d4g2d_post.sh (LH-GEN2CD, pid 612089, untouched) for the --host-hops forest variants
# (forest_var/hhpref, hhfb; source 1e3fbe31b = 15e069307 + reach hops hosted in lane relay stations, _rf/_rrf masters).
# Differences: W=wt/hd4g-rsthop, HSRC=1e3fbe31b, AP=post_rsthop, remote B=gen2d_rsthop (no shared remote dirs with the
# LH-GEN2CD chain), FDS = host-hop variants, rf RTL in FOREST_SRC_PATHS, outline override also for _rf/_rrf, notes -> LH-RSTHOP.
# LH-GEN2CD (LEAD-HBM sub-lane) 10-19 11:45: GEN2d POST-FOREST continuation of resume_forest_codex.sh (Codex durable waiter, source 9d5a2c350).
# The waiter only plans the relay-row reset forest. This script runs everything after it, source-bound to the SAME commit 9d5a2c350
# (worktree wt/hd4g-gen2d-post, branch claude/hd4g-gen2d-post-1019 = 9d5a2c350, contains gen2c b1e9a0734 + 70c8e927e + rstrow 92b6736eb
# + 16 closed _rr records):
#   W0 wait FOREST_RECOVERY_DONE (or waiter exit) -> P0 forest layer present? (else survey + exit 18)
#   S4 splice (d4g_relay_splice) + l12_banklat pads (LAT strict) + strict port bind + functional bind -> S6 synth views -> S7 GEN case (OT_RESET_GATE=fail)
#   -> S8 GRT + STA TT/FF + neighbour-skew clock gate + hold budget (case/run.sh).
# Steps are those of chain_d4g2d.sh (HBM-RSTROW), with: forest from forest_codex9d5a2c350, artifacts under $AP (post/),
# no --hosts pin (data locality via --dir that exists only on ot-epyc4), prior-place = recovered GEN2c case_a run.tcl.
set -o pipefail
TAG=${TAG:?TAG}; RH=${RH:?RH}; COUTS=${COUTS:?COUTS}; PRIOR=${PRIOR:?PRIOR}; PRH=${PRH:?PRH}; SYNH=${SYNH:-ot-epyc5,ot-epyc6,ot-epyc7,ot-epyc9}; export OT_SYNTH_HOSTS=$SYNH
W=/home/ubuntu/wt/hd4g-gen2d-fp-1019; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d; AP=$A/post_fp_$TAG; AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c
A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2; A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1
B=/srv/opentallas-scratch/claude/hd4g/gen2d_fp_$TAG; BC=/srv/opentallas-scratch/claude/hd4g/gen2c; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; HSRC=${HSRC:?HSRC}; FD=${FD:-$A/forest_codex9d5a2c350}; P=$B/forest_codex9d5a2c350
# LH-GEN2CD 11:35: forest_codex9d5a2c350 FAILED (hbm CN: no regional root home within reach after 40 sites). Re-plan variants
# (forest_var/run_var.sh, source 15e069307 = 9d5a2c350 + --max-root-tries + opt-in --overfly-masters, reach unchanged) -> run this with FD=<passing variant dir>.
LANE=/home/ubuntu/claude-takeover-20261007/lanes/L2H-GEN2D-FP.md
step() { echo "STEP $* $(date -Is)"; }
note() { echo "- [L2H-GEN2D-FP chain_post_fp_$TAG] $(date '+%m-%d %H:%M') $*" >> $LANE; }
mkdir -p $AP/net $AP/pbf; echo $$ > $AP/chain.pid; ssh -o ControlPath=none $RH "mkdir -p $B" || exit 9
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
# source binding: every archive / label uses $HSRC; the branch may only add this chain script (results/arch/hbm_die_d4g/gen2d_post/)
H=$HSRC; echo "HEAD $(git -C $W rev-parse --short=9 HEAD) SOURCE $H"
[ "$(git -C $W rev-parse HEAD)" = "$(git -C $W rev-parse $HSRC)" ] || { echo "SOURCE_DRIFT: HEAD != $HSRC"; exit 9; }
[ -z "$(git -C $W status --porcelain --untracked-files=no -- tools rtl results/arch physical)" ] || { echo DIRTY_WT; exit 9; }
step W0 wait_forest_layer
# FDS: candidate forest dirs (space separated, priority order); the first with a layer wins, give up when all have a report.
FDS=${FDS:?FDS}
while :; do
  for f in $FDS; do [ -s $f/layer.json.gz ] && { FD=$f; break 2; }; done
  done_all=1; for f in $FDS; do [ -s $f/report.json ] || done_all=0; done
  [ $done_all = 1 ] && { sleep 30; for f in $FDS; do [ -s $f/layer.json.gz ] && { FD=$f; break 2; }; done; FD=${FDS%% *}; break; }
  sleep 60
done
echo "FOREST_DIR $FD"
COUT=""; for kv in $COUTS; do [ "${kv%%=*}" = "$(basename $FD)" ] && COUT=${kv#*=}; done
[ -n "$COUT" ] || { echo "NO_COUT for $(basename $FD) in '$COUTS'"; exit 9; }; echo "COUT $COUT"
step P0 forest_layer
if [ ! -s $FD/layer.json.gz ]; then
  echo S4_FOREST_PLAN_FAIL; for f in $FDS; do echo "$f: $(head -c 600 $f/report.json)"; done
  note "S4_FOREST_PLAN_FAIL all variants ($FDS): structural H.RST planner/placement work needed (see reports)"; exit 18
fi
cd $W
step S4 splice_bind
ssh -o ControlPath=none $PRH "cat $PRIOR" | ssh -o ControlPath=none $RH "cat > $B/prior_run.tcl && test -s $B/prior_run.tcl" || { echo NO_PRIOR_RUN_TCL; exit 9; }
cp $AC/net/contract_pre.json $AP/net/contract_pre.json
python3 tools/hbm_die_v16/d4g_relay_splice.py $AP/net/contract_pre.json $FD/layer.json.gz $AP/net/contract_forest.json --report $AP/net/forest_splice.json \
  > $AP/net/forest_splice.log 2>&1 || { echo S4_FOREST_SPLICE_FAIL; tail -5 $AP/net/forest_splice.log; note "S4_FOREST_SPLICE_FAIL ($AP/net/forest_splice.log)"; exit 18; }
tail -1 $AP/net/forest_splice.log
# l12_banklat LAST (as GEN2e S8b; TW5-BANKLATDIE README: after the forest splice, pads take the endpoint's forest reset). At 9d5a2c350 the
# functional bind's LAT class is STRICT: GEN2c contract_pre alone fails 124 LAT clients (LH-GEN2CD smoke 11:50), so the pads are required.
step S4b l12_banklat
python3 tools/hbm_die_v16/d4g_layers/l12_banklat.py $AP/net/contract_forest.json $AP/net/contract.json --report $AP/net/l12_banklat.json \
  > $AP/net/l12.log 2>&1 || { echo S4B_L12_FAIL; tail -8 $AP/net/l12.log; note "S4B_L12_FAIL ($AP/net/l12.log)"; exit 18; }
tail -2 $AP/net/l12.log
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $AP/net/contract.json $AP/pbf > /dev/null; tail -1 $AP/pbf/port_bind.log
grep -q "^DIE_PORT_BIND PASS" $AP/pbf/port_bind.log || { echo S4_BIND_FAIL; grep '^FAIL' $AP/pbf/port_bind.log | head; note "S4_BIND_FAIL ($AP/pbf/port_bind.log)"; exit 18; }
python3 tools/hbm_die_v16/d4g_functional_bind.py $AP/net/contract.json --report $AP/pbf/functional_bind.json > $AP/pbf/functional_bind.log 2>&1
tail -3 $AP/pbf/functional_bind.log; grep -q "^FUNCTIONAL_BIND PASS" $AP/pbf/functional_bind.log || { echo S4_FUNCTIONAL_FAIL; note "S4_FUNCTIONAL_FAIL ($AP/pbf/functional_bind.log)"; exit 18; }
FOREST_SRC_PATHS="rtl/hbm_accel/die_glue/hbfd_rrl.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_pad.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/die_glue/hbfd_rly_rf_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rf.sv rtl/hbm_accel/die_glue/hbfd_rrl_c.sv"
synth_round() {   # $1 contract  $2 vplan dir  $3 tag
  rm -rf $2; python3 tools/hbm_die_v15/v16_views.py --out $2 --contract $1 | tail -3
  rm -rf $AP/synmeta_$3; mkdir -p $AP/synmeta_$3
  for Q in $A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth; do [ -d $Q ] && (cd $Q && tar -cf - */meta.json 2>/dev/null) | tar -x -C $AP/synmeta_$3; done
  python3 tools/hbm_die_v16/synth_reuse_r8b.py --views $2 --metas $AP/synmeta_$3 --root $W --out $AP/reuse_$3.json --prev $AC/vplan_pre > $AP/reuse_$3.log; tail -3 $AP/reuse_$3.log | cut -c1-600
  CELLS=$(grep '^SYNTH ' $AP/reuse_$3.log | cut -d' ' -f2-)
  python3 - $2 > $AP/src_paths_$3.txt <<PY
import json, sys
V=json.load(open(sys.argv[1] + '/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/hbm_mtp/rtl','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016','results/arch/hbm_native_1013/sm_own_logic/retention_cell_models.sv'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
print('\n'.join(sorted(p)))
PY
  (grep -v -e "^#" -e "^ *$" $AC/views/extra_src_paths.txt 2>/dev/null; for x in $FOREST_SRC_PATHS; do echo $x; done) >> $AP/src_paths_$3.txt
  sort -u -o $AP/src_paths_$3.txt $AP/src_paths_$3.txt
  ssh -o ControlPath=none $RH "rm -rf $B/src_$H" || return 15
  git -C $W archive $HSRC $(cat $AP/src_paths_$3.txt) | ssh -o ControlPath=none $RH "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || return 15
  tar -C $2/wrap -cf - . | ssh -o ControlPath=none $RH "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || return 15
  for h in ${SYNH//,/ }; do [ $h = $RH ] && continue; ssh -o ControlPath=none $RH "tar -C $B -cf - src_$H" | ssh -o ControlPath=none $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
  N0=$(ssh -o ControlPath=none $RH "find $B/src_$H | wc -l")
  for h in ${SYNH//,/ }; do [ $h = $RH ] && continue; n=$(ssh -o ControlPath=none $h "find $B/src_$H 2>/dev/null | wc -l"); echo "SRC $h $n/$N0"
    [ "$n" != "$N0" ] && ssh -o ControlPath=none $h "rm -rf $B/src_$H" && echo "REMOVED_PARTIAL $h"; done
  echo "SYNTH_$3 $CELLS"
  if [ -n "${CELLS// /}" ]; then
    (cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $2 --commit $H --remote-root $B $CELLS > $AP/drive_$3.log 2>&1); tail -2 $AP/drive_$3.log
    python3 $W/tools/hbm_die_v15/v16_fetch.py --views $2 --remote-root $B --commit $H --contract $1 $CELLS > $AP/fetch_$3.log 2>&1; echo "FETCH rc=$?"; tail -3 $AP/fetch_$3.log
    MISS=""; for c in $CELLS; do [ -f $2/synth/$c/meta.json ] || MISS="$MISS $c"; done
    [ -n "$MISS" ] && { echo "SYNTH_MISSING_$3$MISS (no stubs: every SYNTH view needed)"; return 16; }
  fi
  return 0
}
views_up() {
  ssh -o ControlPath=none $RH "rm -rf $B/views && mkdir -p $B/views/synth" || return 17
  for Q in $A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth $1/synth; do
    [ -d $Q ] && rsync -a $Q/ $RH:$B/views/synth/; done
  scp -q $1/views.json $RH:$B/views/ && scp -q $2 $RH:$B/views/contract.json || return 17
}
step S6 views_synth_final
synth_round $AP/net/contract.json $AP/vplan d || { rc=$?; note "S6 synth FAIL rc=$rc ($AP/drive_d.log, fetch_d.log)"; exit $rc; }
python3 -c "
import json,collections; v=json.load(open('$AP/vplan/views.json')); print('VIEW_KINDS', dict(collections.Counter(x['kind'] for x in v.values())))"
python3 tools/hbm_die_v16/d4g_bindings.py --views $AP/vplan/views.json --grants $D/grants_d4g.json --out $AP/view_bindings.json
OVR=$(COUT=$COUT python3 - $AP/vplan/views.json <<'PY'
import json, re, sys, glob
V = json.load(open(sys.argv[1])); out = []
for c, v in sorted(V.items()):
    m = v.get('master', '')
    mm = re.match(r'(hbfd_rly_\d+_[A-Z]{2})_(rr|rf|rrf)$', m)
    if v.get('kind') == 'SYNTH' and re.match(r'hbfd_rrl_c(sync|hop|pad\d+)$', m):
        out.append(f'{c}=' + __import__('os').environ['COUT'])   # L2H-GEN2D-RST carrier tile: planning outline of the bound forest
    elif v.get('kind') == 'SYNTH' and mm:
        lef = glob.glob(f'physical/**/views/{mm.group(1)}/{mm.group(1)}.lef', recursive=True)
        s = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', open(sorted(lef)[0]).read())
        out.append(f'{c}={s.group(1)}x{s.group(2)}')
print(','.join(out))
PY
)
echo "RR_OUTLINE_OVERRIDE ${OVR:-none}"
export OT_DIE_CASE_EXTRA="${OVR:+--outline-override $OVR }--prior-place $B/prior_run.tcl"
step S7 gen2d
views_up $AP/vplan $AP/net/contract.json || exit 17
sed 's#--diagnostic-param-alias#--diagnostic-param-alias ${OT_DIE_CASE_EXTRA}#' $A2/gen_d4g2.sh > $AP/gen_d4g2d.sh
scp -q $AP/gen_d4g2d.sh $RH:$B/gen_d4g2d.sh && ssh -o ControlPath=none $RH "mkdir -p $B/loc_gen_$H" || exit 17
$OTRUN --mem 64 --threads 2 --disk 10 --priority die --dir $B/loc_gen_$H -- env OT_ABS_PIN_WINDOW_UM=3 OT_GEN2_CASE=case OT_RESET_GATE=fail \
  OT_DIE_CASE_EXTRA="$OT_DIE_CASE_EXTRA" bash $B/gen_d4g2d.sh > $AP/gen.otrun 2>&1; echo "GEN ot-run rc=$? $(date -Is)"; tail -20 $AP/gen.otrun
scp -q $RH:$B/case/layout.png $AP/gen2d_layout.png 2>/dev/null
grep -q GEN_OK $AP/gen.otrun || { note "S7 GEN2d FAIL: $(grep -v '^ot-' $AP/gen.otrun | tail -3 | tr '\n' ' ' | cut -c1-300)"; exit 17; }
scp -q $RH:$B/overreach.json $RH:$B/case/placement_coverage.json $AP/ 2>/dev/null
ssh -o ControlPath=none $RH "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label','flags')}, default=str)[:20000])\"" > $AP/gen_manifest_summary.json
note "S7 GEN2d GEN_OK -> S8 GRT/STA/CLK launched; LOOK at $AP/gen2d_layout.png"
step S8 grt_sta_clk
$OTRUN --mem 160 --threads 16 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $AP/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh -o ControlPath=none $RH "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log; tail -5 $B/case/out/hold_budget.log" > $AP/grt_summary.txt 2>&1
rsync -a $RH:$B/case/out/ $AP/case_out/ --include='*.json' --include='*.log' --include='*.rpt' --include='*.png' --exclude='*.odb' --exclude='*.def' 2>/dev/null
cat $AP/grt_summary.txt
note "S8 done: $AP/grt_summary.txt (GRT overflow / TT setup / FF hold / neighbour skew) -> classify, update H.GRT/H.STA/H.CLK"
step S9 die_verdict
scp -q $W/results/arch/hbm_die_d4g/rstcarrier/die_verdict.py $RH:$B/die_verdict.py
ssh -o ControlPath=none $RH "python3 -I $B/die_verdict.py $B/case $B/case/out/die_verdict.json" > $AP/die_verdict.log 2>&1; cat $AP/die_verdict.log
scp -q $RH:$B/case/out/die_verdict.json $AP/die_verdict.json 2>/dev/null
note "S9 die verdict: $(tail -1 $AP/die_verdict.log | cut -c1-300) ($AP/die_verdict.json; stand-ins labelled)"
echo CHAIN_D4G2D_POST2_DONE HEAD=$H TAG=$TAG FD=$FD
