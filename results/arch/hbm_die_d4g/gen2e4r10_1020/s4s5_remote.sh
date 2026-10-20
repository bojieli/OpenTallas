#!/bin/bash
# HBM-DIE10 10-20 GEN2e4 r10 (= r9 remote S4/S5 script; PORT-AGE layer + reach-first planner come from the source tree)
# HBM-DIE9 10-20 GEN2e4 r9 (channel-cut floorplan + capacity-aware stations), REMOTE S4 + S5 + S5b for one plan.
#   env: B (remote plan root: B/src, B/a/case_a relay-free GEN, B/p/case_p post-landing-pin GEN), H (source label), PD (plan dir in src)
# S4: root sites (cut region map) + pins of the CURRENT views (case_p: r7 post-landing views on the cut floorplan) + routed
#     stations on case_a (bus list on the cut floorplan) + lanes re-plan with the CAPACITY planner (relay_lanes_d4f --capacity).
# S5: relay+landing layer -> l7 precheck -> exact tail classes -> splice -> structural bind -> strict unread manifest.
# S5b: l7_wire post-landing -> bind + functional bind (LAT warn) + contract modules -> strict.
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
: ${B:?} ${H:?} ${PD:?}
A=$B/artifacts; mkdir -p $A/net $A/pb $A/pb5b $A/unread
cd $B/src || exit 9
REV0=$PWD/results/arch/hbm_unread_gen2e3_1019/l21/review_l21_candidate.json
echo "STEP S4 root_sites_pins_stations $(date -Is)"
python3 tools/hbm_die_v16/d4g_root_sites.py --region-map $PD/d4g_region_map.json --manifest $B/a/case_a/manifest.json --out $A/root_sites.json || { echo S4_ROOTS_FAIL; exit 14; }
python3 tools/hbm_die_v16/case_pin_centroids.py $B/p/case_p --out $A/pins_case_p.json.gz || { echo S4_PINS_FAIL; exit 14; }
python3 tools/hbm_die_v16/case_pin_centroids.py $B/a/case_a --out $A/pins_case_a.json.gz || { echo S4_PINS_A_FAIL; exit 14; }
# current pins: case_p (post-landing views) wins; instances absent there (none expected) fall back to case_a
python3 - $A/pins_case_p.json.gz $A/pins_case_a.json.gz $A/pins.json.gz <<'PY' || { echo S4_PINS_MERGE_FAIL; exit 14; }
import gzip, json, sys
p = json.load(gzip.open(sys.argv[1])); a = json.load(gzip.open(sys.argv[2])); n = 0
for k, v in a['instances'].items():
    if k not in p['instances']:
        p['instances'][k] = v; n += 1
p['merged_from_case_a'] = n; json.dump(p, gzip.open(sys.argv[3], 'wt')); print('PINS current=case_p, case_a fallback', n)
PY
python3 tools/hbm_die_v15/die_relay_stations.py $B/a/case_a --contract $B/a/views/contract.json --reach 405 --route-grid 10 --jobs 16 \
  --root-keepouts $A/root_sites.json --out $A/stations_case_a_405.json || { echo S4_STATIONS_FAIL; exit 14; }
python3 tools/hbm_die_v16/relay_lanes_d4f.py --stations $A/stations_case_a_405.json --pins $A/pins.json.gz --contract $B/a/views/contract.json \
  --manifest $B/a/case_a/manifest.json --root-keepouts $A/root_sites.json --jobs 16 --capacity ${OT_CAP_ARGS:-} \
  --out $A/stations_lanes.json --report $A/lanes_report.json > $A/lanes.log 2>&1 || { echo S4_LANES_FAIL; tail $A/lanes.log; exit 14; }
tail -c 1500 $A/lanes.log; echo
touch $B/S4_DONE
echo "STEP S5 layer $(date -Is)"
cp $B/a/views/contract.json $A/net/pre_relay.json
python3 tools/hbm_die_v16/relay_layer_d4f.py --stations $A/stations_lanes.json --contract $A/net/pre_relay.json --manifest $B/a/case_a/manifest.json \
  --root-sites $A/root_sites.json --region-map $PD/d4g_region_map.json --exclude-re "^(rfr|sfr)_" --fork-lane-width 136 --lane-rows --land \
  --land-plan results/arch/hbm_die_d4g/landing/land_plan_d4g.json --out $A/net/relays_d4g_land.json.gz --report $A/net/relays_d4g_land_report.json \
  > $A/net/layer_gen.log 2>&1 || { echo S5_LAYER_GEN_FAIL; tail -5 $A/net/layer_gen.log; exit 15; }
