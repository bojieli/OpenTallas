#!/bin/bash
# P ROOT-selected9a23 combined local root-aware model, diagnostic GEN/PQ/S4 only.
# Model e279106c7: 74 homes, all11 changed bodies/root identities checked; global clock constraints OPEN.
# Fail closed on actualmodelhome mismatch AFTER A and P/Q, before later stages.
# Owned localartifact STOP_FUTURE_STAGES marker stops at next phase boundary;
# it never signals admitted jobs or edits source/input/results.
# Same74S2/H/fullreticle/currentHC23; no sourceupgrade/guardrelax/newS2.
# Source-pinned fresh.keepstage; GEN/PQ/S4only, never S5/route.
set -o pipefail
VAR=${1:?plan M|F}; PL=B; PLAN_UM=300; HOST=ot-epyc5
W=/home/ubuntu/wt/claude-hbm-r16q-1021; AR=/home/ubuntu/artifacts/hdie-d4/claude_hbm_r16q_full_1021; RST_FORM=${RST_FORM:-rfc}; A=$AR/plan$VAR
R11A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r11/plan$PL; R11B=/srv/opentallas-scratch/claude/hbm-die11-1020/plan$PL
A7=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r7portage; B7=/srv/opentallas-scratch/claude/hbm-die7-gen2e4r6-1020
OLDA=/srv/opentallas-scratch/claude/hd4g/gen2e4
AE=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e; AE4=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4; AE3=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e3; AE2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e2
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1; A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c; AD=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d
B=/srv/opentallas-scratch/claude/claude-hbm-r16q-full-1021/chain$VAR; OLD=/srv/opentallas-scratch/claude/codex-hbm-r15-h158-grants-1021/chainB; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; PD=results/arch/hbm_release_r16_1021/plan$VAR; BR=claude/hbm-r16q-1021
GX="${OT_D9_GEN_EXTRA:---relay-outline density --lane-reach-repair 3 --lane-reach-lookahead chain --grt-layer-plan owner1020 --signal-top-layer M8 --carve-reserved all}"
CM="--coord-map $PD/coord_map.json --slot-map $(cat $W/$PD/slot_map.txt)"
# Local transport override only in this successor process: ep6 public route loses packets.
ssh() { local host=; for host in "$@"; do [ "$host" = ot-epyc6 ] && { command ssh -C -J ot-epyc5 -S none "$@"; return $?; }; done; command ssh -C -o ControlPath=none "$@"; }
scp() { local arg=; for arg in "$@"; do [[ "$arg" == ot-epyc6:* ]] && { command scp -C -o ProxyJump=ot-epyc5 -o ControlPath=none "$@"; return $?; }; done; command scp -C -o ControlPath=none "$@"; }
stop_future() {
  [ -e "$A/STOP_FUTURE_STAGES" ] || return 0
  python3 - "$A" "${H:-UNRESOLVED}" "$B" "$BASHPID" "$*" <<'PYSTOP'
import datetime,json,sys
from pathlib import Path
a,source,remote,pid,stage=sys.argv[1:]
r={'status':'STOPPED_BEFORE_FUTURE_ADMISSION','time':datetime.datetime.now().astimezone().isoformat(),'stage':stage,'source':source,'controller_pid':pid,'remote_root':remote,'marker':str(Path(a)/'STOP_FUTURE_STAGES'),'restart_owner':'DIE coordinator /root/hbm_lead/die_chain or returning Claude coordinator','admitted_jobs_signalled':False,'completion_claim':False,'resume':'Manual source/receipt review of identical inputs required; this runner is not automatically restartable over an existing remote root.'}
(Path(a)/('STOP_RECEIPT_'+pid+'.json')).write_text(json.dumps(r,indent=2)+'\n')
PYSTOP
  echo "OWNED_STOP_FUTURE_STAGES before=$* source=${H:-UNRESOLVED} restart_owner=DIE_coordinator $(date -Is)"
  exit 26
}
step() { stop_future "$@"; echo "STEP $* $(date -Is)"; }
mkdir -p $A; touch "$AR/.keep" "$A/.keep"; echo $$ > $A/chain.pid; echo "RUN14_HBM-DIE14 VAR $VAR PLAN $PL PLAN_UM $PLAN_UM GX=$GX"
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
cd $W
[ "$(git -C $W rev-parse --abbrev-ref HEAD)" = "$BR" ] || { echo BAD_BRANCH; exit 9; }
[ -z "$(git -C $W status --porcelain -- tools rtl results/arch/hbm_release_r14_1021)" ] || { echo DIRTY_TOOLS_REFUSED; exit 9; }
H=$(git -C $W rev-parse --short=9 HEAD); echo "CHAIN chain_d4g2e4_r14.sh var $VAR plan $PL HEAD $H $(date -Is)"
FOREST_SRC_PATHS="rtl/hbm_accel/die_glue/hbfd_rrl.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_pad.sv rtl/hdc/ot_hdc_delay.sv rtl/hbm_accel/die_glue/hbfd_rly_rfc_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rfc.sv"
METAS="$A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth $AD/vplan/synth $AE/vplan_a/synth $AE2/vplan_a/synth $AE3/vplan_a/synth $AE4/vplan_a_run3/synth $AE4/vplan_a_run4/synth $A7/vplan_b/synth $R11A/vplan_b_s6a/synth $R11A/vplan_b/synth /home/ubuntu/artifacts/hdie-d4/codex_hbm_r14_release_1021/planB/vplan_a/synth /home/ubuntu/artifacts/hdie-d4/codex_hbm_r14_release_1021/planB/vplan_b/synth /home/ubuntu/artifacts/hdie-d4/codex_hbm_r14_release_1021/planB/vplan/synth /home/ubuntu/artifacts/hdie-d4/codex_hbm_r15_release_1021/plan$VAR/vplan_a/synth /home/ubuntu/artifacts/hdie-d4/codex_hbm_r15_native32_bays_1021/plan$VAR/vplan_changed/synth /home/ubuntu/artifacts/hdie-d4/codex_hbm_r15_native32_bays_1021/plan$VAR/vplan_repair/synth $A/vplan_changed/synth $A/vplan_a/synth"   # REFILL-1730: S6 round-1 views of THIS run (kept across resume)
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
  # Measured r14 top-k synthesis used 69 GiB; 48 GiB caused protected memcg livelock.
  python3 - "$2/jobs.tsv" <<'PYMEM'
