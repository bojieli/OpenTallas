#!/usr/bin/env python3
"""Finite, read-only extraction; no elaboration or production substitution."""
import collections, difflib, gzip, hashlib, json, pathlib, re
P = pathlib.Path(__file__).resolve().parent
S = P / 'source'
def read(name):
    b = (S / name).read_bytes()
    return (gzip.decompress(b) if name.endswith('.gz') else b).decode()
def out(name, obj):
    (P / name).write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n')
g = read('gen0__die.v.gz')
assert hashlib.sha256(g.encode()).hexdigest() == '7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7'
selected = {}
for instance in ['c16_W5_1', 'dvs_W5', 'tt_ctlm']:
    lines = [l for l in g.splitlines() if re.search(r'\b'+instance+r'\s*\(', l)]
    assert len(lines)==1, (instance,len(lines))
    selected[instance] = {'source_line':lines[0], 'ports':dict(re.findall(r'\.(\w+)\(([^()]*)\)',lines[0]))}
assert selected['c16_W5_1']['ports']['bc0'] == selected['dvs_W5']['ports']['cw_s0']
assert selected['c16_W5_1']['ports']['ck_c0r0']=='n_clk_r1'
assert selected['dvs_W5']['ports']['ck']=='n_clk_r135'
assert selected['tt_ctlm']['ports']['ck']=='n_clk_r54'
out('selected_gen0_binding.json',selected)
(P/'selected_gen0_lines.txt').write_text('\n'.join(v['source_line'] for v in selected.values())+'\n')
hr_routes=[l for l in g.splitlines() if re.search(r'\brly_dvw_hr_wi_\d+\s*\(',l)]
assert hr_routes
(P/'actual_hr_transport.txt').write_text('\n'.join(hr_routes)+'\n')
frozen=read('rtl__hdc__ot_qwen_w12_matvec.sv')
diag=read('diagnostic_semantic_source.sv')
(P/'frozen_vs_diagnostic.diff').write_text(''.join(difflib.unified_diff(frozen.splitlines(True),diag.splitlines(True),fromfile='0d4c/frozen_matvec',tofile='e32/diagnostic_matvec')))
assert 'XTX + ((REGROOT >= 5) ? 1 : 0)' in diag
assert 'XTX + ((REGROOT >= 5) ? 1 : 0)' not in frozen
native=read('private_candidate.v.gz')
assert 'module qfd_tile_nk_regroot5_reset_native' in native
assert 'qfd_tile_nk_regroot5_reset_native' not in g
ports = collections.defaultdict(list)
for direction,name in re.findall(r'^\s*(input|output)\s+\\([^\s;]+)\s*;',native,re.M):
    ports[direction].append(name)
assert ports['input'] and ports['output']
expected_inputs=set(x for x in ports['input'] if x.startswith('ck'))
assert len(expected_inputs)==39
for bus,width in [('tap',508),('tile_id',16),('n_a',514),('n_b',514)]:
    expected_inputs.update(bus+'['+str(i)+']' for i in range(width))
expected_inputs.add('rst_n')
assert expected_inputs==set(ports['input'])
expected_outputs={'tie_hi','tie_lo'}
for bus in ['t_out','n_y']:expected_outputs.update(bus+'['+str(i)+']' for i in range(514))
assert expected_outputs==set(ports['output'])
out('diagnostic_scalar_ports.json',ports)
pack=read('rtl__qwen_dv__qfd_dv_hr_pack.sv')
fields=[]
for hi,lo,chi,clo,name in re.findall(r'assign p\[(\d+):(\d+)\] = cmd\[(\d+):(\d+)\];\s*// (\w+)',pack):
    hi,lo,chi,clo=map(int,(hi,lo,chi,clo))
    fields.append({'name':name,'packed_hr':[hi,lo],'cmd':[chi,clo], 'ib':None if name=='go' else [hi,lo]})
assert sum(x['packed_hr'][0]-x['packed_hr'][1]+1 for x in fields)==380
ib=json.loads(read('all_ib_receivers.json'))
assert len(ib)==141
survivors=[]
for row in ib:
    bit=int(re.search(r'ib_i\\\[(\d+)\\\]',row['cell'])[1])
    field=next(x for x in fields if x['ib'] and x['ib'][1]<=bit<=x['ib'][0])
    survivors.append({'ib_bit':bit,'tap_bit':bit+1,'field':field['name'],'field_bit':bit-field['ib'][1], 'native':row})
assert len({x['ib_bit'] for x in survivors})==141
out('descriptor_fields.json',fields)
out('all_surviving_ib_bindings.json',survivors)
out('surviving_field_counts.json',dict(collections.Counter(x['field'] for x in survivors)))
cross=json.loads(read('crossings.json'))
out('clock_hierarchy_contract.json',{
 'primary_su_roots':[{'proposed_primary_index':i,'actual_source_root':None,'local_root_map':None,'phase':None,'station_contract':None} for i in range(8)],
 'selected_parent':{'hierarchy':'c16_W5_1.u_t_0_0.u_g.u_tile','source_commit':'0d4c9808fe7d2370185a4313e831b6f59f7a2f75','REGROOT':2,'external_ck':'n_clk_r1','tile_clock_entries':sorted({x for x in ports['input'] if x.startswith('ck')}),'all_tile_entries_source_tied_to':'ck_c0r0','physical_equal_phase':None},
 'local_eight_regions':[{'g':i,'lsl':'ck_lsl'+str(i),'tx':'ck_tx'+str(i),'primary_su_root':None,'native_phase':None,'reset_recovery':None,'reach_405um':None,'new_storage_bits':None,'added_schedule_edges':None} for i in range(8)],
 'qualification':'UNRESOLVED; top-level eight SU roots are not local LSL/TX roots'})
out('summary.json',{'scope':'SOURCE AUTHORITY REFERENCE / PLAN ONLY','selected_REGROOT':2,'diagnostic_REGROOT':5,'crossing_producers':len(cross) if isinstance(cross,list) else None,'surviving_ib_bits':141,'primary_SU_maps_proved':0,'production_first_use':None,'native_substitution_proved':False,'RTL_changed':False,'compile_launched':False,'new_state_cost':None,'new_schedule_cost':None})
out('source_hashes.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(S.iterdir())})
print('PASS: exact GEN0 and 3 selected constructors; 380 descriptor bits; all 141 surviving IB bits; branch-specific diff; unresolved primary/phase contracts retained')
