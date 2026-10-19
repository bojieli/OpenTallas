#!/bin/bash
# TW5-GEN2E 10-19 GEN2e chain = the next HBM d4g die generation on top of GEN2d (branch claude/hd4g-gen2e-1019, wt/hd4g-gen2e):
#   GEN2c + RSTROW relay-row reset forest + (a) INT8 SM path (l13_int8, COORD 0ki) + (b) HC closed ring (grants + l11, b0 DRLY 2)
#   + (d) GEN2e grant slots for every generated-home block (d4g_gen2e_grants_homes.py: IDX scorers in idxs_<q>, hc_eng at the
#   ring-hub centroid, wbk in the SM pair gaps, xq SE/NE slot renames, 42 more) + (e) l12_banklat (TW5-BANKLATDIE) post-landing.
# New geometry -> the FULL generation pipeline (model: d4g_gen2/chain_d4g2.sh S1..S6, d4g_gen2c/chain_d4g2c_nf2.sh, d4g_gen2d/chain_d4g2d.sh):
#  S1 pre-relay layers (run_layers l1..l8 + l9 + l10 + l11 + l13) + strict/functional bind -> S2 synth round a -> S3 GEN2e case_a
#  (relay-free, diag) -> S3i INSPECTION GATE (waits for $A/case_a_GO written by an agent after looking at case_a_layout.png;
#  $A/case_a_STOP aborts) -> S4 root sites + pins + stations -> S5 lanes + LANDING step (relay+landing layer, lockstep, splice)
#  -> S5b post layers l7_wire + l12_banklat (waits banklat/DONE) + strict/functional bind -> S6 synth round b -> S7 GEN case_b
#  (post-landing, diag, prior homes = case_a) -> S8 relay-row reset forest plan on case_b + splice + bind -> S9 synth round c
#  -> S10 GEN (OT_RESET_GATE=fail, prior homes = case_b) -> S11 GRT + STA TT/FF + neighbour-skew/clock + hold budget.
# LH-GEN2E 10-19 ~12:00 RESTART as GEN2e2 (branch claude/hd4g-gen2e2-1019 = codex/hd4g-strict-1019 a421fa8ab + profile tool):
#  S1 input = Codex's pre-relay contract with l14 scoped RTL, l15 SMB relative, l16 VM fault, l17 router IDs, l16b score fault
#  (pre_l17_score_codex.json, strict structural 0) + l19 IDX256 programme-depth guard (re-run here byte-identical, fd7492f2).
#  Strict bind: main-strict die_port_bind; structural classes must be 0; unread_net_bits is RECORDED (ROOT manifest 65,066 for
#  the d517 die only; residual open) and does not stop the diagnostic physical chain -> every result DIAGNOSTIC until unread PASS.
#  S5 / S8b: d4g_su_lane_profile.py records the EMITTED lanes; S8b requires every SU pgslice_lg at 18/15 (codex 708d112f3 basis)
#  with LAT strict, else FAIL (reprice / re-harden, never absorb).  Data host ot-epyc6 (6 TB scratch), unpinned ot-run + --disk.
# LEAD2-HBM/L2H-GEN2E 10-19 16:5x RESUME from S3 (S1/S2 done 11:53-14:01): the 18 S2 duplicate-read failures were replaced by the
#  corrected failed-only replays (fa719ed07 79-job/142-view identity, final_manifest_1019) and admitted into vplan_a/synth by the strict
#  v16_fetch (source bytes vs 6f783d0a1, ETM ports vs pre_relay contract fd7492f2) -> fetch_a_corrected.log.  SYNTH views = LABELLED
#  stand-ins (native_qualified=false, D5): never closure, never block GEN/GRT/STA.  Unread 70,320 remains the strict-bind FAIL (diag).
set -o pipefail
HOST=ot-epyc6; AE=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e
W=/home/ubuntu/wt/hd4g-gen2e; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2e2; R=/home/ubuntu/OpenTallas
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1; A2=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
AC=/home/ubuntu/artifacts/hdie-d4/d4g_gen2c; AD=/home/ubuntu/artifacts/hdie-d4/d4g_gen2d
B=/srv/opentallas-scratch/claude/hd4g/gen2e2; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; BR=claude/hd4g-gen2e2-1019
step() { echo "STEP $* $(date -Is)"; }
echo $$ > $A/chain.pid
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
cd $W
H=$(git -C $W rev-parse --short=9 HEAD); echo "CHAIN chain_d4g2e2_s3.sh (L2H-GEN2E resume S3; LH-GEN2E restart: strict l14-l19 pre-relay, S4/S5 + 18/15 profile gate) HEAD $H $(date -Is)"
ssh $HOST "mkdir -p $B" || exit 9
FOREST_SRC_PATHS="rtl/hbm_accel/die_glue/hbfd_rrl.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly_rr.sv rtl/hbm_accel/die_glue/hbfd_rly_rr_masters.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_pad.sv rtl/hdc/ot_hdc_delay.sv"
METAS="$A0/vplan/synth $A1/vplan/synth $A2/vplan_fast/synth $A2/vplan_a0/synth $A2/vplan_a1/synth $A2/vplan_a/synth $A2/vplan/synth $A2/vplan_b1/synth $AC/vplan_pre/synth $AC/vplan/synth $AD/vplan/synth $AE/vplan_a/synth"
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
   'physical/hbm_mtp/rtl','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
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
  for h in ot-pve1 ot-epyc5 ot-epyc4; do ssh $HOST "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
  N0=$(ssh -o ControlPath=none $HOST "find $B/src_$H | wc -l")
  for h in ot-pve1 ot-epyc5 ot-epyc4; do n=$(ssh -o ControlPath=none $h "find $B/src_$H 2>/dev/null | wc -l"); echo "SRC $h $n/$N0"
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
  sed 's#--diagnostic-param-alias#--diagnostic-param-alias ${OT_DIE_CASE_EXTRA}#' $A2/gen_d4g2.sh > $A/gen_d4g2e.sh
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
step S1S2 skipped_resume "pre_relay fd7492f2 + vplan_a 79 synth views (57 new incl 18 corrected + 22 reuse)"
step S3 gen2e_case_a
views_up $A/vplan_a $A/net/pre_relay.json || exit 17
gen case_a diag "" || { echo S3_GEN_A_FAIL; exit 13; }
# ---------------- S3i geometry inspection gate (owner rule: inspect the die layout before the long GEN) ----------------
step S3i inspect_wait "agent: look at $A/case_a_layout.png + GENERATED_HOMES line, then 'touch $A/case_a_GO' (or write case_a_STOP)"
while [ ! -f $A/case_a_GO ]; do [ -f $A/case_a_STOP ] && { echo "S3I_STOP $(head -3 $A/case_a_STOP)"; exit 14; }; sleep 120; done
echo "S3i GO $(head -2 $A/case_a_GO)"
# ---------------- S4 root sites / pins / stations ----------------
step S4 root_sites_pins_stations
python3 tools/hbm_die_v16/d4g_root_sites.py --region-map $D/d4g_region_map.json --manifest $A/case_a_manifest.json --out $A/root_sites_d4g2e.json || exit 14
scp -q $A/root_sites_d4g2e.json $HOST:$B/ || exit 14
$OTRUN --mem 8 --threads 1 --disk 5 --dir $B/case_a -- bash -c "cd $B/src && PYTHONDONTWRITEBYTECODE=1 python3 tools/hbm_die_v16/case_pin_centroids.py \
  $B/case_a --out $B/pins_case_a.json.gz" > $A/pins.otrun 2>&1 || { echo S4_PINS_FAIL; tail -4 $A/pins.otrun; exit 14; }
