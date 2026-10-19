#!/bin/bash
# HBM-LANDING 10-18: the LANDING step of the d4g build chain (GEN2+; lanes/LANDING-CONTRACT.md, lanes/HBM-LANDING.md).
# Drop-in for chain_d4g1.sh S2 "relay_layer" + lockstep and S3 "splice + strict bind":
#   relay_layer_d4f.py --land  -> F1 forwarded buses become half-cycle lane stations (hbfd_lh0 / hbfd_lh[_f<N>], in-band
#                                 epoch) ending in a LANDING per sink (hbfd_land_<W>_<dir>, K strap from the land plan),
#                                 equal-age pads after it = plain root-clocked hbfd_rly_<W>_WE; intra/neighbour-region
#                                 buses unchanged (root-clocked hbfd_rly_<W>_<dir>, judged by the TT+FF neighbour check)
#   relay lockstep (fleet Verilator): pos + lane_stage / bitswap / branch_drop / land_k mutants
#   d4g_relay_splice.py -> contract (landing fault -> die status pins, gap G-D4G-LAND-FAULT) -> strict recursive bind
# usage (from the worktree root):
#   d4g_land_step.sh A STATIONS PINS_UNUSED MANIFEST ROOT_SITES PRE_RELAY [LAND_PLAN] [LOCKSTEP_BUSES]
#     A          artifact dir (writes A/net/relays_d4g_land.json.gz, A/net/contract.json, A/pb/, A/lockstep/)
#     STATIONS   relay_lanes_d4f.py output (stations with lane rows + sink pins)
#     MANIFEST   placement manifest of the case the stations were planned on
#     ROOT_SITES d4g_root_sites.py output;  PRE_RELAY = run_layers.py output (GEN pre-relay contract)
#     LAND_PLAN  results/arch/hbm_die_d4g/landing/land_plan_d4g.json (per link E / K, DCC+PRICE); absent -> E 1 placeholders (NO_E)
# exit: 12 layer, 13 splice/bind, 14 lockstep.  Never run two chains on one branch (H-D4G owns the chain).
set -o pipefail
A=$1; ST=$2; MAN=$4; RS=$5; PRE=$6; LP=${7:-}; LB=${8:-120}
D=results/arch/hbm_die_d4g
mkdir -p $A/net $A/pb
LPA=; [ -n "$LP" ] && [ -f "$LP" ] && LPA="--land-plan $LP"
python3 tools/hbm_die_v16/relay_layer_d4f.py --stations $ST --contract $PRE --manifest $MAN --root-sites $RS --region-map $D/d4g_region_map.json \
  --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows --land $LPA \
  --out $A/net/relays_d4g_land.json.gz --report $A/net/relays_d4g_land_report.json > $A/net/layer_land.log 2>&1 || { echo LAND_LAYER_FAIL; tail $A/net/layer_land.log; exit 12; }
python3 -c "
import json; r=json.load(open('$A/net/relays_d4g_land_report.json'))
for k in ('buses','tile_categories','fork_buses','inter_region_buses'): print(k, r.get(k))
l=r['landing']; print('LANDINGS links', l['links'], 'tiles', l['landing_tiles'], 'by_width', l['by_width'], 'NO_E', l['no_E'], 'fault', l['fault'])
print('hops_over', len(r['hops_over_reach'])); print('problems', len(r['problems'])); [print('PROBLEM', p) for p in r['problems'][:20]]"
python3 tools/hbm_die_v16/d4g_relay_splice.py $PRE $A/net/relays_d4g_land.json.gz $A/net/contract.json --report $A/net/splice_land.json \
  > $A/net/splice_land.log 2>&1; tail -3 $A/net/splice_land.log; grep -q "RELAY_SPLICE PASS" $A/net/splice_land.log || { echo LAND_SPLICE_FAIL; exit 13; }
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $A/net/contract.json $A/pb > /dev/null; tail -1 $A/pb/port_bind.log
grep -q "^DIE_PORT_BIND PASS" $A/pb/port_bind.log || { echo LAND_BIND_FAIL; grep '^FAIL' $A/pb/port_bind.log | head; exit 13; }
bash tools/hbm_die_v16/run_relay_lockstep.sh $A/net/relays_d4g_land.json.gz $A/lockstep $LB > $A/lockstep_land.log 2>&1; rc=$?
tail -6 $A/lockstep_land.log; [ $rc = 0 ] || { echo LAND_LOCKSTEP_FAIL; exit 14; }
echo LAND_STEP_DONE
