#!/bin/bash
# H-D4G3b chain GEN1 (local driver, fleet for every heavy step):
# S0 wait GEN0 GEN_OK (chain_d4g0c) -> S1 pins + stations on the GEN0 case (E4) -> S2 lanes + 136-b relay layer on the GEN1
# pre-relay contract (d4g layers l1-l3) + relay lockstep (fleet Verilator) -> S3 splice + die.v + strict/declared recursive
# bind -> S4 views + synth reuse vs GEN0 -> S5 fleet src tree -> S6 SYNTH new cells -> S7 GEN1 (reset-reach gate FAIL mode)
# -> S8 GRT1 with die repeaters + neighbour-skew gate.  STEP lines; fail = exit code.
set -o pipefail
W=/home/ubuntu/wt/hd4g; A=/home/ubuntu/artifacts/hdie-d4/d4g_gen1; A0=/home/ubuntu/artifacts/hdie-d4/d4g_gen0
B=/srv/opentallas-scratch/claude/hd4g/gen1; B0=/srv/opentallas-scratch/claude/hd4g/gen0; OTRUN=/home/ubuntu/bin/ot-run
D=results/arch/hbm_die_d4g
step() { echo "STEP $* $(date -Is)"; }
[ "$(git -C $W rev-parse --show-toplevel)" = "$W" ] || { echo BAD_WT; exit 9; }
H=$(git -C $W rev-parse --short=9 HEAD); echo "HEAD $H"
ssh ot-epyc4 "mkdir -p $B"
step S0 wait_gen0_gen
until grep -q "^GEN ot-run rc=" $A0/chain_d4g0c.log 2>/dev/null; do
  pgrep -f chain_d4g0c.sh >/dev/null || { echo GEN0_CHAIN_STOPPED_BEFORE_GEN; tail -5 $A0/chain_d4g0c.log; exit 10; }
  sleep 300
done
grep -q GEN_OK $A0/gen.otrun || { echo GEN0_GEN_FAIL; tail -8 $A0/gen.otrun; exit 10; }
step S1 pins_stations
scp -q ot-epyc4:$B0/case/manifest.json $A/gen0_manifest.json || exit 11
cd $W && python3 tools/hbm_die_v16/d4g_root_sites.py --region-map $D/d4g_region_map.json --manifest $A/gen0_manifest.json --out $A/root_sites_d4g.json || exit 11
scp -q $W/tools/hbm_die_v16/case_pin_centroids.py ot-epyc4:$B0/src/tools/hbm_die_v16/ && scp -q $A/root_sites_d4g.json ot-epyc4:$B/ || exit 11
$OTRUN --mem 8 --threads 1 --hosts ot-epyc4 --dir $B0/src -- env PYTHONDONTWRITEBYTECODE=1 python3 tools/hbm_die_v16/case_pin_centroids.py \
  $B0/case --out $B/pins_gen0.json.gz > $A/pins.otrun 2>&1 || { echo S1_PINS_FAIL; tail -4 $A/pins.otrun; exit 11; }
$OTRUN --mem 32 --threads 16 --hosts ot-epyc4 --priority die --dir $B0/src -- env PYTHONDONTWRITEBYTECODE=1 python3 tools/hbm_die_v15/die_relay_stations.py \
  $B0/case --contract $B0/views/contract.json --reach 405 --route-grid 10 --jobs 16 --root-keepouts $B/root_sites_d4g.json \
  --out $B/stations_gen0_405.json > $A/stations.otrun 2>&1 || { echo S1_STATIONS_FAIL; tail -8 $A/stations.otrun; exit 11; }
scp -q ot-epyc4:$B/pins_gen0.json.gz ot-epyc4:$B/stations_gen0_405.json $A/ || exit 11
step S2 layers_lanes_relays
mkdir -p $A/net; cd $W
python3 tools/hbm_die_v16/d4g_layers/run_layers.py $D/gen0/contract.json.gz $A/net/pre_relay.json.gz --report-dir $A/net > $A/net/layers.log 2>&1 \
  || { echo S2_LAYERS_FAIL; tail $A/net/layers.log; exit 12; }
tail -5 $A/net/layers.log
python3 tools/hbm_die_v16/relay_lanes_d4f.py --stations $A/stations_gen0_405.json --pins $A/pins_gen0.json.gz \
  --contract $A/net/pre_relay.json.gz --manifest $A/gen0_manifest.json --root-keepouts $A/root_sites_d4g.json \
  --jobs 12 --out $A/stations_gen1_lanes.json --report $A/lanes_report.json > $A/lanes.log 2>&1 || { echo S2_LANES_FAIL; tail $A/lanes.log; exit 12; }