import sys
from pathlib import Path
p=Path(sys.argv[1]); rows=[]
for line in p.read_text().splitlines():
    fields=line.split('\t')
    if fields[0]=='ot_hbm_idx_topk_link_static': fields[3]=str(max(128,int(fields[3])))
    rows.append('\t'.join(fields))
p.write_text('\n'.join(rows)+'\n')
PYMEM
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
 'results/arch/hbm_unread_gen2e3_1019','results/arch/hbm_native_1013/sm_own_logic/retention_cell_models.sv',
 'physical/hbm_pll_views','physical/ref_tile/hdie_pc_ctrl/floorplan.json',
 'results/arch/hbm_die_d4g/landing','results/arch/hbm_die_d4g/gen0/die.v.pads.json',
 'results/arch/hbm_release_r15_1021/planB_cxdl_bays','results/arch/hbm_release_r15_1021/planB_h158'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
p|=set(Path('results/arch/hbm_release_r15_1021/relay_view_dirs.txt').read_text().splitlines())
print('\n'.join(sorted(p)))
PY
  (grep -v -e "^#" -e "^ *$" $AC/views/extra_src_paths.txt 2>/dev/null; for x in $FOREST_SRC_PATHS; do [ -e $x ] && echo $x; done) >> $A/src_paths_$3.txt
  sort -u -o $A/src_paths_$3.txt $A/src_paths_$3.txt
  ssh $HOST "rm -rf $B/src_$H" || return 15
  git -C $W archive HEAD $(cat $A/src_paths_$3.txt) | ssh $HOST "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || return 15
  tar -C $2/wrap -cf - . | ssh $HOST "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || return 15
  for h in ot-epyc7 ot-epyc9 ot-pve1 ot-gold1 ot-gold2; do ssh $HOST "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
  N0=$(ssh -o ControlPath=none $HOST "find $B/src_$H | wc -l")
  for h in ot-epyc7 ot-epyc9 ot-pve1 ot-gold1 ot-gold2; do n=$(ssh -o ControlPath=none $h "find $B/src_$H 2>/dev/null | wc -l"); echo "SRC $h $n/$N0"
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
  for P in $METAS $A/vplan_b/synth $2/synth; do [ -d $P ] && rsync -azW --partial --timeout=120 -e 'ssh -S none -o ConnectTimeout=20 -o ServerAliveInterval=20 -o ServerAliveCountMax=3' $P/ $HOST:$1/synth/; done
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
  stop_future "GEN_ADMISSION $2"
  $OTRUN --mem 64 --threads 2 --disk 10 --priority die --dir $1 -- env OT_ABS_PIN_WINDOW_UM=3 OT_GEN2_CASE=$2 OT_RESET_GATE=$3 \
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
# Exact source-bound K: selected375 graph + CLOSEDcolh source/ABI. No oldUCIE alias.
CACHED=/home/ubuntu/artifacts/hdie-d4/codex_ucie_colh_bind_1021
CACHE16=/home/ubuntu/artifacts/hdie-d4/codex_hbm_r16e_full_1021/planeM/vplan_changed/synth
J=/srv/opentallas-scratch/claude/codex-hbm-r16j-s4q-1021/chainjM
if [ -z "${RESUME_S4:-}" ]; then
step S3_STAGE exact_source_colh
[ -z "$(git diff --name-only 83d057be0 HEAD -- rtl tools | grep -v -x -e tools/hbm_die_v15/die_case_v16.py -e tools/hbm_die_v15/die_relay_stations.py -e rtl/hbm_accel/die_glue/hbfd_exact_tail_classes.sv)" ] || { echo SOURCE_READSET_CHANGED_REFUSED; exit 12; }
python3 - "$CACHED/reuse.json" "$CACHED/pre_relay_colm.json" "$W/$PD/corridor_model.json" <<'PYREADY'
import json,sys
m=json.load(open(sys.argv[3]));assert len(m['placement_checks'])==78 and not any(i['fixed_body_overlaps'] for i in m['placement_checks']);assert m['rtl_changes']==m['guard_changes']==m['cycle_credit']==0
r=json.load(open(sys.argv[1]));assert not r['synth'] and len(r['reuse'])==74, 'Exact initial S2 reuse required; no duplicate build'
c=json.load(open(sys.argv[2]));h=c['instances']['host_N']
assert h['master']=='ot_pdie_ucie_col' and h['params']=={'MUT':0}
assert h['physical_view']=='physical/ref_tile/hbm_pdie_ucie_colh/views/ot_pdie_ucie_col'
assert c['external_clock_entries'][0]['port']=='ck_rck' and not c['external_clock_entries'][0]['pll_alias']
print('SOURCE_READY_COLH exact74reuse + realexternalroot; parentarrival/startup OPEN')
PYREADY
[ $? = 0 ] || exit 12
# The copied input tree is immutable. Break every overlaid file hardlink before extracting.
python3 - "$CACHED/pre_relay_colm.json" "$CACHED/views/views.json" > "$A/source_paths.txt" <<'PYPATHS'
import json,sys
c=json.load(open(sys.argv[1]));v=json.load(open(sys.argv[2]));p=set()
for i in c['instances'].values():p.update([i['source']]+(i.get('rtl_deps') or []))
p|={'tools/hbm_die_v15/die_case_v16.py','rtl/common/landed_parent/ot_pl_land.sv','results/arch/hbm_release_r16_1021','results/arch/hbm_ucie_selected_bind_1430_1021'}
p|={i['view_dir'] for i in v.values() if i.get('view_dir')}
p|=set(__import__('subprocess').check_output(['git','diff-tree','--no-commit-id','--name-only','-r','7e13df2b1'],text=True).splitlines())
print('\n'.join(sorted(p)))
PYPATHS
[ $? = 0 ] || exit 13
git archive --format=tar.gz HEAD $(cat "$A/source_paths.txt") > "$A/source_$H.tar.gz" || exit 13
ssh $HOST "set -e; test ! -e $B; mkdir -p $B/a $B/p $B/q; touch $B/.keep /srv/opentallas-scratch/claude/claude-hbm-r16q-full-1021/.keep; cp -al \$(readlink -f $J/src) $B/src_$H; ln -sfn $B/src_$H $B/src; cp -al $J/a/views $B/a/views; rm -f $B/a/views/views.json $B/a/views/contract.json; ln -sfn $B/src $B/a/src" || exit 13
scp -q "$A/source_$H.tar.gz" $HOST:$B/source.tar.gz || exit 13
ssh $HOST "python3 - '$B' '$H' <<'PYUNLINK'
import sys,tarfile
from pathlib import Path
b=Path(sys.argv[1]);root=b/('src_'+sys.argv[2])
with tarfile.open(b/'source.tar.gz') as t:
 for m in t.getmembers():
  if m.isfile() or m.issym():
   p=root/m.name
   if p.exists() or p.is_symlink():p.unlink()
 t.extractall(root)
