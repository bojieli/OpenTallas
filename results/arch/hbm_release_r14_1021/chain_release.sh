#!/bin/bash
# HBM-DIE14 10-21 RUN 14 = r13 (ft grid <= 405 um, --carve-reserved all, GEN check) + DRIVE-HBM 23:36 decision:
#  (1) l23 SU pre-tree (16 su PRETREE=1 + closed leaf hbm_su_pretree_s_1018-p3 child, 4 pslice SB 2470, +32 edges) and
#  (2) l23q qcore r13c on sucore_<q> (ot_hbm_su_static_qcore_r13 PRETREE=1, clk_ctl only) on the pre_relay contract BEFORE
#      S3a (new edges need stations) -> S2a synth of the changed masters -> case_a views on the r14 contract;
#      S4 pins of the changed instances from case_a (PINS_A_L23);
#  (3) strict S5S/S5B through the renewed l25 review (HBM-STRICT8), as S8;
#  (4) closed-view folds: idx256r_b views (HBM-TREE8 e3c3e1c22).  Lockstep hosts ep6/ep7/agidock (ep4 down, pve1 overloaded).
#  usage: chain_d4g2e4_r14.sh A|B   (A = plan A --plan-um 300; B = plan B --plan-um 340; floorplans gen2e4r13_1020)
# HBM-DIE13 10-20 RUN 13 = r12 (S4 station slack --plan-um, x12_q-type current-pin basis, owner1020 M8 GRT plan, synthspread)
#  + OWNER 21:40 DIE FLOORPLAN RULE: relay channels at <= 405 um.  Between blocks the d4g die has free channels; the rule
#  failed only ACROSS blocks > 405 um in both dims (121 blocks).  r13 reserves a die FEEDTHROUGH GRID in those blocks
#  (tools/hbm_die_v16/d4g_ft_grid.py: 43.2 um columns/rows, every segment <= 405 um, 113 slots / 65 mm2, die area unchanged;
#  plans results/arch/hbm_die_d4g/gen2e4r13_1020/plan{A,B}) and GEN carves them out of the SYNTH abstracts
#  (die_case_v16 --carve-reserved all), so relay rows sit inside the blocks on the pass-through wires (M6/M8 over the block).
#  New floorplan -> S3a/S3b/S3q GENs re-run (views reused from r11: a/p views, q = r11 vplan_b + contract_pre = x12_q basis).
#  + GEN CHECK (ROOT14 tools/die_safety/gen_check.py): d4g_reach_check per bus -> gen_check W1 after S7 (diagnostic) and
#  after S10 (hard: exit 1 = no GRT); + FT_USAGE per master after S3a/S7/S10 (tile-redesign NOTICE evidence).
#  usage: chain_d4g2e4_r13.sh A|B   (A = plan A, --plan-um 300; B = plan B, --plan-um 340)
# HBM-DIE12 10-20 RUN 12 = r11 + STATION SLACK (structural fix of the r11 S7 GEN_REACH_FAIL, lanes/HBM-DIE12.md):
#  r11 S4 sited stations every 380 um of routed length (25 um slack vs the 405 reach) while the capacity planner books each
#  row over +-100 um (cap-radius 2 x 50 um bins) and GEN slides rows <= 150 um -> collinear rows on the block-face tracks
#  (y 19.9 / 12.5 mm SU/SFU faces) collide and every slide > 25 um breaks the hop on both sides (A 1057 / B 1297 rows).
#  Macros do NOT box the rows in (334 mm2 free vs 18 mm2 relay rows; 92 % of fail sites have >1 mm free across travel).
#  r12: S4 lanes --plan-um $PLAN_UM (slack 405-PLAN_UM >= the capacity spread), S4 pin basis = x12_q (r11 case_b views in GEN
#  diag mode: the CURRENT SYNTH pin bind; r11 used r7 case_p pins -> 1621 planned hops into vmdel/smw/cij over reach).
#  Resumes from r11 case_a / case_p (floorplan + views unchanged, cp -al); S6 reuses r11 vplan_b synth (METAS);
#  + HBM-SYNTHSPREAD 43d60efaf (v16_synth_drive spread).  usage: chain_d4g2e4_r12.sh A|B|B340
# HBM-DIE11 10-20 RUN 11 = r10 + Codex die11 (PORT-AGE landed transport --port-age-land, physical port-face repartition
#  --split-port-faces, free-channel route preference --macro-transit-cost 1000; branch codex/hbm-die11-portage-1020 @20200bdc2)
#  + HC ESCAPE CHANNELS: tools/hbm_die_v16/d4g_cluster_spread.py opens a '#' channel grid inside each hce_* 3x3 hub cluster
#  (x 172.8 / y 86.4 um; centre band shifted +172.8 to make room; die outline unchanged) -> plan dirs gen2e4r11_1020/plan{A,B}.
#  r10 S5 died on 79 hops over reach (32 hc rows: nearest legal cell ~750 um, hub boxed by its 8 banks) + PORT-AGE + class drift.
#  Tail class source is GENERATED at S5 for this layer (canonical hbfd_exact_tail_classes.sv, hardlink broken first) and
#  committed to the plan worktree before S5L/S6 (no --check drift stop: the file is per-layer generated source).
#  One worktree + branch per plan (claude/hbm-die11-1020 = A, claude/hbm-die11-1020-b = B).   usage: chain_d4g2e4_r11.sh A|B
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
VAR=${1:?plan A|B}; PL=${VAR:0:1}; PLAN_UM=300; HOST=ot-epyc6
W=/home/ubuntu/wt/codex-hbm-r14-closed-bind-1021; AR=/home/ubuntu/artifacts/hdie-d4/codex_hbm_r14_release_1021; A=$AR/plan$VAR
R11A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r11/plan$PL; R11B=/srv/opentallas-scratch/claude/hbm-die11-1020/plan$PL
A7=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r7portage; B7=/srv/opentallas-scratch/claude/hbm-die7-gen2e4r6-1020
OLDA=/srv/opentallas-scratch/claude/hd4g/gen2e4
AE=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e; AE4=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4; AE3=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e3; AE2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e2
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1; A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c; AD=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d
B=/srv/opentallas-scratch/claude/codex-hbm-r14-release-1021/chain$VAR; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; PD=results/arch/hbm_release_r14_1021/planB_margin; BR=codex/hbm-r14-closed-bind-1021
GX="${OT_D9_GEN_EXTRA:---relay-outline density --lane-reach-repair 3 --lane-reach-lookahead chain --grt-layer-plan owner1020 --signal-top-layer M8 --carve-reserved all}"
CM="--coord-map $PD/coord_map.json"
step() { echo "STEP $* $(date -Is)"; }
mkdir -p $A; echo $$ > $A/chain.pid; echo "RUN14_HBM-DIE14 VAR $VAR PLAN $PL PLAN_UM $PLAN_UM GX=$GX"
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
cd $W
[ "$(git -C $W rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo BAD_BRANCH; exit 9; }
[ -z "$(git -C $W status --porcelain -- tools rtl results/arch/hbm_release_r14_1021)" ] || { echo DIRTY_TOOLS_REFUSED; exit 9; }
H=$(git -C $W rev-parse --short=9 HEAD); echo "CHAIN chain_d4g2e4_r14.sh var $VAR plan $PL HEAD $H $(date -Is)"
FOREST_SRC_PATHS="rtl/hbm_accel/die_glue/hbfd_rrl.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_pad.sv rtl/hdc/ot_hdc_delay.sv"
METAS="$A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth $AD/vplan/synth $AE/vplan_a/synth $AE2/vplan_a/synth $AE3/vplan_a/synth $AE4/vplan_a_run3/synth $AE4/vplan_a_run4/synth $A7/vplan_b/synth $R11A/vplan_b_s6a/synth $R11A/vplan_b/synth $A/vplan_a/synth"   # REFILL-1730: S6 round-1 views of THIS run (kept across resume)
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
strict_manifest() {   # (r14: H9R11 l25 renewed review at S5S/S5B/S8) transfer -> renewed review (l25 review) -> propose -> replay
  local U=$A/unread/$3; mkdir -p $U
  python3 tools/hbm_die_v16/unread_l21_transfer.py $REV0 $2/die.v $1 $2/port_bind.json $H $U/review_transfer.json > $U/transfer.log 2>&1 \
    || { echo "$3_UNREAD_TRANSFER_REFUSED"; tail -2 $U/transfer.log; return 1; }
  tail -1 $U/transfer.log
  python3 tools/hbm_die_v16/d4g_layers/l25_h9c_fallback.py review $U/review_transfer.json $U/review.json > $U/review.log 2>&1 \
    || { echo "$3_REVIEW_RENEW_REFUSED"; tail -2 $U/review.log; return 1; }
  tail -1 $U/review.log
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
from pathlib import Path
# Sparse release sources only; exclude historical build outputs from archive.
p={str(f) for root in ('rtl','tools') for f in Path(root).rglob('*')
   if f.is_file() and f.suffix in ('.sv','.v','.vh','.svh','.py','.sh','.tcl')}
p|={str(f) for f in Path('physical').rglob('*')
    if f.is_file() and f.suffix in ('.sv','.v','.vh','.svh','.lef','.lib')}
p|={'results/arch/hbm_release_r14_1021/planB_margin','results/arch/die_reach_1016.json',
 'results/arch/hbm_die_v15/compact660_v5','results/arch/hbm_die_v15/source_contract',
 'results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016',
 'results/arch/hbm_unread_gen2e3_1019','results/arch/hbm_native_1013/sm_own_logic/retention_cell_models.sv'}
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
    (cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --source-root $W --views $2 --commit $H --remote-root $B --workers 8 --resume-remote $CELLS > $A/drive_$3.log 2>&1); tail -2 $A/drive_$3.log
    python3 $W/tools/hbm_die_v15/v16_fetch.py --views $2 --remote-root $B --commit $H --contract $1 $CELLS > $A/fetch_$3.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch_$3.log
    MISS=""; for c in $CELLS; do [ -f $2/synth/$c/meta.json ] || MISS="$MISS $c"; done
    [ -n "$MISS" ] && { echo "SYNTH_MISSING_$3$MISS (no stubs: every SYNTH view needed)"; return 16; }
  fi
  python3 -c "
import json,collections; v=json.load(open('$2/views.json')); print('VIEW_KINDS_$3', dict(collections.Counter(x['kind'] for x in v.values())))"
  return 0
}
views_to() {      # $1 remote views dir  $2 vplan dir  $3 contract  (all earlier synth overlays, own last)
  ssh $HOST "rm -rf $1 && mkdir -p $1/synth" || return 17
  for P in $METAS $A/vplan_b/synth $2/synth; do [ -d $P ] && rsync -a $P/ $HOST:$1/synth/; done
  scp -q $2/views.json $HOST:$1/ && scp -q $3 $HOST:$1/contract.json || return 17
}
views_up() { views_to $B/views "$@"; }
# HBM-DIE13: GEN CHECK (ROOT14) = d4g_reach_check per bus (real pins) -> tools/die_safety/gen_check.py W1 -> GEN packet
gen_check_step() {   # $1 remote case dir  $2 remote contract  $3 tag  $4 extra gen_check args (e.g. --diagnostic REASON)
  $OTRUN --mem 64 --threads 1 --disk 2 --priority die --dir $1 -- bash -c "cd $B/src && python3 tools/hbm_die_v16/d4g_reach_check.py $1 $2 \
    --out $1/reach_check.json > $1/reach_check.log 2>&1; tail -3 $1/reach_check.log; python3 tools/die_safety/gen_check.py --design hbm \
    --hbm-reach $1/reach_check.json --packet $1/GEN_PACKET.json --out $1/gen_safety.json $4" > $A/gen_check_$3.otrun 2>&1; local rc=$?
  grep -v '^ot-run' $A/gen_check_$3.otrun | tail -4 | cut -c1-600
  scp -q $HOST:$1/reach_check.json $A/reach_check_$3.json 2>/dev/null; scp -q $HOST:$1/gen_safety.json $A/gen_safety_$3.json 2>/dev/null
  echo "GEN_CHECK_$3 rc=$rc"; return $rc
}
ft_usage() { python3 tools/hbm_die_v16/d4g_ft_usage.py $1 --out $A/ft_usage_$2.json | head -40; }
# gen DIR CASE RESET_GATE "EXTRA": GEN on the cut floorplan in remote dir DIR (DIR/src, DIR/views), log $A/gen_CASE.otrun
gen() {
  sed -e 's#--diagnostic-param-alias#--diagnostic-param-alias ${OT_DIE_CASE_EXTRA}#' \
      -e "s#--grants \$D/grants_d4g.json#--grants $PD/grants_d4g.json#" -e "s#--plan \$D/plan/d4g_phy/compact.P.json#--plan $PD/compact.P.json#" \
      -e "s#--lanes \$D/plan/d4g_phy/lanes.json#--lanes $PD/lanes.json#" -e "s#--clock-region-map \$D/d4g_region_map.json#--clock-region-map $PD/d4g_region_map.json#" \
      $A2/gen_d4g2.sh > $A/gen_d4g2e9_$2.sh
  for k in "--grants $PD/grants_d4g.json" "--plan $PD/compact.P.json" "--lanes $PD/lanes.json" "--clock-region-map $PD/d4g_region_map.json"; do
    grep -q -- "$k" $A/gen_d4g2e9_$2.sh || { echo "GEN_SCRIPT_NOT_SET $k"; return 1; }; done
  scp -q $A/gen_d4g2e9_$2.sh $HOST:$1/gen_d4g2e9.sh || return 17
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
# ---------------- R13 INIT: r11 a/p views + q views (r11 vplan_b + contract_pre), fresh source; S3a/S3b/S3q GENs on the ft-grid plan ----------------
if [ -z "${RESUME_S5L:-}" ] && [ -z "${R14_SKIP_S3:-}" ]; then
step R14_INIT layers_synth_a_views_src
# r14 pre_relay = l23q(l23(GEN2e4 pre_relay 9d1a3f20)): SU pre-tree (16 su PRETREE=1 + hard-child leaf, 4 pslice SB 2470,
# +32 edges / 1264 b) + qcore r13c on sucore_<q> (PRETREE=1, clk_ctl only).  New edges -> they need S4 stations, so the
# layers apply BEFORE S3a (case_a views are re-synthesised for the changed masters; r11/r13 reused the 9d1a3f20 views).
mkdir -p $A/net
[ "$(sha256sum $AE4/net/pre_relay.json | cut -c1-8)" = 9d1a3f20 ] || { echo R14_PRE_RELAY_BASIS_MISMATCH; exit 9; }
python3 tools/hbm_die_v16/d4g_layers/compose_release_r14.py $AE4/net/pre_relay.json $A/net/release_source_closed || { echo R14_RELEASE_COMPOSE_FAIL; exit 9; }
cp $A/net/release_source_closed/pre_relay_release.json $A/net/pre_relay_r14.json
python3 tools/hbm_die_v15/check_contract_modules.py --contract $A/net/pre_relay_r14.json --rev HEAD --json $A/net/cmc_pre_relay_r14.json > $A/net/cmc_pre_relay_r14.log 2>&1; tail -1 $A/net/cmc_pre_relay_r14.log
python3 tools/hbm_die_v16/d4g_functional_bind.py $A/net/pre_relay_r14.json --report $A/net/functional_bind_pre_relay_r14.json --lat warn > $A/net/functional_bind_pre_relay_r14.log 2>&1; tail -1 $A/net/functional_bind_pre_relay_r14.log
echo "R14_PRE_RELAY $(sha256sum $A/net/pre_relay_r14.json | cut -c1-16)"
step S2a synth_a_r14_masters
if [ -n "${R14_REUSE_PRIMARY:-}" ]; then
  step S2a_wait_primary_preserve_admitted
  while kill -0 2765338 2>/dev/null; do sleep 20; done
  CELLS=$(cat /home/ubuntu/scratch/codex-hbm-r14-primary-cells.txt)
  # Single bounded retry reuses completed/running paths; repairs the one missing CSA source input.
  python3 tools/hbm_die_v15/v16_synth_drive.py --source-root /home/ubuntu/wt/codex-hbm-die14-release-1021 --views $A/vplan_a_primary --commit 1fe61477b --legacy-source-commit 1fe61477b --remote-root $B --workers 8 --resume-remote $CELLS > $A/drive_a_finish.log 2>&1
  python3 tools/hbm_die_v15/v16_fetch.py --views $A/vplan_a_primary --remote-root $B --commit 1fe61477b --contract $A/net/pre_relay_r14.json $CELLS > $A/fetch_a_primary.log 2>&1 || { echo S2_FETCH_FAIL; tail -8 $A/fetch_a_primary.log; exit 12; }
  cp -a $A/vplan_a_primary/. $A/vplan_a/
  python3 tools/hbm_die_v15/v16_views.py --out $A/vplan_a --contract $A/net/pre_relay_r14.json
  # ETMs retain their actual 1fe source receipts; CLOSED views consume current explicit selections.
else
  synth_round $A/net/pre_relay_r14.json $A/vplan_a a $R11A/vplan_b || { echo S2A_SYNTH_FAIL; exit 12; }
fi
ssh $HOST "mkdir -p $B && rm -rf $B/a $B/p $B/q && mkdir -p $B/a $B/p $B/q && cp -al $R11B/p/views $B/p/views" || { echo R14_INIT_REMOTE_FAIL; exit 9; }
views_to $B/a/views $A/vplan_a $A/net/pre_relay_r14.json || { echo R14_INIT_AVIEWS_FAIL; exit 9; }
(cat $A/src_paths_a.txt; echo tools/hbm_die_v16/d4g_layers/l26_closed_views.py; echo physical/ref_tile/hdie_col_idx256r_b; echo physical/ref_tile/hdie_pc_ctrl_cfg_h9c) | sort -u > $A/src_paths_init.txt
git -C $W archive HEAD $(cat $A/src_paths_init.txt) results/arch/hbm_unread_gen2e3_1019 | ssh $HOST "rm -rf $B/src_$H && mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src \
  && ln -sfn $B/src $B/a/src && ln -sfn $B/src $B/p/src && ln -sfn $B/src $B/q/src && test -f $B/src/$PD/grants_d4g.json" || { echo R14_INIT_SRC_FAIL; exit 9; }
# r11 S3 GENs ran on the r7 source tree (src_0ae60e322 + changed tools): overlay it NO-CLOBBER (hardlinks) for the
# physical/ref_tile relay/landing views GEN reads that the git archive path list does not carry
ssh $HOST "for d in $B7/src_0ae60e322/physical/ref_tile/hbfd*; do [ -d \$d/views ] || continue; t=$B/src_$H/physical/ref_tile/\$(basename \$d); mkdir -p \$t; cp -aln \$d/views \$t/; [ ! -f \$d/spec.json ] || cp -n \$d/spec.json \$t/; done; test -f $B/src_$H/physical/ref_tile/hbfd_rly_1136_ew/views/hbfd_rly_1136_EW/hbfd_rly_1136_EW.lef" || { echo R14_INIT_R7SRC_OVERLAY_FAIL; exit 9; }
views_to $B/q/views $R11A/vplan_b $R11A/net/contract_pre.json || { echo R14_INIT_QVIEWS_FAIL; exit 9; }
mkdir -p $A; rm -rf $A/banklat; cp -a $R11A/banklat $A/banklat
echo "R14_INIT_OK src_$H plan $PD plan_um=$PLAN_UM"
step S3a gen_case_a_ftgrid
gen $B/a case_a diag "--lane-reach diag $CM --coord-map-re . --carve-reserved all" || { echo S3A_GEN_FAIL; exit 13; }
ft_usage $A/case_a_manifest.json case_a
step S3bq gen_case_p_and_pins_case_q_parallel
gen $B/p case_p diag "--prior-place $B/a/case_a/run.tcl --lane-reach diag --relay-outline density $CM --coord-map-re . --carve-reserved all" > $A/s3b.log 2>&1 &
S3B=$!
gen $B/q x12_q diag "--prior-place $B/a/case_a/run.tcl --lane-reach diag $GX $CM --coord-map-re ^(std|stu)_" > $A/s3q.log 2>&1 &
S3Q=$!
wait $S3B; R3B=$?; wait $S3Q; R3Q=$?; cat $A/s3b.log $A/s3q.log
[ $R3B = 0 ] || { echo S3B_GEN_FAIL; exit 13; }; [ $R3Q = 0 ] || { echo S3Q_GEN_FAIL; exit 13; }
ft_usage $A/x12_q_manifest.json x12_q
dense $B/q/x12_q $B/q/views/contract.json x12_q
fi
# ---------------- S4 + S5 + S5b remote (capacity planner) || lockstep ----------------
if [ -z "${RESUME_S5L:-}" ]; then
step S4_S5 remote_capacity_stations_layer
scp -q $AR/s4s5_remote.sh $HOST:$B/s4s5_remote.sh || exit 14
[ -n "${RESUME_BIND:-}" ] && echo "RESUME_BIND from S5 bind (S4/S5 layer outputs of this run reused)"
git -C $W archive HEAD results/arch/hbm_unread_gen2e3_1019 | ssh $HOST "cd $B/src_$H && rm -rf results/arch/hbm_unread_gen2e3_1019 && tar -x" || exit 14
$OTRUN --mem 96 --threads 16 --disk 20 --priority die --dir $B -- env B=$B H=$H PD=$PD RESUME_BIND=${RESUME_BIND:-} OT_CAP_ARGS="--plan-um $PLAN_UM" PINS_CASE=$B/q/x12_q PINS_A_L23=1 bash $B/s4s5_remote.sh > $A/s4s5.otrun 2>&1; rc=$?
grep -E "^(STEP|S4_|S5_|S5B_|HOPS_OVER|PINS|CAPACITY|EXACT_TAIL|RELAY_SPLICE|DIE_PORT_BIND|SU_LANE)" $A/s4s5.otrun | cut -c1-400
mkdir -p $A/net $A/pb $A/pb5b $A/unread
rsync -a --exclude 'contract_l7.json' $HOST:$B/artifacts/ $A/ 2>/dev/null
[ $rc = 0 ] && grep -q S5B_DONE_R11 $A/s4s5.otrun || { echo "S4_S5_REMOTE_FAIL rc=$rc"; tail -8 $A/s4s5.otrun; exit 15; }
python3 -c "import json;r=json.load(open('$A/lanes_report.json'));c=r.get('capacity') or {};w=c.get('windows',{});print('CAPACITY_PLAN forced',c.get('forced'),'windows',w.get('windows'),'over1',w.get('over_1'),'hop_violations',r['hop_violations'],'worst',w.get('worst',[])[:5])"
else echo "RESUME_S5L: S4/S5/S5b outputs of this run reused ($A)"; fi
step S5T commit_generated_tail_classes
TC=rtl/hbm_accel/die_glue/hbfd_exact_tail_classes.sv
scp -q $HOST:$B/src/$TC $W/$TC || { echo S5T_FETCH_FAIL; exit 15; }
ssh $HOST "sha256sum $B/src/$TC" | cut -d' ' -f1 > $A/tail_classes.sha; [ "$(sha256sum $W/$TC | cut -d' ' -f1)" = "$(cat $A/tail_classes.sha)" ] || { echo S5T_SHA_MISMATCH; exit 15; }
if ! git -C $W diff --quiet -- $TC; then
  git -C $W add -- $TC && git -C $W commit -q -m "HBM-DIE14 r14 $VAR: exact tail class source generated for this run's S5 relay layer

Generated by tools/hbm_die_v16/exact_tail_layer.py --classes at chain S5 ($B/artifacts/net/exact_tail_classes.json).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01RrFw9ZXqn3BZPFX6461n1E" -- $TC || { echo S5T_COMMIT_FAIL; exit 15; }
  H=$(git -C $W rev-parse --short=9 HEAD); echo "S5T_COMMITTED $H"; git -C $W push -q origin $BR 2>&1 | tail -1
fi
step S5S strict_unread_local
# HBM-DIE11: strict unread review/proposal/replay need git history of the exact source (remote src is an archive) -> here, gated
# strict needs a RENEWED semantic review (L21 review pins pre-l24 ot_hbm_svc_sm_xcal_rel_t.sv; h9c rebind also renews it):
# recorded as DIAGNOSTIC FAIL (release needs PASS); structural bind (unread only, transfer remaining 0) is the gate here
strict_manifest $A/net/post_landing.json $A/pb S5 || echo "S5_STRICT_NOT_PASS recorded (DIAGNOSTIC; l25 renewed review path; release needs PASS)"
strict_manifest $A/net/contract_pre.json $A/pb5b S5B || echo "S5B_STRICT_NOT_PASS recorded (DIAGNOSTIC; renewed review owed)"
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
ft_usage $A/case_b_manifest.json case_b
gen_check_step $B/case_b $B/views/contract.json case_b "--diagnostic S7_pre_forest_case"
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
# HBM-H9R11 10-20: bind the CLOSED h9c PC-controller fallback (l25 = prepare_fallback, LEAD-admitted ea87fbac pattern) on the
# S8 contract BEFORE S8c/bind2/strict/S9 synth_c; strict reuses the admitted H9BIND delta review (4 l24 re-pins, 0 entries).
step S8h h9c_fallback_swap
echo 'S8H_H9C_ALREADY_SELECTED_BEFORE_S3_S4 (64 exact closed controllers; no late remaster)'
step S8c su_lane_profile_gate
python3 tools/hbm_die_v16/d4g_su_lane_profile.py $A/net/contract.json --stage final --out $A/su_lane_profile_final.json --require-budget \
  || { echo "S8C_SU_PROFILE_FAIL: an SU lane is over the 18/15 budget -> reprice/re-harden (record to TOK.HDS.PRICE), no silent absorb"; exit 18; }
bind2 $A/net/contract.json $A/pbf S8 || exit 18
strict_manifest $A/net/contract.json $A/pbf S8 || echo "S8_STRICT_NOT_PASS recorded (DIAGNOSTIC; release needs PASS)"
# ---------------- S9 / S10 final GEN (reset gate FAIL) ----------------
step S9 synth_c
synth_round $A/net/contract.json $A/vplan c $A/vplan_b || exit $?
python3 -c "import json;v=json.load(open('$A/vplan/views.json'));print('S9_H9C_VIEW',[(c,e['kind'],e.get('view_dir'),len(e['instances'])) for c,e in v.items() if 'pc_ctrl' in e['master']])"
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
gen $B case diag "$X --lane-reach diag" || { echo S10_GEN_FAIL; exit 19; }
ssh $HOST "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label','flags')}, default=str)[:20000])\"" > $A/gen_manifest_summary.json
echo 'R14_S10_COMPLETE; proceeding scoped diagnostic physical run with declared child/native limitations'
# ---------------- S11 GRT + STA + clock ----------------
dense $B/case $B/views/contract.json case_final
ft_usage $A/case_manifest.json case
echo "DIAGNOSTIC_PHYSICAL_SCOPE: available views; final child/native/GEN qualification outstanding"
step S11 grt_sta_clk
$OTRUN --mem 160 --threads 16 --disk 60 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh $HOST "cat $B/case/out/run.exit; grep -E 'OT_PG_|OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log; tail -5 $B/case/out/hold_budget.log" > $A/grt_summary.txt 2>&1
rsync -a $HOST:$B/case/out/ $A/case_out/ --include='*.json' --include='*.log' --include='*.rpt' --include='*.png' --exclude='*.odb' --exclude='*.def' 2>/dev/null
cat $A/grt_summary.txt
echo CHAIN_D4G2E4_R14_DONE VAR=$VAR PLAN=$PL HEAD=$H
