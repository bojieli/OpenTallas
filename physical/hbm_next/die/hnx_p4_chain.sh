#!/bin/bash
# HBM-NEXT-DIE 10-19 DIE-P4-1: stations at 405 + LANDING/relay layer + GEN + die GRT (+TT/FF clock gate) on the P = 4 plan
# f4c_t5 with stand-ins, in the GEN2 S4..S8 form (results/arch/hbm_die_d4g/gen2/chain_d4g2*.sh + tools/hbm_die_v16/d4g_land_step.sh,
# forked by copy; no GEN2 file edited).  Every python / sim / GEN / GRT step runs on the fleet case host (data locality) via
# ot-run at NORMAL priority; outputs are hnx_* under the case dir only; the case src tree is a hardlink copy of GEN2's, so
# this chain only ever ADDS files there (never edits in place).
#   local driver:  nohup bash hnx_p4_chain.sh > $A/chain.log 2>&1 &
set -o pipefail
TAG=${TAG:-f4c_t5}; B=/srv/opentallas-scratch/claude/hnx/die_p4; S=$B/src; CA=$B/case_$TAG; PRE=$B/views/contract.json
A=${A:-/home/ubuntu/artifacts/hnx/die_p4}; W=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd); OTRUN=/home/ubuntu/bin/ot-run; H=ot-epyc4
export A W OT_RUN_PRIO_ENV="" # HBM-NEXT always normal priority, including auto-detected die commands
RM=physical/hbm_next/die/$TAG/region_map_hnx_$TAG.json; LP=results/arch/hbm_die_d4g/landing/land_plan_d4g.json
G2V=/srv/opentallas-scratch/claude/hd4g/gen2/views/synth      # GEN2 synth views (incl. hbfd_lh0_* / hbfd_land0_* masters)
step() { echo "STEP $* $(date -Is)"; }
otr() { local m=$1 t=$2; shift 2; $OTRUN --mem $m --threads $t --dir $S -- env PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg "$@"; }
mkdir -p $A; ssh $H "mkdir -p $B/net" || exit 9
scp -q $W/physical/hbm_next/die/hnx_case_relay.sh $H:$B/ || exit 9
if [ "${FROM:-S4}" = S4 ]; then
step S4 root_sites_pins_stations
otr 8 1 python3 tools/hbm_die_v16/d4g_root_sites.py --region-map $RM --manifest $CA/manifest.json --out $B/hnx_root_sites.json > $A/root_sites.otrun 2>&1 || { echo S4_ROOT_FAIL; tail $A/root_sites.otrun; exit 14; }
otr 8 1 python3 tools/hbm_die_v16/case_pin_centroids.py $CA --out $B/hnx_pins.json.gz > $A/pins.otrun 2>&1 || { echo S4_PINS_FAIL; tail $A/pins.otrun; exit 14; }
otr 32 16 python3 tools/hbm_die_v15/die_relay_stations.py $CA --contract $PRE --reach 405 --route-grid 10 --jobs 16 \
  --root-keepouts $B/hnx_root_sites.json --out $B/hnx_stations_405.json > $A/stations.otrun 2>&1 || { echo S4_STATIONS_FAIL; tail -8 $A/stations.otrun; exit 14; }
tail -4 $A/stations.otrun
fi
if [ "${FROM:-S4}" = S4 ] || [ "$FROM" = S5 ]; then
step S5 lanes_landing_layer
otr 32 12 python3 tools/hbm_die_v16/relay_lanes_d4f.py --stations $B/hnx_stations_405.json --pins $B/hnx_pins.json.gz --contract $PRE \
  --manifest $CA/manifest.json --root-keepouts $B/hnx_root_sites.json --jobs 12 --out $B/hnx_stations_lanes.json --report $B/hnx_lanes_report.json \
  > $A/lanes.otrun 2>&1 || { echo S5_LANES_FAIL; tail $A/lanes.otrun; exit 15; }
otr 32 1 python3 tools/hbm_die_v16/relay_layer_d4f.py --stations $B/hnx_stations_lanes.json --contract $PRE --manifest $CA/manifest.json \
  --root-sites $B/hnx_root_sites.json --region-map $RM --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows --land --land-plan $LP \
  --out $B/net/hnx_relays_land.json.gz --report $B/net/hnx_relays_land_report.json > $A/layer_land.otrun 2>&1 || { echo S5_LAYER_FAIL; tail $A/layer_land.otrun; exit 12; }
ssh $H "python3 -c \"
import json; r=json.load(open('$B/net/hnx_relays_land_report.json'))
for k in ('buses','tile_categories','fork_buses','inter_region_buses'): print(k, r.get(k))
l=r['landing']; print('LANDINGS links', l['links'], 'tiles', l['landing_tiles'], 'by_width', l['by_width'], 'NO_E', l['no_E'], 'fault', l['fault'])
print('hops_over', len(r['hops_over_reach'])); print('problems', len(r['problems'])); [print('PROBLEM', p) for p in r['problems'][:20]]\"" | tee $A/layer_land_summary.txt
otr 48 1 python3 tools/hbm_die_v16/d4g_relay_splice.py $PRE $B/net/hnx_relays_land.json.gz $B/net/hnx_contract.json --report $B/net/hnx_splice.json \
  > $A/splice.otrun 2>&1; tail -3 $A/splice.otrun; grep -q "RELAY_SPLICE PASS" $A/splice.otrun || { echo S5_SPLICE_FAIL; exit 13; }