PYUNLINK" || exit 13
rsync -azW --partial --timeout=120 "$CACHE16/" $HOST:$B/a/views/synth/ || exit 13
scp -q "$CACHED/views/views.json" $HOST:$B/a/views/views.json || exit 13
scp -q "$CACHED/pre_relay_colm.json" $HOST:$B/a/views/contract.json || exit 13
ssh $HOST "set -e; cp -al $B/a/views $B/p/views; cp -al $B/a/views $B/q/views; ln -sfn $B/src $B/p/src; ln -sfn $B/src $B/q/src" || exit 13
step S3a source_bound_colm_case_a
gen $B/a case_a diag "--lane-reach diag $CM --coord-map-re . --carve-reserved all" || { echo S3A_GEN_FAIL; exit 13; }
python3 "$W/results/arch/hbm_release_r16_1021/verify_model_homes.py" "$W/$PD/corridor_model.json" "$A/case_a_manifest.json" "$A/actual_model_A.json" || { echo MODEL_A_NOT_REALIZED; exit 25; }
python3 "$W/results/arch/hbm_release_r16_1021/verify_rootaware_identity.py" "$W/results/arch/hbm_no_window_decomposition_1021/root_aware_model.json" "$A/case_a_manifest.json" "$W/$PD/d4g_region_map.json" "$A/rootaware_A.json" || { echo ROOT_A_IDENTITY_FAIL; exit 25; }
ft_usage $A/case_a_manifest.json case_a
step S3bq source_bound_colm_pins
gen $B/p case_p diag "--prior-place $B/a/case_a/run.tcl --lane-reach diag --relay-outline density $CM --coord-map-re . --carve-reserved all" > $A/s3b.log 2>&1 &
S3B=$!
gen $B/q x12_q diag "--prior-place $B/a/case_a/run.tcl --lane-reach diag $GX $CM --coord-map-re ^(std|stu)_" > $A/s3q.log 2>&1 &
S3Q=$!
wait $S3B; R3B=$?; wait $S3Q; R3Q=$?; cat $A/s3b.log $A/s3q.log
[ $R3B = 0 ] && [ $R3Q = 0 ] || { echo GEN_PQ_FAIL; exit 13; }
stop_future "AFTER_PQ completed_workers"
for tag in case_p x12_q; do python3 "$W/results/arch/hbm_release_r16_1021/verify_model_homes.py" "$W/$PD/corridor_model.json" "$A/${tag}_manifest.json" "$A/actual_model_${tag}.json" || { echo MODEL_PQ_NOT_REALIZED; exit 25; }; done
for tag in case_p x12_q; do python3 "$W/results/arch/hbm_release_r16_1021/verify_rootaware_identity.py" "$W/results/arch/hbm_no_window_decomposition_1021/root_aware_model.json" "$A/${tag}_manifest.json" "$W/$PD/d4g_region_map.json" "$A/rootaware_${tag}.json" || { echo ROOT_PQ_IDENTITY_FAIL; exit 25; }; done
else
  # HBM-DIE17 RESUME_S4: staged remote root + A/P/Q GEN of this run kept (S3 verdicts above in this log); re-stage only the
  # tool files changed since that staging (hardlinks broken first), then rerun S4..S11.
  echo "RESUME_S4 from staged $B (S3 A/P/Q of this run reused) HEAD $H $(date -Is)"
  for f in ${RESUME_TOOLS:-tools/hbm_die_v15/die_relay_stations.py}; do
    git -C $W show HEAD:$f | ssh $HOST "rm -f $B/src/$f && cat > $B/src/$f" || { echo RESUME_RESTAGE_FAIL $f; exit 14; }
    [ "$(ssh $HOST sha256sum $B/src/$f | cut -d' ' -f1)" = "$(git -C $W show HEAD:$f | sha256sum | cut -d' ' -f1)" ] || { echo RESUME_SHA_FAIL $f; exit 14; }
    echo "RESUME_RESTAGED $f"
  done
  ssh $HOST "rm -f $B/S4_DONE $B/S5_LAYER_DONE"
