#!/bin/bash
# H-D4G-GEN2 chain (local driver, fleet for every heavy step; branch claude/hd4g-gen2-1018, worktree wt/hd4g-gen2).
# GEN2 = NEW geometry (SMFRAME +276.48 SM column, SFUPLAN orientations/positions, SET 2 slots, COLLQ slots) + GEN2 netlist
# (GEN1 layers + l5_host_ep + l5b_cij4 + l6_collq), so stations cannot come from the GEN0 case: a relay-free GEN2a placement
# case on the GEN2 plan gives the pins / stations / root sites, then the relay (or LANDING) layer, then GEN2 + GRT2.
#  S0 wait GEN1 end (chain_d4g1 exits) -> S0b landing: merge claude/hland-1018 (+ hland-rtl) if it carries d4g_land_step.sh
#  -> S1 layers (pre-relay) + strict bind -> S2 views + SYNTH new cells (reuse GEN0/GEN1) -> S3 GEN2a relay-free case
#  -> S4 root sites (GEN2a manifest) + pins + stations -> S5 lanes + relay layer (LANDING step when merged) + splice + bind
#  -> S6 views + SYNTH relay/landing masters -> S7 GEN2 (reset gate FAIL mode) + bus model on GEN2a -> S8 GRT2 + TT/FF clock gate.
set -o pipefail
W=/home/ubuntu/wt/hd4g-gen2; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen2
A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0; A1=/home/ubuntu/artifacts/hdie-d4/d4g_gen1
B=/srv/opentallas-scratch/claude/hd4g/gen2; B0=/srv/opentallas-scratch/claude/hd4g/gen0; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g; BR=claude/hd4g-gen2-1018
step() { echo "STEP $* $(date -Is)"; }
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
step S0 wait_gen1_end
while pgrep -f 'bash chain_d4g1.sh' >/dev/null; do sleep 300; done
echo "GEN1_END $(grep -E '^(STEP|GEN ot-run|GRT ot-run|CHAIN_D4G1_DONE|S[0-9]_|GEN0_|SYNTH_MISSING)' $A1/chain_d4g1.log | tail -3 | tr '\n' ' ')"
step S0b landing
git -C /home/ubuntu/OpenTallas fetch -q origin || true
LAND=0
if git -C $W cat-file -e origin/claude/hland-1018:tools/hbm_die_v16/d4g_land_step.sh 2>/dev/null; then
  if git -C $W merge --no-edit -q origin/claude/hland-1018 && { git -C $W merge-base --is-ancestor origin/claude/hland-rtl-1018 HEAD \
       || git -C $W merge --no-edit -q origin/claude/hland-rtl-1018; }; then
    LAND=1; git -C $W push -q origin HEAD:$BR || echo PUSH_WARN; echo "LANDING merged: $(git -C $W log --oneline -1)"
  else
    git -C $W merge --abort 2>/dev/null; echo "LANDING_NOT_USED: merge of claude/hland-1018 conflicted (aborted) -> GEN2 runs WITHOUT landings"
  fi
else
  echo "LANDING_NOT_USED: claude/hland-1018 has no tools/hbm_die_v16/d4g_land_step.sh at $(date -Is) -> GEN2 runs WITHOUT landings (plain relays)"
fi
H=$(git -C $W rev-parse --short=9 HEAD); echo "HEAD $H LAND=$LAND"
ssh ot-epyc4 "mkdir -p $B" || exit 9
step S1 layers
mkdir -p $A/net $A/pb0; cd $W
python3 tools/hbm_die_v16/d4g_layers/run_layers.py $D/gen0/contract.json.gz $A/net/pre_relay.json.gz --report-dir $A/net > $A/net/layers.log 2>&1 \
  || { echo S1_LAYERS_FAIL; tail $A/net/layers.log; exit 11; }