$OTRUN --mem 32 --threads 16 --disk 5 --priority die --dir $B/case_a -- bash -c "cd $B/src && PYTHONDONTWRITEBYTECODE=1 python3 tools/hbm_die_v15/die_relay_stations.py \
  $B/case_a --contract $B/views/contract.json --reach 405 --route-grid 10 --jobs 16 --root-keepouts $B/root_sites_d4g2e.json \
  --out $B/stations_case_a_405.json" > $A/stations.otrun 2>&1 || { echo S4_STATIONS_FAIL; tail -8 $A/stations.otrun; exit 14; }
scp -q $HOST:$B/pins_case_a.json.gz $HOST:$B/stations_case_a_405.json $A/ || exit 14
python3 tools/hbm_die_v16/d4g_bus_model_gen2.py --contract $A/net/pre_relay.json.gz --manifest $A/case_a_manifest.json \
  --plan $D/plan/d4g_phy/compact.P.json --label gen2e_case_a --out $A/d4g_gen2e_bus_model_case_a.json --png $A/d4g_gen2e_bus_model_case_a.png \
  > $A/bus_model.log 2>&1; echo "BUS_MODEL rc=$?"; tail -4 $A/bus_model.log
# ---------------- S5 lanes + LANDING step ----------------
step S5 lanes_landing
python3 tools/hbm_die_v16/relay_lanes_d4f.py --stations $A/stations_case_a_405.json --pins $A/pins_case_a.json.gz \
  --contract $A/net/pre_relay.json.gz --manifest $A/case_a_manifest.json --root-keepouts $A/root_sites_d4g2e.json \
  --jobs 8 --out $A/stations_gen2e_lanes.json --report $A/lanes_report.json > $A/lanes.log 2>&1 || { echo S5_LANES_FAIL; tail $A/lanes.log; exit 15; }