tail -2 $A/net/layer_gen.log | cut -c1-1500
python3 -c "import json;r=json.load(open('$A/net/relays_d4g_land_report.json'));print('HOPS_OVER',len(r['hops_over_reach']),'PORT_AGE_PADS',len(r.get('port_age_pads',[])),'PROBLEMS',len(r['problems']) if isinstance(r['problems'],list) else r['problems'])"
touch $B/S5_LAYER_DONE
python3 tools/hbm_die_v16/d4g_relay_splice.py $A/net/pre_relay.json $A/net/relays_d4g_land.json.gz $A/net/precheck_contract.json --report $A/net/precheck_splice.json > /dev/null \
  && python3 tools/hbm_die_v16/d4g_layers/l7_wire.py $A/net/precheck_contract.json $A/net/precheck_l7.json --report $A/net/precheck_l7.json.rep \
  || { echo S5_PRECHECK_L7_FAIL; cat $A/net/precheck_l7.json.rep; exit 15; }
rm -f $A/net/precheck_contract.json $A/net/precheck_l7.json
python3 tools/hbm_die_v16/exact_tail_layer.py $A/net/relays_d4g_land.json.gz --out $A/net/relays_d4g_land_tail.json.gz \
  --source rtl/hbm_accel/die_glue/hbfd_exact_tail_classes.sv --report $A/net/exact_tail_classes.json --classes --check || { echo S5_TAIL_FAIL; exit 15; }
python3 tools/hbm_die_v16/exact_tail_validate.py $A/net/relays_d4g_land.json.gz $A/net/relays_d4g_land_tail.json.gz \
  tools/hbm_die_v16/exact_tail_baseline_full_die_v16.py > $A/net/tail_validate.log 2>&1; grep EXACT_TAIL_MAP $A/net/tail_validate.log || { echo S5_TAIL_VALIDATE_FAIL; tail -3 $A/net/tail_validate.log; exit 15; }
python3 tools/hbm_die_v16/d4g_relay_splice.py $A/net/pre_relay.json $A/net/relays_d4g_land_tail.json.gz $A/net/contract.json --report $A/net/splice_land.json || { echo S5_SPLICE_FAIL; exit 15; }
cp $A/net/contract.json $A/net/post_landing.json
structural() {  # $1 contract $2 dir $3 tag
  rc=0; bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $1 $2 > /dev/null || rc=$?; tail -1 $2/port_bind.log
  [ $rc = 0 ] && return 0
  python3 - $2/port_bind.json $3 <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1]));print(sys.argv[2]+'_STRUCTURAL_BIND',r.get('failing'),r.get('summary',{}).get('unread_net_bits'))
sys.exit(0 if r.get('failing')==['unread_net_bits'] else 1)
CHECK
}
strict_manifest() {   # $1 contract  $2 bind dir  $3 tag -> transfer -> propose -> replay (as chain_d4g2e4_r5.sh)
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
echo "STEP S5 bind $(date -Is)"
structural $A/net/contract.json $A/pb S5 || { echo S5_BIND_FAIL; exit 15; }
strict_manifest $A/net/contract.json $A/pb S5 || { echo S5_STRICT_FAIL; exit 15; }
python3 tools/hbm_die_v16/d4g_su_lane_profile.py $A/net/post_landing.json --stage post_landing --out $A/su_lane_profile_post_landing.json | head -6
echo "STEP S5b post_l7 $(date -Is)"
python3 tools/hbm_die_v16/d4g_layers/l7_wire.py $A/net/post_landing.json $A/net/contract_l7.json --report $A/net/l7_wire_post.json > $A/net/l7_post.log 2>&1 \
  || { echo S5B_L7_FAIL; tail -3 $A/net/l7_post.log; exit 16; }
cp $A/net/contract_l7.json $A/net/contract_pre.json
structural $A/net/contract_pre.json $A/pb5b S5B || { echo S5B_BIND_FAIL; exit 16; }
python3 tools/hbm_die_v16/d4g_functional_bind.py $A/net/contract_pre.json --report $A/pb5b/functional_bind.json --lat warn > $A/pb5b/functional_bind.log 2>&1
tail -3 $A/pb5b/functional_bind.log; grep -q "^FUNCTIONAL_BIND PASS" $A/pb5b/functional_bind.log || { echo S5B_FUNCTIONAL_FAIL; exit 16; }
python3 tools/hbm_die_v15/check_contract_modules.py --contract $A/net/contract_pre.json --rev HEAD --json $A/pb5b/contract_modules_check.json > $A/pb5b/cmc.log 2>&1; tail -1 $A/pb5b/cmc.log
strict_manifest $A/net/contract_pre.json $A/pb5b S5B || { echo S5B_STRICT_FAIL; exit 16; }
touch $B/S5B_DONE
echo S5B_DONE_R10 $H $(date -Is)
