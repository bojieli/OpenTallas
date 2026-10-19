#!/usr/bin/env python3
"""Finite read-only reconciliation. No solver, RTL generation or native tools."""
import collections, gzip, hashlib, json, math, pathlib, re, subprocess
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'results/arch/qwen_cluster_1017/q_cluster16/'
SOURCE_REV = 'c672ee40ff58ad02d870ee3a540a4dadd9be16f7'
def blob(rev, path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', rev+':'+path])
def load(rev, path):
    return json.loads(blob(rev, path))
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
raw = blob('16f76334c', BASE+'pickup2/pre_stop.json')
incumbent = json.loads(next(s for row in json.loads(raw) for s in row['outputs'].values()))
plan_path = BASE+'safe_graph_model/safe_endpoint_plan_actual_master.json'
plan = json.loads((ROOT/plan_path).read_text())
place = {v['inst']:v for v in incumbent['placement']}
pins = {}; final_nonpayload_changes = {}; inputs = {plan_path:digest((ROOT/plan_path).read_bytes()),
                     '16f76334c:'+BASE+'pickup2/pre_stop.json':digest(raw)}
for master, asset in plan['native_pin_assets'].items():
    raw = (ROOT/asset['path']).read_bytes()
    assert digest(raw) == asset['sha256']
    pins[master] = json.loads(raw)['pins']; inputs[asset['path']] = digest(raw)
    if '_narrow' in master:
        final = load('16f76334c', BASE+'pickup2/'+master+'_final_pins.json')
        changed=[]
        for name, pin in final['pins'].items():
            if [r[1] for r in pins[master].get(name,{}).get('rectangles',[])] != pin['rectangles']:
                assert not name.startswith(('bank_', 'vld[', 'i[', 'o[')), name
                changed.append(name)
        final_nonpayload_changes[master]=changed

def endpoint(ep, bit):
    master = ep.get('master'); name = ep['port']+f'[{bit}]'
    region = place.get(ep['inst'], {}).get('region')
    result = dict(inst=ep['inst'], master=master, pin=name,
                  logical_region=region, native_clock_root=None, native_clock_phase_ps=None,
                  mapped_publication_or_capture_ff=None, parent_reset_epoch=None,
                  native_transparent_fanout=None)
    if master not in pins:
        result['qualification'] = 'UNQUALIFIED_A0_OR_BOUNDARY'; return result
    pin = pins[master][name]; assert len(pin['centers_um']) == 1
    result['direction'] = pin['direction']
    result['native_local_center_um'] = pin['centers_um'][0]
    result['candidate_R0_center_um'] = [round(a+b, 6) for a,b in
        zip(place[ep['inst']]['at'], pin['centers_um'][0])]
    result['qualification'] = 'PIN_GEOMETRY_ONLY_NO_PARENT_ORIENTATION_OR_CLOCK_PROOF'
    return result

summary = []; count = collections.Counter(); records = []; debt = collections.Counter()
for number, bus in enumerate(plan['bindings']):
    lo = [ep.get('range', [0,bus['bits']-1])[0] for ep in (bus['src'], bus['dst'])]
    known = 0; maximum = 0.; failing = 0
    for offset in range(bus['bits']):
        eps = [endpoint(ep, start+offset) for ep,start in zip((bus['src'],bus['dst']),lo)]
        distance = None
        if all('candidate_R0_center_um' in ep for ep in eps):
            assert eps[0]['direction']=='OUTPUT' and eps[1]['direction']=='INPUT'
            distance = round(sum(abs(a-b) for a,b in zip(eps[0]['candidate_R0_center_um'],eps[1]['candidate_R0_center_um'])),6)
            known += 1; maximum=max(maximum,distance); failing += distance>405.000001
        # Slot interleaving is explicit, not a full-record width on each half.
        logical_bit = bus.get('logical_range',[None])[0]
        if logical_bit is not None: logical_bit += offset
        if 'logical_segments' in bus:
            logical_bit = next(s['logical'][0]+offset-s['physical'][0]
                for s in bus['logical_segments'] if s['physical'][0]<=offset<=s['physical'][1])
        records.append(dict(binding=number,net=bus['net'],kind=bus['kind'],logical_bit=logical_bit,
                            physical_port_bit=offset,src=eps[0],dst=eps[1],
                            candidate_R0_manhattan_um=distance,obstacle_avoiding_route_um=None,
                            first_use_epoch=None, compiler_delta=None))
    count[bus['kind']+'_bits'] += bus['bits']; count['known_bits'] += known
    count['unqualified_bits'] += bus['bits']-known; count['over405_known_bits'] += failing
    if known:
        region_class='same_region' if place[bus['src']['inst']]['region']==place[bus['dst']['inst']]['region'] else 'cross_region'
        debt[(region_class,bus['kind'],'bits')]+=failing
        debt[(region_class,bus['kind'],'buses')]+=bool(failing)
    summary.append(dict(binding=number,net=bus['net'],kind=bus['kind'],bits=bus['bits'],
                        src=bus['src'],dst=bus['dst'],known_bits=known,over405_bits=failing,
                        max_R0_manhattan_um=maximum if known else None))
# Group halves/faces/flags back into complete source records before costing.
groups={}
for b in summary:
    logical=lambda ep:place.get(ep['inst'],{}).get('logical',ep['inst']+'/'+ep['port'])
    net=re.sub(r'_written_p[01]$','',b['net'])
    key=(net,logical(b['src']),logical(b['dst']))
    g=groups.setdefault(key,dict(net=net,src=key[1],dst=key[2],bindings=[],
        bits=0,known_bits=0,max_pin_distance_um=0.,kind='coherent_landing_bank' if b['kind']!='ordinary_data' else 'forward_record'))
    g['bindings'].append(b['binding']);g['bits']+=b['bits'];g['known_bits']+=b['known_bits']
    g['max_pin_distance_um']=max(g['max_pin_distance_um'],b['max_R0_manhattan_um'] or 0.)
for g in groups.values():
    complete=g['bits']==g['known_bits']
    n=max(1,math.ceil(g['max_pin_distance_um']/405)) if complete else None
    g.update(segment_lower_bound=n,intermediate_capture_lower_bound=n-1 if n else None,
        complete_record_capture_state_bit_lower_bound=(n-1)*g['bits'] if n else None,
        reset_landing_ff_floor=2*(n-1) if n else None,
        additional_control_epoch_ff=None,native_root_and_phase=None,legal_sites=None,
        clock_buffer_count=None,area_um2=None,PG_reservation_um2=None,first_use=None,
        compiler_SU_delta=None,compiler_MU_delta=None,
        reservation='LOWER_BOUND_ONLY: full record moves together; no interpolation sites or root qualification')
    if g['kind']=='coherent_landing_bank':
        W=(g['bits']-88)//4;assert 4*W+88==g['bits'] and W in (514,516)
        g['existing_landing_state']=dict(record_bits=W,ring_data=4*W,registered_output=W,
            source_written_flags=88,writer_reader_select=176,reset_capture=48,
            reader_warm=22,reader_age=44,total_ff=5*W+378,clock_pins=4)
        g['extra_capture_full_record_over_2kb']=g['bits']>2048
violations=collections.Counter(); stages=collections.Counter(); families=collections.Counter()
for v in incumbent['reach_violations']:
    e=v['edge']; cls='unqualified_boundary' if 'unqualified' in e['reach_basis'] else (
        'same_region' if e['src_region']==e['dst_region'] else 'cross_region')
    violations[cls]+=1; stages[cls]+=math.ceil((405+v['overrun_um'])/405)-1
    families[(cls,e['kind'])]+=1
source_inputs={}
for path in ['rtl/physical/qcluster/qfd_c_b16_dv_fabric.sv',
             'rtl/physical/qcluster/qfd_c_land_safe.sv','tools/qwen_cluster/qc_safe_graph.py']:
    current=(ROOT/path).read_bytes();assert current==blob(SOURCE_REV,path)
    old=subprocess.run(['git','-C',str(ROOT),'show','ac8e4c483:'+path],capture_output=True)
    historical=old.stdout if old.returncode==0 else None
    source_inputs[path]=dict(current_sha256=digest(current),
        ac8e4c483_sha256=digest(historical) if historical is not None else None,
        current_equals_historical=current==historical,
        source_revision=SOURCE_REV)
gen=load('eb0ee1e0b','results/arch/qwen_gen2_integration_1019/land_owed_rA.json')
genlinks=gen if isinstance(gen,list) else gen.get('links',gen.get('owed',[]))
out=dict(schema='opentallas.cb16.parent_contract.v1',model_only=True,release_ready=False,
         candidate_source='ac8e4c483 standalone diagnostic; no selected successor GEN source',
         parent_orientation='R0 assumption in diagnostic packing; not an adopted DEF',
         inputs=inputs,source_inputs=source_inputs,physical_children=len(place),
         final_nonpayload_rectangles_changed=final_nonpayload_changes,
         packed_bindings=len(summary),counts=dict(count),incumbent_edges=len(incumbent['edges']),
         packed_reach_debt=[dict(region=k[0],kind=k[1],unit=k[2],count=v)for k,v in debt.items()],
         incumbent_violations=dict(violations),distance_only_intermediate_stages=dict(stages),
         violation_families=[dict(classification=k[0],kind=k[1],edges=v)for k,v in families.items()],
         incumbent_overrun_um=incumbent['total_overrun_um'],
         full_native_phase_reset_firstuse_census_qualified=False,
         frozen_GEN_cb16=dict(source='0d4c9808f/dv2f18dh2',links=264,payload_bits=136080,
           equivalence_to_standalone=False,reason='different hierarchy and inter-macro logical links, not internal half-port pin routes'),
         half_ABI={str(h):dict(data_input_or_output=h,bank_data=4*h,written_flags=44,
            clock=1,reset=1,ring_slots=4,K=2,slices=11,
            writer_ff=4*h+100,reader_ff=h+89,
            coherent_full_record_bits=2*h,
            full_record_slot_state=8*h,
            independent_lane_proof=False)for h in (257,258)})
(HERE/'contract.json').write_text(json.dumps(out,indent=2)+'\n')
(HERE/'bindings.json').write_text(json.dumps(summary,indent=1)+'\n')
(HERE/'complete_record_lower_bounds.json').write_text(json.dumps(list(groups.values()),indent=1)+'\n')
with gzip.GzipFile(filename=str(HERE/'per_bit.jsonl.gz'),mode='wb',mtime=0) as f:
    for record in records: f.write((json.dumps(record,separators=(',',':'))+'\n').encode())
assert len(summary)==735 and count['known_bits']==226534
assert dict(violations)==dict(unqualified_boundary=55,same_region=136,cross_region=19)
assert count['bank_data_bits']==111120 and count['written_flags_bits']==4752
print(json.dumps(dict(bindings=len(summary),counts=dict(count),violations=dict(violations))))
