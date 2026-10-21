#!/bin/bash
# O2 precise six-slot binding recovery, same O intended73/source/geometry.
# Model0ebafacb8: six dedicated actualmaster/body slots plus explicit CLI maps.
# Fail closed on actualmodelhome mismatch AFTER A and P/Q, before later stages.
# Owned localartifact STOP_FUTURE_STAGES marker stops at next phase boundary;
# it never signals admitted jobs or edits source/input/results.
# Same74S2/H/fullreticle/currentHC23; no sourceupgrade/guardrelax/newS2.
# Source-pinned fresh.keepstage; GEN/PQ/S4only, never S5/route.
set -o pipefail
VAR=${1:?plan M|F}; PL=B; PLAN_UM=300; HOST=ot-epyc5
W=/home/ubuntu/wt/codex-hbm-die-o2-binding-1021; AR=/home/ubuntu/artifacts/hdie-d4/codex_hbm_r16o2_binding_1021; RST_FORM=${RST_FORM:-rfc}; A=$AR/plan$VAR
R11A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r11/plan$PL; R11B=/srv/opentallas-scratch/claude/hbm-die11-1020/plan$PL
A7=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4_r7portage; B7=/srv/opentallas-scratch/claude/hbm-die7-gen2e4r6-1020
OLDA=/srv/opentallas-scratch/claude/hd4g/gen2e4
AE=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e; AE4=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e4; AE3=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e3; AE2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e2
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1; A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c; AD=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d
B=/srv/opentallas-scratch/claude/codex-hbm-r16o2-binding-1021/chain$VAR; OLD=/srv/opentallas-scratch/claude/codex-hbm-r15-h158-grants-1021/chainB; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; PD=results/arch/hbm_release_r16_1021/plan$VAR; BR=codex/hbm-die-o2-binding-1021
GX="${OT_D9_GEN_EXTRA:---relay-outline density --lane-reach-repair 3 --lane-reach-lookahead chain --grt-layer-plan owner1020 --signal-top-layer M8 --carve-reserved all}"
CM="--coord-map $PD/coord_map.json --slot-map $(cat $W/$PD/slot_map.txt)"
# Local transport override only in this successor process: ep6 public route loses packets.
ssh() { local host=; for host in "$@"; do [ "$host" = ot-epyc6 ] && { command ssh -C -J ot-epyc5 -S none "$@"; return $?; }; done; command ssh -C -o ControlPath=none "$@"; }
scp() { local arg=; for arg in "$@"; do [[ "$arg" == ot-epyc6:* ]] && { command scp -C -o ProxyJump=ot-epyc5 -o ControlPath=none "$@"; return $?; }; done; command scp -C -o ControlPath=none "$@"; }
step() { if [ -e "$A/STOP_FUTURE_STAGES" ]; then echo "OWNED_STOP_FUTURE_STAGES before=$* source=$H $(date -Is)"; exit 26; fi; echo "STEP $* $(date -Is)"; }
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
step S3_STAGE exact_source_colh
python3 - "$CACHED/reuse.json" "$CACHED/pre_relay_colm.json" "$W/$PD/corridor_model.json" <<'PYREADY'
import json,sys
m=json.load(open(sys.argv[3]));assert len(m['placement_checks'])==73 and not any(i['fixed_body_overlaps'] for i in m['placement_checks']);assert m['rtl_changes']==m['guard_changes']==m['cycle_credit']==0
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
ssh $HOST "set -e; test ! -e $B; mkdir -p $B/a $B/p $B/q; touch $B/.keep /srv/opentallas-scratch/claude/codex-hbm-r16o2-binding-1021/.keep; cp -al \$(readlink -f $J/src) $B/src_$H; ln -sfn $B/src_$H $B/src; cp -al $J/a/views $B/a/views; rm -f $B/a/views/views.json $B/a/views/contract.json; ln -sfn $B/src $B/a/src" || exit 13
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
ft_usage $A/case_a_manifest.json case_a
step S3bq source_bound_colm_pins
gen $B/p case_p diag "--prior-place $B/a/case_a/run.tcl --lane-reach diag --relay-outline density $CM --coord-map-re . --carve-reserved all" > $A/s3b.log 2>&1 &
S3B=$!
gen $B/q x12_q diag "--prior-place $B/a/case_a/run.tcl --lane-reach diag $GX $CM --coord-map-re ^(std|stu)_" > $A/s3q.log 2>&1 &
S3Q=$!
wait $S3B; R3B=$?; wait $S3Q; R3Q=$?; cat $A/s3b.log $A/s3q.log
[ $R3B = 0 ] && [ $R3Q = 0 ] || { echo GEN_PQ_FAIL; exit 13; }
for tag in case_p x12_q; do python3 "$W/results/arch/hbm_release_r16_1021/verify_model_homes.py" "$W/$PD/corridor_model.json" "$A/${tag}_manifest.json" "$A/actual_model_${tag}.json" || { echo MODEL_PQ_NOT_REALIZED; exit 25; }; done
step S4_ONLY exact_source_colh_capacity
scp -q $W/results/arch/hbm_release_r16_1021/s4_only_remote.sh $HOST:$B/s4_only_remote.sh || exit 14
$OTRUN --mem 96 --threads 16 --disk 20 --priority die --dir $B -- env B=$B H=$H PD=$PD OT_CAP_ARGS="--plan-um $PLAN_UM" PINS_CASE=$B/q/x12_q PINS_A_L23=1 bash $B/s4_only_remote.sh > $A/s4_only.otrun 2>&1
rc=$?; grep -E '^(STEP|S4_|PINS|CAPACITY)' $A/s4_only.otrun | cut -c1-400
rsync -azW --partial --timeout=120 $HOST:$B/artifacts/ $A/ || true
echo "SOURCE_BOUND_COLH_S4_TERMINAL rc=$rc NO_S5_ROUTE; externalarrival/reset/calendar qualification OPEN";exit $rc