mkdir -p $W/tools/hbm_die_v15/v16_relays
python3 tools/hbm_die_v16/relay_layer_d4f.py --stations $A/stations_gen1_lanes.json --contract $A/net/pre_relay.json.gz \
  --manifest $A/gen0_manifest.json --root-sites $A/root_sites_d4g.json --region-map $D/d4g_region_map.json \
  --exclude-re '^(rfr|sfr)_' --fork-lane-width 136 --lane-rows \
  --out $A/net/relays_d4g1.json.gz --report $A/net/relays_d4g1_report.json > $A/net/layer.log 2>&1 || { echo S2_LAYER_FAIL; tail $A/net/layer.log; exit 12; }
python3 -c "
import json; r=json.load(open('$A/net/relays_d4g1_report.json'))
for k in ('buses','tile_categories','fork_buses','inter_region_buses','equal_age_max_depth_by_domain'): print(k, r.get(k))
print('hops_over', len(r['hops_over_reach'])); print('problems', len(r['problems'])); [print('PROBLEM', p) for p in r['problems'][:20]]"
bash tools/hbm_die_v16/run_relay_lockstep.sh $A/net/relays_d4g1.json.gz $A/lockstep 120 > $A/lockstep.log 2>&1; echo "LOCKSTEP rc=$?"; tail -4 $A/lockstep.log
step S3 splice_bind
python3 tools/hbm_die_v16/d4g_relay_splice.py $A/net/pre_relay.json.gz $A/net/relays_d4g1.json.gz $A/net/contract.json --report $A/net/splice.json \
  > $A/net/splice.log 2>&1; tail -6 $A/net/splice.log; grep -q "RELAY_SPLICE PASS" $A/net/splice.log || { echo S3_SPLICE_FAIL; exit 13; }
mkdir -p $A/pb
python3 tools/hbm_die_v15/check_contract_modules.py --contract $A/net/contract.json --rev HEAD --json $A/pb/contract_modules_check.json > $A/pb/cmc.log 2>&1; tail -1 $A/pb/cmc.log
# strict recursive bind (child closure, declared identity straps only, GEN0 pad sidecar); the ONLY allowed failures are the
# documented gap G-D4G-L3-IDXQ-SE/NE (IDX quad client not landed: SEb/NEb glue cq, q0 bank rq4) -- never a tie or stub.
bash tools/hbm_die_v16/d4g_layers/l1_bind_check.sh $A/net/contract.json $A/pb; tail -1 $A/pb/port_bind.log
python3 - <<PY || { echo S3_BIND_FAIL; exit 13; }
import json, re, sys
L = open('$A/pb/port_bind.log').read().splitlines()
summ = [l for l in L if l.startswith('DIE_PORT_BIND')][-1]
cnt = dict(re.findall(r'(\w+)=(\d+)', summ))
bad = {k: v for k, v in cnt.items() if k not in ('masters', 'instances', 'strap_ports', 'pad_bits', 'input_unconnected') and int(v)}
ALLOW = {('hfd_hgi_vms_static_SEb_glue', 'cq'), ('hfd_hgi_vms_static_NEb_glue', 'cq'), ('hfd_vms_bank_native_q0_faces', 'rq4')}
fails = [l for l in L if l.startswith('FAIL ')]
other = [l for l in fails if not any(l.split()[1] == m and ('in_unconn=' + p) in l for m, p in ALLOW)]
print('BIND_GATE', 'counts_bad', bad, 'fails', len(fails), 'outside_gap_allowlist', len(other)); [print(' ', l) for l in other[:10]]
sys.exit(1 if bad or other else 0)
PY
step S4 views
rm -rf $A/vplan; python3 tools/hbm_die_v15/v16_views.py --out $A/vplan --contract $A/net/contract.json | tail -4
python3 tools/hbm_die_v16/d4g_bindings.py --views $A/vplan/views.json --grants $D/grants_d4g.json --out $A/view_bindings.json
rm -rf $A/synmeta; mkdir -p $A/synmeta; (cd $A0/vplan/synth && tar -cf - */meta.json) | tar -x -C $A/synmeta
python3 tools/hbm_die_v16/synth_reuse_r8b.py --views $A/vplan --metas $A/synmeta --root $W --out $A/reuse.json --prev $A0/vplan > $A/reuse.log; tail -3 $A/reuse.log | cut -c1-600
CELLS=$(grep '^SYNTH ' $A/reuse.log | cut -d' ' -f2-)
step S5 trees
python3 - > $A/src_paths.txt <<PY
import json
V=json.load(open('$A/vplan/views.json'))
p={'rtl','tools','physical/asap7_memory_macros','physical/asap7_memory_macros_v2','physical/asap7_v41x_pdie_macros','physical/hbm_xp_aq_tree13_1014',
   'physical/hbm_mtp/rtl','physical/hbm_accel_die_views','physical/hbm_generic/argmax18/rtl',
   'physical/ref_tile/hdie_pc_ctrl/floorplan.json','results/arch/hbm_die_d4g','results/arch/die_reach_1016.json','results/arch/hbm_die_v15/compact660_v5',
   'results/arch/hbm_die_v15/source_contract','results/arch/hbm_die_v16','results/arch/hier_contract_1015','results/arch/die_clock_method_1016'}