fi
# ---------------- HBM-DIE17 r16q: S4 + S5 + S5b remote, S4 capacity gate RECORDED (diag) so the die reaches GRT/STA/CLK ----------------
# Owner 10-21 closure push: real GRT overflow / STA / clock numbers on the current die beat a capacity model; the S4 capacity
# verdict is still emitted (S4_CAPACITY_GATE ...) and kept as a release blocker until it reads 0/0/0.
# ---------------- S4 + S5 + S5b remote (capacity planner) || lockstep ----------------
if [ -z "${RESUME_S5L:-}" ]; then
step S4_S5 remote_capacity_stations_layer
scp -q results/arch/hbm_release_r16_1021/s4s5_remote_q.sh $HOST:$B/s4s5_remote.sh || exit 14
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
Claude-Session: https://claude.ai/code/session_01VFyQ4mXgp29XPHp3K9ddAm" -- $TC || { echo S5T_COMMIT_FAIL; exit 15; }
  H=$(git -C $W rev-parse --short=9 HEAD); echo "S5T_COMMITTED $H"; git -C $W push -q origin $BR 2>&1 | tail -1
fi
step S5S strict_unread_local
# HBM-DIE11: strict unread review/proposal/replay need git history of the exact source (remote src is an archive) -> here, gated
# strict needs a RENEWED semantic review (L21 review pins pre-l24 ot_hbm_svc_sm_xcal_rel_t.sv; h9c rebind also renews it):
# recorded as DIAGNOSTIC FAIL (release needs PASS); structural bind (unread only, transfer remaining 0) is the gate here
strict_manifest $A/net/post_landing.json $A/pb S5 || echo "S5_STRICT_NOT_PASS recorded (DIAGNOSTIC; l25 renewed review path; release needs PASS)"
strict_manifest $A/net/contract_pre.json $A/pb5b S5B || echo "S5B_STRICT_NOT_PASS recorded (DIAGNOSTIC; renewed review owed)"
step S5L relay_lockstep
bash results/arch/hbm_release_r15_1021/lockstep_runner_unpinned.sh $A/net/relays_d4g_land.json.gz $A/lockstep 120 > $A/lockstep_land.log 2>&1; tail -12 $A/lockstep_land.log
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
FOREST_X=''; [ "$RST_FORM" = rfc ] && FOREST_X="--overfly-masters 'hbfd_(rly|lh|land)' --max-root-tries 57 --host-hops prefer --route-detour 2.0 --host-form rfc"
echo "S8_RST_FORM $RST_FORM $FOREST_X"
P=$B/forest; ssh $HOST "rm -rf $P && mkdir -p $P/relay_views && cp -al $B/case_b/views $P/views" || exit 18
scp -q $AC/forest/relay_views/*.lef $HOST:$P/relay_views/ && scp -q $A/net/contract_pre.json $HOST:$P/contract_pre.json || exit 18
git -C $W archive HEAD tools/hbm_die_v16 tools/hbm_die_v15 tools/die_port_bind.py tools/die_reach.py rtl/hbm_accel/die_glue rtl/lib | ssh $HOST "rm -rf $P/src && mkdir -p $P/src && tar -x -C $P/src" || exit 18
$OTRUN --mem 32 --threads 1 --disk 10 --priority die --dir $P -- bash -c "cd src/tools/hbm_die_v16 && OT_FOREST_LOG=1 /usr/bin/time -v python3 reset_forest_layer.py --relay-rows $FOREST_X --contract $P/contract_pre.json --manifest $B/case_b/manifest.json --views $P/views --relay-views $P/relay_views --out $P/layer.json --report $P/report.json && gzip -kf $P/layer.json" > $A/forest_plan.otrun 2>&1
echo "FOREST_PLAN rc=$?"; tail -3 $A/forest_plan.otrun
scp -q $HOST:$P/report.json $A/net/forest_report.json
scp -q $HOST:$P/layer.json.gz $A/net/forest_layer.json.gz || { echo S8_FOREST_PLAN_FAIL; head -c 1500 $A/net/forest_report.json; exit 18; }
python3 tools/hbm_die_v16/d4g_relay_splice.py $A/net/contract_pre.json $A/net/forest_layer.json.gz $A/net/contract_forest.json --report $A/net/forest_splice.json \
  > $A/net/forest_splice.log 2>&1 || { echo S8_FOREST_SPLICE_FAIL; tail -5 $A/net/forest_splice.log; exit 18; }
tail -1 $A/net/forest_splice.log
if [ "$RST_FORM" = rfc ]; then
  step S8r l27_rfc_closed_views
  python3 results/arch/hbm_release_r15_1021/collect_closed.py || exit 18
  python3 tools/hbm_die_v16/d4g_layers/l27_rfc_closed_views.py $A/net/contract_forest.json $A/net/contract_forest_rfc.json --report $A/net/l27_rfc.json || { echo S8R_L27_FAIL; exit 18; }
  mv $A/net/contract_forest_rfc.json $A/net/contract_forest.json
fi
step S8b l12_banklat
python3 tools/hbm_die_v16/d4g_layers/l12_banklat.py $A/net/contract_forest.json $A/net/contract.json --report $A/net/l12_banklat.json --budget-overlay results/arch/hbm_release_r15_1021/l12_budget_h158.json \
  > $A/net/l12.log 2>&1 || { echo S8B_L12_FAIL; tail -8 $A/net/l12.log; exit 18; }
tail -2 $A/net/l12.log
python3 tools/hbm_die_v16/d4g_layers/l29_rootctl_closed.py $A/net/contract.json $A/net/contract.json --latency-report $A/net/l12_banklat.json --report $A/net/l29_rootctl_binding.json || exit 18
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
# Reuse the actual GEN geometry verdict before spending on a physical route.
python3 - "$A/case_manifest.json" <<'PYGEOM'
import json,sys
m=json.load(open(sys.argv[1])); bad=m.get('placement_problems', [])
if bad: raise SystemExit('GRT_HELD_FOR_GEOMETRY: '+repr(bad))
PYGEOM
[ $? = 0 ] || exit 20
step S11 grt_sta_clk
$OTRUN --mem 160 --threads 16 --disk 60 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
# Existing mandatory IR step, sourced from the actual GRT database; missing ODB is NOT_RUN/FAIL.
step S11i required_ir_drop
$OTRUN --mem 32 --threads 8 --disk 4 --priority die --dir $B/case -- env OT_IR_DESIGN=hbm CPUS=8 MEMG=32 bash $B/src/tools/die_safety/ir_step.sh $B/case/out/grt.odb $B/case/out/ir_drop $B/case/out/run.log > $A/ir_drop.otrun 2>&1
IR_RC=$?
grep -E 'DIE_IR_DROP|OWNER_REPORT' $A/ir_drop.otrun || true
[ $IR_RC = 0 ] || echo "OWNER_REPORT HBM die IR-drop failed or NOT_RUN; see $A/ir_drop.otrun"
ssh $HOST "cat $B/case/out/run.exit; grep -E 'OT_PG_|OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log; tail -5 $B/case/out/hold_budget.log" > $A/grt_summary.txt 2>&1
rsync -a $HOST:$B/case/out/ $A/case_out/ --include='*.json' --include='*.log' --include='*.rpt' --include='*.png' --exclude='*.odb' --exclude='*.def' 2>/dev/null
cat $A/grt_summary.txt
[ "$IR_RC" = 0 ] || exit 21
echo CHAIN_HBM_R15_NEXT_DONE VAR=$VAR PLAN=$PL HEAD=$H
