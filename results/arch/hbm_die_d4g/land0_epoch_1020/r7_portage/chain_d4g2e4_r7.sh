#!/bin/bash
# HBM-DIE7 10-20 RUN 7 = RUN 6 + PORT-AGE (0ae60e322: equal-age pads for one producer port split over rows; l7 G-CIL-RC fix)
# HBM-DIE7 10-20 RUN 6 (GEN2e4 release die): r5codex S5 (source 27a01b34d, strict 59,994/199 unread0, LEAD 2a0f4791) FAILED the
#  5.050 relay lockstep: hbfd_land0 (zero-hop forwarded landing) FIRST=1 registers en before the hop-0 gate -> write epoch +1 edge,
#  but relay_layer_d4f.py still strapped K = ceil(N/2)+E (the pre-en-register basis) -> rf0044/rf0045/... sinks read the wrong ring
#  slot (6275 errors, 2758 landing-fault cycles; every mutant failed at the same rf0044 witness = non-discriminating).
#  Fix at the generator (codex e03558505, branch claude/hbm-gen2e4r6-land0-1020): K = ceil(N/2)+E+(N==0) for the 42 zero-hop
#  tiles (84 strap bits); trees/clocks/resets/data/latency unchanged.  S5 + S5b ran remotely (resume_s5_r6_remote.sh, B below).
#  This driver: waits lockstep GATE PASS (local) + remote S5B_DONE, then S6 synth_b -> S7 case_b -> S8 forest -> S9 -> S10 GEN fail
#  -> S11 GRT + STA + clock (r5 chain body unchanged).  WT /home/ubuntu/wt/hbm-die7-r6 pinned at e03558505: never commit in it.
set -o pipefail
HOST=ot-epyc6; AE=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e
W=/home/ubuntu/wt/hbm-die7-r6; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r7portage; AE4=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4; AE3=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e3; AE2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e2; R=/home/ubuntu/OpenTallas
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1; A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c; AD=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d
B=/srv/opentallas-scratch/claude/hbm-die7-gen2e4r6-1020; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; BR=claude/hbm-gen2e4r6-land0-1020; GR=$D/gen2e4r_1020/grants_d4g.json
step() { echo "STEP $* $(date -Is)"; }
echo $$ > $A/chain.pid; echo RUN7_HBM-DIE7
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
cd $W
H=$(git -C $W rev-parse --short=9 HEAD); echo "CHAIN chain_d4g2e4.sh (L2H-GEN2E: GEN2e3 + l21 + l22 FAN32/MC3 + exact-tail classes) HEAD $H $(date -Is)"
ssh $HOST "mkdir -p $B" || exit 9
FOREST_SRC_PATHS="rtl/hbm_accel/die_glue/hbfd_rrl.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_pad.sv rtl/hdc/ot_hdc_delay.sv"
METAS="$A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth $AD/vplan/synth $AE/vplan_a/synth $AE2/vplan_a/synth $AE3/vplan_a/synth $AE4/vplan_a_run3/synth $AE4/vplan_a_run4/synth"
bind2() {   # $1 contract  $2 out dir  $3 tag -> strict port bind + functional bind (LAT strict when l12 is in)
  mkdir -p $2; bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $1 $2 > /dev/null; tail -1 $2/port_bind.log
  if ! grep -q "^DIE_PORT_BIND PASS" $2/port_bind.log; then
    # strict main tool: every structural class must be 0; unread_net_bits alone is recorded (held, ROOT manifest scope d517 only)
    python3 - $2/port_bind.json > $2/bind_classes.log <<'PY' || { echo "$3_BIND_FAIL"; cat $2/bind_classes.log; grep '^FAIL' $2/port_bind.log | head; return 1; }
import json, sys
r = json.load(open(sys.argv[1])); bad = [f for f in r.get('failing', []) if f != 'unread_net_bits']
print('BIND_STRUCTURAL', 'PASS' if not bad else 'FAIL', 'failing', r.get('failing'), 'unread_net_bits', r['summary'].get('unread_net_bits'))
sys.exit(1 if bad or not r.get('failing') else 0)
PY
    echo "$3_BIND_STRUCTURAL_PASS_UNREAD_HELD $(cat $2/bind_classes.log) -> DIAGNOSTIC (strict unread FAIL recorded, not waived)"
  fi
  python3 tools/hbm_die_v16/d4g_functional_bind.py $1 --report $2/functional_bind.json $4 > $2/functional_bind.log 2>&1
  tail -3 $2/functional_bind.log; grep -q "^FUNCTIONAL_BIND PASS" $2/functional_bind.log || { echo "$3_FUNCTIONAL_FAIL"; return 1; }
  python3 tools/hbm_die_v15/check_contract_modules.py --contract $1 --rev HEAD --json $2/contract_modules_check.json > $2/cmc.log 2>&1; tail -1 $2/cmc.log
  return 0
}
strict_manifest() {   # $1 contract  $2 bind dir (die.v + port_bind.json from bind2)  $3 tag -> transfer -> propose -> replay
  local U=$A/unread/$3; mkdir -p $U
  python3 tools/hbm_die_v16/unread_l21_transfer.py $REV0 $2/die.v $1 $2/port_bind.json $H $U/review.json > $U/transfer.log 2>&1 \
    || { echo "$3_UNREAD_TRANSFER_REFUSED"; tail -2 $U/transfer.log; return 1; }
  tail -1 $U/transfer.log
  local X=$(python3 -c "
import json,gzip; p='$1'; c=json.load(gzip.open(p,'rt') if p.endswith('.gz') else open(p))
print(' '.join(sorted({'--rtl-file '+f for i in c['instances'].values() for f in [i['source']]+(i.get('rtl_deps') or [])
      if f.startswith('rtl/hbm_accel/die_glue/scoped_d4g/') or not (f.startswith('rtl/') or '/rtl/' in f)})))")
  python3 tools/die_port_bind.py $2/die.v --top hbm_v16_die $X --allow-model ot_hbm3e_phy_rc_e8p5 --allow-model ot_hbm_pll_bb \
    --rtl-root rtl --rtl-root physical/hbm_mtp/rtl --rtl-root physical/hbm_accel_die_views/common --rtl-root physical/hbm_accel_die_views/quant/rtl \
    --rtl-root physical/hbm_generic/argmax18/rtl --rtl-root physical/hbm_xp_aq_tree13_1014 --lib-root physical/asap7_memory_macros --lib-root physical/asap7_memory_macros_v2 \
    --define OT_SMH_FC_HIER --strap-file $2/straps.json --pad-file $2/die.v.pads.json --unread-review $U/review.json --unread-contract $1 \
    --unread-proposal-out $U/manifest_proposal.json --out $U/proposal_bind.json > $U/proposal.log 2>&1 || { echo "$3_UNREAD_PROPOSAL_REFUSED"; tail -2 $U/proposal.log; return 1; }
  local S=$(sha256sum $U/manifest_proposal.json | cut -d' ' -f1); echo "$3_UNREAD_PROPOSAL $S"
  bash tools/hbm_die_v16/d4g_layers/l21_strict_replay.sh $1 $U/replay $U/review.json $U/manifest_proposal.json $S > $U/replay.out 2>&1; local rc=$?
  tail -1 $U/replay.out; [ $rc = 0 ] && echo "$3_STRICT_PASS_WITH_PROPOSAL $S (LEAD digest admission pending)" || echo "$3_STRICT_FAIL_WITH_PROPOSAL $S"
  return $rc
}
synth_round() {   # $1 contract  $2 vplan dir  $3 tag  $4 prev vplan
  rm -rf $2; python3 tools/hbm_die_v15/v16_views.py --out $2 --contract $1 | tail -3
  rm -rf $A/synmeta_$3; mkdir -p $A/synmeta_$3
  for P in $METAS $A/vplan_a/synth $A/vplan_b/synth; do [ -d $P ] && [ "$P" != "$2/synth" ] && (cd $P && tar -cf - */meta.json 2>/dev/null) | tar -x -C $A/synmeta_$3; done
  python3 tools/hbm_die_v16/synth_reuse_r8b.py --views $2 --metas $A/synmeta_$3 --root $W --out $A/reuse_$3.json --prev $4 > $A/reuse_$3.log; tail -3 $A/reuse_$3.log | cut -c1-600
  CELLS=$(grep '^SYNTH ' $A/reuse_$3.log | cut -d' ' -f2-)
  python3 - $2 > $A/src_paths_$3.txt <<PY
import json, sys
V=json.load(open(sys.argv[1] + '/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/hbm_mtp/rtl','physical/hbm_pll_views','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016','results/arch/hbm_native_1013/sm_own_logic/retention_cell_models.sv'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
print('\n'.join(sorted(p)))
PY
  (grep -v -e "^#" -e "^ *$" $AC/views/extra_src_paths.txt 2>/dev/null; for x in $FOREST_SRC_PATHS; do [ -e $x ] && echo $x; done) >> $A/src_paths_$3.txt
  sort -u -o $A/src_paths_$3.txt $A/src_paths_$3.txt
  ssh $HOST "rm -rf $B/src_$H" || return 15
  git -C $W archive HEAD $(cat $A/src_paths_$3.txt) | ssh $HOST "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || return 15
  tar -C $2/wrap -cf - . | ssh $HOST "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || return 15
  for h in ot-epyc5 ot-epyc7 ot-epyc9 ot-pve1; do ssh $HOST "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
  N0=$(ssh -o ControlPath=none $HOST "find $B/src_$H | wc -l")
  for h in ot-epyc5 ot-epyc7 ot-epyc9 ot-pve1; do n=$(ssh -o ControlPath=none $h "find $B/src_$H 2>/dev/null | wc -l"); echo "SRC $h $n/$N0"
    [ "$n" != "$N0" ] && ssh -o ControlPath=none $h "rm -rf $B/src_$H" && echo "REMOVED_PARTIAL $h"; done
  echo "SYNTH_$3 $CELLS"
  if [ -n "${CELLS// /}" ]; then
    (cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $2 --commit $H --remote-root $B $CELLS > $A/drive_$3.log 2>&1); tail -2 $A/drive_$3.log
    python3 $W/tools/hbm_die_v15/v16_fetch.py --views $2 --remote-root $B --commit $H --contract $1 $CELLS > $A/fetch_$3.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch_$3.log
    MISS=""; for c in $CELLS; do [ -f $2/synth/$c/meta.json ] || MISS="$MISS $c"; done
    [ -n "$MISS" ] && { echo "SYNTH_MISSING_$3$MISS (no stubs: every SYNTH view needed)"; return 16; }
  fi
  python3 -c "
import json,collections; v=json.load(open('$2/views.json')); print('VIEW_KINDS_$3', dict(collections.Counter(x['kind'] for x in v.values())))"
  return 0
}
views_up() {      # $1 vplan dir  $2 contract  -> $B/views (all earlier synth overlays, own last)
  ssh $HOST "rm -rf $B/views && mkdir -p $B/views/synth" || return 17
  for P in $METAS $A/vplan_a/synth $A/vplan_b/synth $1/synth; do [ -d $P ] && rsync -a $P/ $HOST:$B/views/synth/; done
  scp -q $1/views.json $HOST:$B/views/ && scp -q $2 $HOST:$B/views/contract.json || return 17
}
gen() {   # $1 case name  $2 reset gate  $3 extra die_case args  -> $A/gen_$1.otrun
  sed -e 's#--diagnostic-param-alias#--diagnostic-param-alias ${OT_DIE_CASE_EXTRA}#' -e "s#--grants \$D/grants_d4g.json#--grants $GR#" $A2/gen_d4g2.sh > $A/gen_d4g2e.sh
  grep -q -- "--grants $GR" $A/gen_d4g2e.sh || { echo GEN_SCRIPT_GRANTS_NOT_SET; return 1; }
  scp -q $A/gen_d4g2e.sh $HOST:$B/gen_d4g2e.sh || return 17
  $OTRUN --mem 64 --threads 2 --disk 10 --priority die --dir $B/views -- env OT_ABS_PIN_WINDOW_UM=3 OT_GEN2_CASE=$1 OT_RESET_GATE=$2 \
    OT_DIE_CASE_EXTRA="$3" bash $B/gen_d4g2e.sh > $A/gen_$1.otrun 2>&1; echo "GEN_$1 ot-run rc=$? $(date -Is)"; tail -12 $A/gen_$1.otrun
  grep -q GEN_OK $A/gen_$1.otrun || return 1
  scp -q $HOST:$B/$1/manifest.json $A/$1_manifest.json; scp -q $HOST:$B/$1/layout.png $A/$1_layout.png 2>/dev/null
  scp -q $HOST:$B/$1/run.tcl $A/$1_run.tcl 2>/dev/null
  python3 -c "
import json; m=json.load(open('$A/$1_manifest.json')); h=m.get('homes',{})
gen=[(n,v['rule'][:40],v.get('dist_um')) for n,v in h.items() if not v['rule'].startswith(('planned relay','relay chain','region','grant slot','prior home','lane row'))]
print('GENERATED_HOMES_$1', len(gen), sorted(gen, key=lambda t:-(t[2] or 0))[:12]); print('PROBLEMS', len(m.get('placement_problems',[])))"
  return 0
}
REV0=$W/results/arch/hbm_unread_gen2e3_1019/l21/review_l21_candidate.json
[ "$H" = 0ae60e322 ] || { echo SOURCE_HEAD_DRIFT $H; exit 9; }
# ---------------- wait: lockstep gate + remote S5/S5b ----------------
step WAIT lockstep_s5b
while ! grep -q "RELAY_LOCKSTEP_GATE" $A/lockstep_land.log 2>/dev/null; do sleep 60; done
grep -q "RELAY_LOCKSTEP_GATE PASS" $A/lockstep_land.log || { echo S5_LOCKSTEP_FAIL; tail -12 $A/lockstep_land.log; exit 15; }
while ! ssh -o ControlPath=none -o ConnectTimeout=20 $HOST "test -f $B/S5B_DONE_$H"; do
  grep -qE "_FAIL |_FAIL$|SOURCE_HEAD_DRIFT|RAN on .*exit [1-9]" $A/s5_r7.otrun && { echo S5_REMOTE_FAIL; tail -8 $A/s5_r7.otrun; exit 16; }
  sleep 120; done
mkdir -p $A/net $A/pb $A/pb5b $A/unread
rsync -a $HOST:$B/artifacts_$H/net/ $A/net/ && rsync -a $HOST:$B/artifacts_$H/pb/ $A/pb/ && rsync -a $HOST:$B/artifacts_$H/pb5b/ $A/pb5b/ && rsync -a $HOST:$B/artifacts_$H/unread/ $A/unread/ || exit 16
grep -h "STRICT_PASS_WITH_PROPOSAL" $A/s5_r7.otrun
# ---------------- S6 / S7 post-landing case (forest basis) ----------------
step S6 synth_b
synth_round $A/net/contract_pre.json $A/vplan_b b $A/vplan_a || exit $?
step S7 gen2e_case_b_postlanding
views_up $A/vplan_b $A/net/contract_pre.json || exit 17
scp -q $AE4/case_a_run.tcl $HOST:$B/prior_case_a.tcl || exit 17
gen case_b diag "--prior-place $B/prior_case_a.tcl" || { echo S7_GEN_B_FAIL; exit 17; }
# ---------------- S8 relay-row reset forest (RSTROW Proposal A) ----------------
step S8 rowforest_plan_splice
P=$B/forest; ssh $HOST "rm -rf $P && mkdir -p $P/relay_views && cp -al $B/case_b/views $P/views" || exit 18
scp -q $AC/forest/relay_views/*.lef $HOST:$P/relay_views/ && scp -q $A/net/contract_pre.json $HOST:$P/contract_pre.json || exit 18
git -C $W archive HEAD tools/hbm_die_v16 tools/hbm_die_v15 tools/die_port_bind.py tools/die_reach.py rtl/hbm_accel/die_glue rtl/lib | ssh $HOST "rm -rf $P/src && mkdir -p $P/src && tar -x -C $P/src" || exit 18
$OTRUN --mem 32 --threads 1 --disk 10 --priority die --dir $P -- bash -c "cd src/tools/hbm_die_v16 && OT_FOREST_LOG=1 /usr/bin/time -v python3 reset_forest_layer.py --relay-rows --contract $P/contract_pre.json --manifest $B/case_b/manifest.json --views $P/views --relay-views $P/relay_views --out $P/layer.json --report $P/report.json && gzip -kf $P/layer.json" > $A/forest_plan.otrun 2>&1
echo "FOREST_PLAN rc=$?"; tail -3 $A/forest_plan.otrun
scp -q $HOST:$P/report.json $A/net/forest_report.json
scp -q $HOST:$P/layer.json.gz $A/net/forest_layer.json.gz || { echo S8_FOREST_PLAN_FAIL; head -c 1500 $A/net/forest_report.json; exit 18; }
python3 tools/hbm_die_v16/d4g_relay_splice.py $A/net/contract_pre.json $A/net/forest_layer.json.gz $A/net/contract_forest.json --report $A/net/forest_splice.json \
  > $A/net/forest_splice.log 2>&1 || { echo S8_FOREST_SPLICE_FAIL; tail -5 $A/net/forest_splice.log; exit 18; }
tail -1 $A/net/forest_splice.log
# l12_banklat LAST (TW5-BANKLATDIE README: after the forest splice; pads take the endpoint's forest reset), LAT strict
step S8b l12_banklat
python3 tools/hbm_die_v16/d4g_layers/l12_banklat.py $A/net/contract_forest.json $A/net/contract.json --report $A/net/l12_banklat.json $(cat $A/banklat/L12_ARGS 2>/dev/null) \
  > $A/net/l12.log 2>&1 || { echo S8B_L12_FAIL; tail -8 $A/net/l12.log; exit 18; }
tail -2 $A/net/l12.log
step S8c su_lane_profile_gate
python3 tools/hbm_die_v16/d4g_su_lane_profile.py $A/net/contract.json --stage final --out $A/su_lane_profile_final.json --require-budget \
  || { echo "S8C_SU_PROFILE_FAIL: an SU lane is over the 18/15 budget -> reprice/re-harden (record to TOK.HDS.PRICE), no silent absorb"; exit 18; }
bind2 $A/net/contract.json $A/pbf S8 || exit 18
strict_manifest $A/net/contract.json $A/pbf S8 || echo "S8_STRICT_NOT_PASS recorded (DIAGNOSTIC; release needs PASS)"
# ---------------- S9 / S10 final GEN (reset gate FAIL) ----------------
step S9 synth_c
synth_round $A/net/contract.json $A/vplan c $A/vplan_b || exit $?
python3 tools/hbm_die_v16/d4g_bindings.py --views $A/vplan/views.json --grants $GR --out $A/view_bindings.json
OVR=$(python3 - $A/vplan/views.json <<'PY'
import json, re, sys, glob
V = json.load(open(sys.argv[1])); out = []
for c, v in sorted(V.items()):
    m = v.get('master', '')
    if v.get('kind') == 'SYNTH' and re.match(r'hbfd_rly_\d+_[A-Z]{2}_rr$', m):
        lef = glob.glob(f'physical/**/views/{m[:-3]}/{m[:-3]}.lef', recursive=True)
        if lef:
            s = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', open(sorted(lef)[0]).read())
            out.append(f'{c}={s.group(1)}x{s.group(2)}')
print(','.join(out))
PY
)
echo "RR_OUTLINE_OVERRIDE $OVR"
step S10 gen2e_final
views_up $A/vplan $A/net/contract.json || exit 17
ssh $HOST "cp $B/case_b/run.tcl $B/prior_case_b.tcl" || exit 17
X="--prior-place $B/prior_case_b.tcl"; [ -n "$OVR" ] && X="--outline-override $OVR $X"
gen case fail "$X" || { echo S10_GEN_FAIL; exit 19; }
scp -q $HOST:$B/overreach.json $A/ 2>/dev/null
ssh $HOST "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label','flags')}, default=str)[:20000])\"" > $A/gen_manifest_summary.json
# ---------------- S11 GRT + STA + clock ----------------
step S11 grt_sta_clk
$OTRUN --mem 160 --threads 16 --disk 60 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh $HOST "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log; tail -5 $B/case/out/hold_budget.log" > $A/grt_summary.txt 2>&1
rsync -a $HOST:$B/case/out/ $A/case_out/ --include='*.json' --include='*.log' --include='*.rpt' --include='*.png' --exclude='*.odb' --exclude='*.def' 2>/dev/null
cat $A/grt_summary.txt
echo CHAIN_D4G2E4_DONE HEAD=$H