p|={v['view_dir'] for v in V.values() if v.get('view_dir')}
print('\n'.join(sorted(p)))
PY
ssh ot-epyc4 "rm -rf $B/src_$H" || exit 15
git -C $W archive HEAD $(cat $A/src_paths.txt) | ssh ot-epyc4 "mkdir -p $B/src_$H && tar -x -C $B/src_$H && ln -sfn $B/src_$H $B/src" || exit 15
tar -C $A/vplan/wrap -cf - . | ssh ot-epyc4 "mkdir -p $B/src_$H/v16w && tar -x -C $B/src_$H/v16w" || exit 15
for h in ot-agidock128 ot-pve1; do ssh ot-epyc4 "tar -C $B -cf - src_$H" | ssh $h "mkdir -p $B && rm -rf $B/src_$H && tar -x -C $B && ln -sfn $B/src_$H $B/src && echo $h ok"; done
step S6 synth "$CELLS"
if [ -n "${CELLS// /}" ]; then
  cd /tmp && python3 $W/tools/hbm_die_v15/v16_synth_drive.py --views $A/vplan --commit $H --remote-root $B $CELLS > $A/drive.log 2>&1
  tail -2 $A/drive.log
  python3 $W/tools/hbm_die_v15/v16_fetch.py --views $A/vplan --remote-root $B --commit $H --contract $A/net/contract.json $CELLS > $A/fetch.log 2>&1; echo "FETCH rc=$?"; tail -3 $A/fetch.log
  MISS=""; for c in $CELLS; do [ -f $A/vplan/synth/$c/meta.json ] || MISS="$MISS $c"; done
  [ -n "$MISS" ] && { echo "SYNTH_MISSING$MISS (no stubs: GEN1 needs every SYNTH view)"; exit 16; }
fi
step S7 gen1
ssh ot-epyc4 "rm -rf $B/views && mkdir -p $B/views/synth" || exit 17
rsync -a $A0/vplan/synth/ ot-epyc4:$B/views/synth/ && [ -d $A/vplan/synth ] && rsync -a $A/vplan/synth/ ot-epyc4:$B/views/synth/
scp -q $A/vplan/views.json ot-epyc4:$B/views/ && scp -q $A/net/contract.json ot-epyc4:$B/views/contract.json && scp -q $A/gen_d4g1.sh ot-epyc4:$B/gen_d4g1.sh || exit 17
$OTRUN --mem 64 --threads 2 --hosts ot-epyc4 --priority die --dir $B -- bash $B/gen_d4g1.sh > $A/gen.otrun 2>&1; echo "GEN ot-run rc=$? $(date -Is)"; tail -20 $A/gen.otrun
grep -q GEN_OK $A/gen.otrun || exit 17
scp -q ot-epyc4:$B/overreach.json ot-epyc4:$B/case/layout.png $A/ 2>/dev/null
ssh ot-epyc4 "python3 -c \"
import json; m=json.load(open('$B/case/manifest.json'))
print(json.dumps({k: m.get(k) for k in ('reset_reach_gate','clock_regions','placement_problems','pin_density_over','die_repeaters','label')}, default=str)[:20000])\"" > $A/gen_manifest_summary.json
step S8 grt1
$OTRUN --mem 160 --threads 16 --hosts ot-epyc4 --priority die --dir $B/case -- env CPUS=16 MEMG=160 bash $B/case/run.sh > $A/grt.otrun 2>&1; echo "GRT ot-run rc=$? $(date -Is)"
ssh ot-epyc4 "cat $B/case/out/run.exit; grep -E 'OT_DIE_REP|overflow|Total wire|tns|wns' $B/case/out/run.log | tail -15; cat $B/case/out/neighbour_skew_gate.log" > $A/grt_summary.txt 2>&1
cat $A/grt_summary.txt
echo CHAIN_D4G1_DONE