tail -6 $A/net/layers.log
python3 -c "import gzip,shutil; shutil.copyfileobj(gzip.open('$A/net/pre_relay.json.gz'), open('$A/net/pre_relay.json','wb'))"
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $A/net/pre_relay.json $A/pb0 > /dev/null; tail -1 $A/pb0/port_bind.log
grep -q "^DIE_PORT_BIND PASS" $A/pb0/port_bind.log || { echo S1_BIND_FAIL; grep '^FAIL' $A/pb0/port_bind.log | head; exit 11; }
# synth views of every master: GEN0 + GEN1 metas, then SYNTH only what neither has (same wrapper text)
synth_round() {   # $1 contract  $2 vplan dir  $3 tag
  rm -rf $2; python3 tools/hbm_die_v15/v16_views.py --out $2 --contract $1 | tail -3
  rm -rf $A/synmeta_$3; mkdir -p $A/synmeta_$3
  for P in $A0/vplan/synth $A1/vplan/synth $A/vplan_a/synth; do [ -d $P ] && (cd $P && tar -cf - */meta.json 2>/dev/null) | tar -x -C $A/synmeta_$3; done
  PREV=$A0/vplan; [ -f $A1/vplan/views.json ] && PREV=$A1/vplan
  python3 tools/hbm_die_v16/synth_reuse_r8b.py --views $2 --metas $A/synmeta_$3 --root $W --out $A/reuse_$3.json --prev $PREV > $A/reuse_$3.log; tail -3 $A/reuse_$3.log | cut -c1-600
  CELLS=$(grep '^SYNTH ' $A/reuse_$3.log | cut -d' ' -f2-)
  python3 - $2 > $A/src_paths_$3.txt <<PY
import json, sys
V=json.load(open(sys.argv[1] + '/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/hbm_mtp/rtl','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
print('\n'.join(sorted(p)))
PY
  ssh ot-epyc4 "rm -rf $B/src_$H" || return 15
  git -C $W archive HEAD $(cat $A/src_paths_$3.txt) | ssh ot-epyc4 "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || return 15
  tar -C $2/wrap -cf - . | ssh ot-epyc4 "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || return 15
  for h in ot-agidock128 ot-pve1 ot-epyc5; do ssh ot-epyc4 "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
  echo "SYNTH_$3 $CELLS"
  if [ -n "${CELLS// /}" ]; then
    (cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $2 --commit $H --remote-root $B $CELLS > $A/drive_$3.log 2>&1); tail -2 $A/drive_$3.log
    python3 $W/tools/hbm_die_v15/v16_fetch.py --views $2 --remote-root $B --commit $H --contract $1 $CELLS > $A/fetch_$3.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch_$3.log
    MISS=""; for c in $CELLS; do [ -f $2/synth/$c/meta.json ] || MISS="$MISS $c"; done
    [ -n "$MISS" ] && { echo "SYNTH_MISSING_$3$MISS (no stubs: every SYNTH view needed)"; return 16; }
  fi
  return 0
}
views_up() {      # $1 vplan dir  $2 contract  -> $B/views (GEN0 + GEN1 + GEN2 synth overlays)
  ssh ot-epyc4 "rm -rf $B/views && mkdir -p $B/views/synth" || return 17
  rsync -a $A0/vplan/synth/ ot-epyc4:$B/views/synth/ 2>/dev/null; [ -d $A1/vplan/synth ] && rsync -a $A1/vplan/synth/ ot-epyc4:$B/views/synth/
  [ -d $A/vplan_a/synth ] && rsync -a $A/vplan_a/synth/ ot-epyc4:$B/views/synth/; [ -d $1/synth ] && rsync -a $1/synth/ ot-epyc4:$B/views/synth/
  scp -q $1/views.json ot-epyc4:$B/views/ && scp -q $2 ot-epyc4:$B/views/contract.json || return 17
}
step S2 views_synth_prerelay
synth_round $A/net/pre_relay.json $A/vplan_a a || exit $?
step S3 gen2a_relay_free
views_up $A/vplan_a $A/net/pre_relay.json || exit 17
scp -q $A/gen_d4g2.sh ot-epyc4:$B/gen_d4g2.sh || exit 17
$OTRUN --mem 64 --threads 2 --hosts ot-epyc4 --priority die --dir $B -- env OT_ABS_PIN_WINDOW_UM=3 OT_RESET_GATE=diag OT_GEN2_CASE=case_a \
  bash $B/gen_d4g2.sh > $A/gen_a.otrun 2>&1; echo "GEN2a ot-run rc=$? $(date -Is)"; tail -12 $A/gen_a.otrun
grep -q GEN_OK $A/gen_a.otrun || { echo S3_GEN2A_FAIL; exit 13; }
scp -q ot-epyc4:$B/case_a/manifest.json $A/gen2a_manifest.json && scp -q ot-epyc4:$B/case_a/layout.png $A/gen2a_layout.png 2>/dev/null
[ -f $A/gen2a_manifest.json ] || exit 13
step S4 root_sites_pins_stations
python3 tools/hbm_die_v16/d4g_root_sites.py --region-map $D/d4g_region_map.json --manifest $A/gen2a_manifest.json --out $A/root_sites_d4g2.json || exit 14
scp -q $A/root_sites_d4g2.json ot-epyc4:$B/ || exit 14
$OTRUN --mem 8 --threads 1 --hosts ot-epyc4 --dir $B/src -- env PYTHONDONTWRITEBYTECODE=1 python3 tools/hbm_die_v16/case_pin_centroids.py \
  $B/case_a --out $B/pins_gen2a.json.gz > $A/pins.otrun 2>&1 || { echo S4_PINS_FAIL; tail -4 $A/pins.otrun; exit 14; }
$OTRUN --mem 32 --threads 16 --hosts ot-epyc4 --priority die --dir $B/src -- env PYTHONDONTWRITEBYTECODE=1 python3 tools/hbm_die_v15/die_relay_stations.py \
  $B/case_a --contract $B/views/contract.json --reach 405 --route-grid 10 --jobs 16 --root-keepouts $B/root_sites_d4g2.json \
  --out $B/stations_gen2a_405.json > $A/stations.otrun 2>&1 || { echo S4_STATIONS_FAIL; tail -8 $A/stations.otrun; exit 14; }
scp -q ot-epyc4:$B/pins_gen2a.json.gz ot-epyc4:$B/stations_gen2a_405.json $A/ || exit 14
# bus / lever-2 model on the real GEN2a placement (replaces the stale run8-manifest d4g_vs_b numbers)
python3 tools/hbm_die_v16/d4g_bus_model_gen2.py --contract $A/net/pre_relay.json.gz --manifest $A/gen2a_manifest.json \
  --plan $D/plan/d4g_phy/compact.P.json --label gen2a_case --out $A/d4g_gen2_bus_model_case.json --png $A/d4g_gen2_bus_model_case.png \
  > $A/bus_model.log 2>&1; echo "BUS_MODEL rc=$?"; tail -4 $A/bus_model.log
step S5 lanes_relays
python3 tools/hbm_die_v16/relay_lanes_d4f.py --stations $A/stations_gen2a_405.json --pins $A/pins_gen2a.json.gz \
  --contract $A/net/pre_relay.json.gz --manifest $A/gen2a_manifest.json --root-keepouts $A/root_sites_d4g2.json \
  --jobs 12 --out $A/stations_gen2_lanes.json --report $A/lanes_report.json > $A/lanes.log 2>&1 || { echo S5_LANES_FAIL; tail $A/lanes.log; exit 15; }
mkdir -p $W/tools/hbm_die_v15/v16_relays
if [ $LAND = 1 ]; then
  bash tools/hbm_die_v16/d4g_land_step.sh $A $A/stations_gen2_lanes.json - $A/gen2a_manifest.json $A/root_sites_d4g2.json \
    $A/net/pre_relay.json.gz $D/landing/land_plan_d4g.json 120 > $A/land_step.log 2>&1; rc=$?; tail -12 $A/land_step.log
  [ $rc = 0 ] || { echo "S5_LAND_STEP_FAIL rc=$rc"; exit 15; }
else
  python3 tools/hbm_die_v16/relay_layer_d4f.py --stations $A/stations_gen2_lanes.json --contract $A/net/pre_relay.json.gz \
    --manifest $A/gen2a_manifest.json --root-sites $A/root_sites_d4g2.json --region-map $D/d4g_region_map.json \
    --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows \
    --out $A/net/relays_d4g2.json.gz --report $A/net/relays_d4g2_report.json > $A/net/layer.log 2>&1 || { echo S5_LAYER_FAIL; tail $A/net/layer.log; exit 15; }
  bash tools/hbm_die_v16/run_relay_lockstep.sh $A/net/relays_d4g2.json.gz $A/lockstep 120 > $A/lockstep.log 2>&1; echo "LOCKSTEP rc=$?"; tail -4 $A/lockstep.log
  python3 tools/hbm_die_v16/d4g_relay_splice.py $A/net/pre_relay.json.gz $A/net/relays_d4g2.json.gz $A/net/contract.json --report $A/net/splice.json \
    > $A/net/splice.log 2>&1; tail -4 $A/net/splice.log; grep -q "RELAY_SPLICE PASS" $A/net/splice.log || { echo S5_SPLICE_FAIL; exit 15; }
  mkdir -p $A/pb; bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $A/net/contract.json $A/pb > /dev/null; tail -1 $A/pb/port_bind.log
  grep -q "^DIE_PORT_BIND PASS" $A/pb/port_bind.log || { echo S5_BIND_FAIL; grep '^FAIL' $A/pb/port_bind.log | head; exit 15; }
fi
python3 tools/hbm_die_v15/check_contract_modules.py --contract $A/net/contract.json --rev HEAD --json $A/pb/contract_modules_check.json > $A/pb/cmc.log 2>&1; tail -1 $A/pb/cmc.log
step S6 views_synth_final
synth_round $A/net/contract.json $A/vplan b || exit $?
python3 tools/hbm_die_v16/d4g_bindings.py --views $A/vplan/views.json --grants $D/grants_d4g.json --out $A/view_bindings.json
step S7 gen2
views_up $A/vplan $A/net/contract.json || exit 17
$OTRUN --mem 64 --threads 2 --hosts ot-epyc4 --priority die --dir $B -- env OT_ABS_PIN_WINDOW_UM=3 OT_GEN2_CASE=case bash $B/gen_d4g2.sh \
  > $A/gen.otrun 2>&1; echo "GEN ot-run rc=$? $(date -Is)"; tail -20 $A/gen.otrun
grep -q GEN_OK $A/gen.otrun || exit 17
scp -q ot-epyc4:$B/overreach.json ot-epyc4:$B/case/layout.png $A/ 2>/dev/null
ssh ot-epyc4 "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label','flags')}, default=str)[:20000])\"" > $A/gen_manifest_summary.json
step S8 grt2
$OTRUN --mem 160 --threads 16 --hosts ot-epyc4 --priority die --dir $B/case -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh ot-epyc4 "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log" > $A/grt_summary.txt 2>&1
cat $A/grt_summary.txt
echo CHAIN_D4G2_DONE LAND=$LAND