otr 48 1 bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $B/net/hnx_contract.json $B/net/hnx_pb > $A/bind.otrun 2>&1; tail -2 $A/bind.otrun
ssh $H "tail -1 $B/net/hnx_pb/port_bind.log" | tee $A/port_bind_tail.txt; grep -q "^DIE_PORT_BIND PASS" $A/port_bind_tail.txt || { echo S5_BIND_FAIL; exit 13; }
step S5L lockstep
bash $W/tools/hbm_next/die/hnx_relay_lockstep.sh $S $B/net/hnx_relays_land.json.gz $B/hnx_lockstep $A/lockstep 120 > $A/lockstep.log 2>&1; rc=$?
tail -7 $A/lockstep.log; [ $rc = 0 ] || echo "S5_LOCKSTEP_FAIL (recorded; chain continues to GEN/GRT for the physical evidence)"
fi
step S6 views
otr 16 1 python3 tools/hbm_die_v15/v16_views.py --out $B/hnx_vplan --contract $B/net/hnx_contract.json > $A/views.otrun 2>&1; tail -3 $A/views.otrun
views_merge() {
ssh $H "rm -rf $B/views_land && mkdir -p $B/views_land/synth && cp -al $G2V/. $B/views_land/synth/ 2>/dev/null; cp -al $B/views/synth/. $B/views_land/synth/ 2>/dev/null; \
  [ -d $B/hnx_vplan/synth ] && cp -al $B/hnx_vplan/synth/. $B/views_land/synth/ 2>/dev/null; cp $B/hnx_vplan/views.json $B/views_land/ && cp $B/net/hnx_contract.json $B/views_land/contract.json && \
  python3 -c \"
import json,os; V=json.load(open('$B/views_land/views.json')); miss=[c for c,v in V.items() if v.get('kind','').startswith('SYNTH') and not os.path.exists('$B/views_land/synth/'+c+'/meta.json')]
print('VIEWS', len(V), 'SYNTH_MISSING', len(miss), ' '.join(miss))\"" | tee $A/views_check.txt
}
views_merge
# S6 structural fix (P3-DIE 10-19): the relay/landing layer of a new frame instantiates landing / lane-hop masters (hbfd_land0_*,
# hbfd_lh0_*_f2, hbfd_lh_*_f4, ...) that neither GEN2's views nor an earlier hnx run synthesised.  The missing list is DERIVED
# from this run's view plan (not a hand list): pull the plan rows + wrappers, add the wrappers to the case src (add-only),
# synth exactly those masters (hnx_s6_synth.sh: GEN2 synth_master/etm form, normal priority, LIBCELLS=1 for lh0/land0),
# fetch (source bytes checked), upload, and merge again.  No stubs: the chain still stops if any master stays missing.
if ! grep -q "SYNTH_MISSING 0" $A/views_check.txt; then
  MISS=$(sed -n 's/.*SYNTH_MISSING [0-9]* //p' $A/views_check.txt)
  step S6S auto_synth $MISS
  V=$A/vplan_s6; mkdir -p $V
  rsync -a $H:$B/hnx_vplan/jobs.tsv $H:$B/hnx_vplan/views.json $V/ && rsync -a $H:$B/hnx_vplan/wrap/ $V/wrap/ && scp -q $H:$B/net/hnx_contract.json $V/hnx_contract.json || { echo S6S_PULL_FAIL; exit 16; }
  NOCHAIN=1 bash $W/tools/hbm_next/die/hnx_s6_synth.sh $MISS || { echo S6S_FAIL; exit 16; }
  views_merge
fi
grep -q "SYNTH_MISSING 0" $A/views_check.txt || { echo S6_SYNTH_MISSING; exit 16; }
step S7 gen
$OTRUN --mem 64 --threads 2 --dir $B -- bash $B/hnx_case_relay.sh $TAG $B/views_land hnx_case_${TAG}_land > $A/gen.otrun 2>&1; echo "GEN rc=$? $(date -Is)"; tail -22 $A/gen.otrun
grep -q GEN_OK $A/gen.otrun || exit 17
scp -q $H:$B/hnx_case_${TAG}_land/layout.png $A/hnx_case_${TAG}_land_layout.png
step S8 grt
$OTRUN --mem 160 --threads 16 --dir $B/hnx_case_${TAG}_land -- env OT_ABS_PIN_WINDOW_UM=3 CPUS=16 MEMG=160 bash $B/hnx_case_${TAG}_land/run.sh > $A/grt.otrun 2>&1; echo "GRT rc=$? $(date -Is)"
ssh $H "cd $B/hnx_case_${TAG}_land/out; cat run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' run.log | tail -15; cat neighbour_skew_gate.log; tail -5 hold_budget.log" > $A/grt_summary.txt 2>&1
cat $A/grt_summary.txt
echo HNX_P4_CHAIN_DONE TAG=$TAG