mkdir -p $W/tools/hbm_die_v15/v16_relays
bash tools/hbm_die_v16/d4g_land_step.sh $A $A/stations_gen2e_lanes.json - $A/case_a_manifest.json $A/root_sites_d4g2e.json \
  $A/net/pre_relay.json.gz $D/landing/land_plan_d4g.json 120 > $A/land_step.log 2>&1; rc=$?; tail -12 $A/land_step.log
[ $rc = 0 ] || { echo "S5_LAND_STEP_FAIL rc=$rc"; exit 15; }
cp $A/net/contract.json $A/net/post_landing.json
# emitted S4/S5 lanes vs the 18/15 source basis (record only: l12_banklat pads at S8b; delta > 0 = priced cycles for the schedule)
python3 tools/hbm_die_v16/d4g_su_lane_profile.py $A/net/post_landing.json --stage post_landing --out $A/su_lane_profile_post_landing.json | head -6
# ---------------- S5b post-landing layer l7_wire (l12_banklat runs LAST, after the forest splice: pads copy forest resets) ----------------
step S5b post_l7
python3 tools/hbm_die_v16/d4g_layers/l7_wire.py $A/net/post_landing.json $A/net/contract_l7.json --report $A/net/l7_wire_post.json > $A/net/l7_post.log 2>&1 \
  || { echo S5B_L7_FAIL; tail -3 $A/net/l7_post.log; exit 16; }
cp $A/net/contract_l7.json $A/net/contract_pre.json
bind2 $A/net/contract_pre.json $A/pb S5B "--lat warn" || exit 16
# ---------------- S6 / S7 post-landing case (forest basis) ----------------
step S6 synth_b
synth_round $A/net/contract_pre.json $A/vplan_b b $A/vplan_a || exit $?
step S7 gen2e_case_b_postlanding
views_up $A/vplan_b $A/net/contract_pre.json || exit 17
ssh $HOST "cp $B/case_a/run.tcl $B/prior_case_a.tcl" || exit 17
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
# ---------------- S9 / S10 final GEN (reset gate FAIL) ----------------
step S9 synth_c
synth_round $A/net/contract.json $A/vplan c $A/vplan_b || exit $?
python3 tools/hbm_die_v16/d4g_bindings.py --views $A/vplan/views.json --grants $D/grants_d4g.json --out $A/view_bindings.json
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
echo CHAIN_D4G2E_DONE HEAD=$H
