#!/bin/bash
# HBM-DIE10 10-20 RUN 10 = r9 + (a) PORT-AGE 0ae60e322 merged back (r9 branch had dropped it -> S5 G-CIL-RC sucore_NE.red_tag
#  15/16 stages), (b) S4 capacity planner REACH FIRST (r9: 641/792 hops > 405 from jumping past full windows), (c) l24
#  (svg/xc XSLOT, OPEN_IL = x reuse; sm INT8W = Qwen INT8) on contract_pre before S6, (d) dense-face wire reports
#  (S3b/S7/S10, case pin views) before GRT, (e) main die_clock_check (ring-landed crossings).  usage: chain_d4g2e4_r10.sh A|B
# HBM-DIE9 10-20 RUN 9 (LEAD7-HBM decision 10-20: the r7 S4 station plan is structurally infeasible -> re-run S4/S5/S5b/S6
#  on a NEW plan; r7 S5/S6 stay r7 evidence).  usage: chain_d4g2e4_r9.sh A|B   (one detached chain per floorplan plan)
#  Floorplan: channel cuts (tools/hbm_die_v16/d4g_channel_cuts.py, results/arch/hbm_die_d4g/gen2e4r9_1020/plan<P>):
#    A = channels at every SM gap (both sides of each xq/xl stack + 100 um gaps + centre), 22.58 x 32.46 mm (733 mm2)
#    B = fewer wider channels (xq/xl sides +345.6, centre spine +432),                       23.40 x 32.46 mm (760 mm2)
#    both: y channels at the SM-row / middle-band edges (+259.2) and SM / stripe edges (+86.4); PHY/PC stripes rigid.
#  S3a GEN case_a (pre_relay, relay-free views, cut plan) -> S3b GEN case_p (r7 post-landing contract + r7 S6 views on the
#  cut plan, prior homes = case_a: the CURRENT pin positions) -> S4 stations on case_a + CAPACITY-aware lane planner on the
#  current pins -> S5 layer/tail/splice/strict (remote) || relay lockstep (pos + 4 causal mutants, fleet 5.050) -> S5b
#  -> S6 synth b -> S7 GEN case_b (lane-reach fail, density outlines, chain look-ahead, repair 3) -> S8 forest/l12/S8c/bind
#  -> S9 synth c -> S10 GEN (reset gate fail) -> S11 GRT (global_connect PG step) + STA TT/FF + neighbour clock + hold.
set -o pipefail
PL=${1:?plan A|B}; HOST=ot-epyc6
W=/home/ubuntu/wt/hbm-die9-station; AR=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r10; A=$AR/plan$PL
A7=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r7portage; B7=/srv/opentallas-scratch/claude/hbm-die7-gen2e4r6-1020
OLDA=/srv/opentallas-scratch/claude/hd4g/gen2e4
AE=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e; AE4=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4; AE3=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e3; AE2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e2
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1; A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c; AD=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d
B=/srv/opentallas-scratch/claude/hbm-die10-1020/plan$PL; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; PD=$D/gen2e4r9_1020/plan$PL; BR=claude/hbm-die10-1020
GX="${OT_D9_GEN_EXTRA:---relay-outline density --lane-reach-repair 3 --lane-reach-lookahead chain}"
CM="--coord-map $PD/coord_map.json"
step() { echo "STEP $* $(date -Is)"; }
mkdir -p $A; echo $$ > $A/chain.pid; echo "RUN10_HBM-DIE10 PLAN $PL GX=$GX"
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
cd $W
[ "$(git -C $W rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo BAD_BRANCH; exit 9; }
[ -z "$(git -C $W status --porcelain -- tools results/arch/hbm_die_d4g/gen2e4r9_1020)" ] || { echo DIRTY_TOOLS_REFUSED; exit 9; }
H=$(git -C $W rev-parse --short=9 HEAD); echo "CHAIN chain_d4g2e4_r10.sh plan $PL HEAD $H $(date -Is)"
FOREST_SRC_PATHS="rtl/hbm_accel/die_glue/hbfd_rrl.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_pad.sv rtl/hdc/ot_hdc_delay.sv"
METAS="$A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth $AD/vplan/synth $AE/vplan_a/synth $AE2/vplan_a/synth $AE3/vplan_a/synth $AE4/vplan_a_run3/synth $AE4/vplan_a_run4/synth $A7/vplan_b/synth"
bind2() {   # $1 contract  $2 out dir  $3 tag -> strict port bind + functional bind (LAT strict when l12 is in)
  mkdir -p $2; bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $1 $2 > /dev/null; tail -1 $2/port_bind.log
  if ! grep -q "^DIE_PORT_BIND PASS" $2/port_bind.log; then
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
strict_manifest() {   # $1 contract  $2 bind dir  $3 tag -> transfer -> propose -> replay
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
  for P in $METAS; do [ -d $P ] && [ "$P" != "$2/synth" ] && (cd $P && tar -cf - */meta.json 2>/dev/null) | tar -x -C $A/synmeta_$3; done
  python3 tools/hbm_die_v16/synth_reuse_r8b.py --views $2 --metas $A/synmeta_$3 --root $W --out $A/reuse_$3.json --prev $4 > $A/reuse_$3.log; tail -3 $A/reuse_$3.log | cut -c1-600
  CELLS=$(grep '^SYNTH ' $A/reuse_$3.log | cut -d' ' -f2-)
  python3 - $2 > $A/src_paths_$3.txt <<PY
import json, sys
V=json.load(open(sys.argv[1] + '/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/hbm_mtp/rtl','physical/hbm_pll_views','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016','results/arch/hbm_native_1013/sm_own_logic/retention_cell_models.sv',
   'results/arch/hbm_unread_gen2e3_1019'}
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
  for P in $METAS $A/vplan_b/synth $1/synth; do [ -d $P ] && rsync -a $P/ $HOST:$B/views/synth/; done
  scp -q $1/views.json $HOST:$B/views/ && scp -q $2 $HOST:$B/views/contract.json || return 17
}
# gen DIR CASE RESET_GATE "EXTRA": GEN on the cut floorplan in remote dir DIR (DIR/src, DIR/views), log $A/gen_CASE.otrun
gen() {
  sed -e 's#--diagnostic-param-alias#--diagnostic-param-alias ${OT_DIE_CASE_EXTRA}#' \
      -e "s#--grants \$D/grants_d4g.json#--grants $PD/grants_d4g.json#" -e "s#--plan \$D/plan/d4g_phy/compact.P.json#--plan $PD/compact.P.json#" \
      -e "s#--lanes \$D/plan/d4g_phy/lanes.json#--lanes $PD/lanes.json#" -e "s#--clock-region-map \$D/d4g_region_map.json#--clock-region-map $PD/d4g_region_map.json#" \
      $A2/gen_d4g2.sh > $A/gen_d4g2e9.sh
  for k in "--grants $PD/grants_d4g.json" "--plan $PD/compact.P.json" "--lanes $PD/lanes.json" "--clock-region-map $PD/d4g_region_map.json"; do
    grep -q -- "$k" $A/gen_d4g2e9.sh || { echo "GEN_SCRIPT_NOT_SET $k"; return 1; }; done
  scp -q $A/gen_d4g2e9.sh $HOST:$1/gen_d4g2e9.sh || return 17
  $OTRUN --mem 64 --threads 2 --disk 10 --priority die --dir $1/views -- env OT_ABS_PIN_WINDOW_UM=3 OT_GEN2_CASE=$2 OT_RESET_GATE=$3 \
    OT_DIE_CASE_EXTRA="$4" bash $1/gen_d4g2e9.sh > $A/gen_$2.otrun 2>&1; echo "GEN_$2 ot-run rc=$? $(date -Is)"; tail -12 $A/gen_$2.otrun
  scp -q $1/$2/layout.png $A/$2_layout.png 2>/dev/null; scp -q $HOST:$1/$2/layout.png $A/$2_layout.png 2>/dev/null
  scp -q $HOST:$1/$2/out/reach_fail.json $A/$2_reach_fail.json 2>/dev/null
  grep -q GEN_OK $A/gen_$2.otrun || return 1
  scp -q $HOST:$1/$2/manifest.json $A/$2_manifest.json; scp -q $HOST:$1/$2/run.tcl $A/$2_run.tcl 2>/dev/null
  python3 -c "
import json; m=json.load(open('$A/$2_manifest.json')); h=m.get('homes',{})
gen=[(n,v['rule'][:40],v.get('dist_um')) for n,v in h.items() if not v['rule'].startswith(('planned relay','relay chain','region','grant slot','prior home','lane row'))]
print('GENERATED_HOMES_$2', len(gen), sorted(gen, key=lambda t:-(t[2] or 0))[:12]); print('PROBLEMS', len(m.get('placement_problems',[])), 'DIE', m.get('die_um'))"
  return 0
}
REV0=$W/results/arch/hbm_unread_gen2e3_1019/l21/review_l21_candidate.json
# DIE CHECKLIST (COORD 10-20 08:20): dense faces (HBM PHY, d2d/SerDes, host/ep, frame landings) from the case's own pin
# views: per face max wire um, wires > 405, wires per crossing.  Report (GEN packet), never a gate.
dense() {   # $1 remote case dir  $2 remote contract  $3 tag
  $OTRUN --mem 12 --threads 1 --disk 2 --priority die --dir $1 -- python3 -I $B/src/tools/hbm_die_v16/die_dense_face_report.py $1 \
    --contract $2 --out $1/dense_face.json > $A/dense_$3.otrun 2>&1; echo "DENSE_$3 rc=$?"; grep '^DENSE_FACE' $A/dense_$3.otrun | cut -c1-300
  scp -q $HOST:$1/dense_face.json $A/dense_face_$3.json 2>/dev/null; true
}
# ---------------- S0 remote source + views ----------------
step S0 remote_src_views
CH=$(git -C $W diff --name-only 0ae60e322 HEAD -- tools results/arch/hbm_die_d4g/gen2e4r9_1020); echo "CHANGED_VS_0ae $(echo $CH | wc -w) files"
echo "$CH" | grep -v -e '^tools/' -e '^results/arch/hbm_die_d4g/gen2e4r9_1020/' | grep -q . && { echo NON_TOOL_SOURCE_CHANGE_REFUSED; exit 9; }
L24RTL="rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm4pc_cdc_rel_id.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_feed_programmed_rel_id.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group_rel_id.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_issuer_rel.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal_rel_t.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_sm_packed136.sv rtl/hbm_accel/sm/attn/ot_hbm_accel_smh_attn.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_attn_front_static.sv rtl/hbm_accel/sm/attn/ot_hbm_sm_i8w_front.sv rtl/hbm_accel/sm/static/ot_smh_int8_tile.sv"
CHR=$(git -C $W diff --name-only 0ae60e322 HEAD -- rtl physical)   # only the l24 RTL (= origin/main) may differ
for f in $CHR; do case " $L24RTL " in *" $f "*) ;; *) echo "RTL_CHANGE_REFUSED $f"; exit 9;; esac; done
CH="$CH $CHR"
ssh $HOST "mkdir -p $B && rm -rf $B/src_$H && cp -al $B7/src_0ae60e322 $B/src_$H && ln -sfn $B/src_$H $B/src" || exit 9
(for f in $CH; do echo $f; done) | tar -C $W -cf - -T - | ssh $HOST "cd $B/src_$H && tar -tf - > /dev/null" || exit 9
for f in $CH; do ssh $HOST "rm -f $B/src_$H/$f && mkdir -p $B/src_$H/$(dirname $f)" && scp -q $W/$f $HOST:$B/src_$H/$f || exit 9; done
ssh $HOST "rm -rf $B/a $B/p && mkdir -p $B/a $B/p && ln -sfn $B/src $B/a/src && ln -sfn $B/src $B/p/src && cp -al $OLDA/views $B/a/views && cp -al $B7/views $B/p/views \
  && sha256sum $B/a/views/contract.json $B/p/views/contract.json" > $A/remote_views.sha || exit 9
cat $A/remote_views.sha
[ "$(head -1 $A/remote_views.sha | cut -d' ' -f1)" = "$(sha256sum $AE4/net/pre_relay.json | cut -d' ' -f1)" ] || { echo CASE_A_VIEWS_CONTRACT_MISMATCH; exit 9; }
[ "$(sed -n 2p $A/remote_views.sha | cut -d' ' -f1)" = "$(sha256sum $A7/net/contract_pre.json | cut -d' ' -f1)" ] || { echo CASE_P_VIEWS_CONTRACT_MISMATCH; exit 9; }
# ---------------- S3a / S3b planning GENs on the cut floorplan ----------------
step S3a gen_case_a_cut
gen $B/a case_a diag "--lane-reach diag $CM --coord-map-re ." || { echo S3A_GEN_FAIL; exit 13; }
step S3b gen_case_p_current_pins
gen $B/p case_p diag "--prior-place $B/a/case_a/run.tcl --lane-reach diag --relay-outline density $CM --coord-map-re ." || { echo S3B_GEN_FAIL; exit 13; }
dense $B/p/case_p $B/p/views/contract.json case_p   # baseline only: case_p relays sit at r7 homes (S4 re-sites them)
# ---------------- S4 + S5 + S5b remote (capacity planner) || lockstep ----------------
step S4_S5 remote_capacity_stations_layer
scp -q $AR/s4s5_remote.sh $HOST:$B/s4s5_remote.sh || exit 14
$OTRUN --mem 96 --threads 16 --disk 20 --priority die --dir $B -- env B=$B H=$H PD=$PD bash $B/s4s5_remote.sh > $A/s4s5.otrun 2>&1; rc=$?
grep -E "^(STEP|S4_|S5_|S5B_|HOPS_OVER|PINS|CAPACITY|EXACT_TAIL|RELAY_SPLICE|DIE_PORT_BIND|SU_LANE)" $A/s4s5.otrun | cut -c1-400
mkdir -p $A/net $A/pb $A/pb5b $A/unread
rsync -a --exclude 'contract_l7.json' $HOST:$B/artifacts/ $A/ 2>/dev/null
[ $rc = 0 ] && grep -q S5B_DONE_R10 $A/s4s5.otrun || { echo "S4_S5_REMOTE_FAIL rc=$rc"; tail -8 $A/s4s5.otrun; exit 15; }
python3 -c "import json;r=json.load(open('$A/lanes_report.json'));c=r.get('capacity') or {};w=c.get('windows',{});print('CAPACITY_PLAN forced',c.get('forced'),'windows',w.get('windows'),'over1',w.get('over_1'),'hop_violations',r['hop_violations'],'worst',w.get('worst',[])[:5])"
step S5L relay_lockstep
bash $AR/lockstep_runner_unpinned.sh $A/net/relays_d4g_land.json.gz $A/lockstep 120 > $A/lockstep_land.log 2>&1; tail -12 $A/lockstep_land.log
grep -q "RELAY_LOCKSTEP_GATE PASS" $A/lockstep_land.log || { echo S5_LOCKSTEP_FAIL; exit 15; }
python3 tools/hbm_die_v15/check_contract_modules.py --contract $A/net/contract_pre.json --rev HEAD --json $A/pb5b/contract_modules_check.json > $A/pb5b/cmc_local.log 2>&1; tail -1 $A/pb5b/cmc_local.log
# ---------------- S6 / S7 post-landing case ----------------
step S5X l24_xreuse_int8w
python3 tools/hbm_die_v16/d4g_layers/l24_sm_xslot_i8w.py $A/net/contract_pre.json $A/net/contract_pre_l24.json --report $A/net/l24_report.json \
  || { echo S5X_L24_FAIL; exit 16; }
mv $A/net/contract_pre.json $A/net/contract_pre_nol24.json && mv $A/net/contract_pre_l24.json $A/net/contract_pre.json
python3 tools/hbm_die_v15/check_contract_modules.py --contract $A/net/contract_pre.json --rev HEAD --json $A/pb5b/contract_modules_l24.json > $A/pb5b/cmc_l24.log 2>&1; tail -1 $A/pb5b/cmc_l24.log
python3 tools/hbm_die_v16/d4g_functional_bind.py $A/net/contract_pre.json --report $A/pb5b/functional_bind_l24.json --lat warn > $A/pb5b/functional_bind_l24.log 2>&1
tail -1 $A/pb5b/functional_bind_l24.log; grep -q "^FUNCTIONAL_BIND PASS" $A/pb5b/functional_bind_l24.log || { echo S5X_FUNCTIONAL_FAIL; exit 16; }
step S6 synth_b
synth_round $A/net/contract_pre.json $A/vplan_b b $A7/vplan_b || exit $?
step S7 gen2e_case_b_postlanding
views_up $A/vplan_b $A/net/contract_pre.json || exit 17
ssh $HOST "cp $B/a/gen_d4g2e9.sh $B/ 2>/dev/null; true"
gen $B case_b diag "--prior-place $B/a/case_a/run.tcl $GX $CM --coord-map-re ^(std|stu)_" || { echo S7_GEN_B_FAIL; exit 17; }
echo "S7_PNG_INSPECT_OWED $A/case_b_layout.png"
dense $B/case_b $B/views/contract.json case_b
# ---------------- S8 relay-row reset forest ----------------
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
python3 tools/hbm_die_v16/d4g_bindings.py --views $A/vplan/views.json --grants $PD/grants_d4g.json --out $A/view_bindings.json
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
X="--prior-place $B/case_b/run.tcl $GX $CM --coord-map-re ^(std|stu)_"; [ -n "$OVR" ] && X="--outline-override $OVR $X"
gen $B case fail "$X" || { echo S10_GEN_FAIL; exit 19; }
ssh $HOST "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label','flags')}, default=str)[:20000])\"" > $A/gen_manifest_summary.json
# ---------------- S11 GRT + STA + clock ----------------
dense $B/case $B/views/contract.json case_final
step S11 grt_sta_clk
$OTRUN --mem 160 --threads 16 --disk 60 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh $HOST "cat $B/case/out/run.exit; grep -E 'OT_PG_|OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log; tail -5 $B/case/out/hold_budget.log" > $A/grt_summary.txt 2>&1
rsync -a $HOST:$B/case/out/ $A/case_out/ --include='*.json' --include='*.log' --include='*.rpt' --include='*.png' --exclude='*.odb' --exclude='*.def' 2>/dev/null
cat $A/grt_summary.txt
echo CHAIN_D4G2E4_R10_DONE PLAN=$PL HEAD=$H
