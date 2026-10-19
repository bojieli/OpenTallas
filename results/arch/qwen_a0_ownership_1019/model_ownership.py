"""Read existing pinned artifacts only; no simulator/synthesis invocation."""
import collections,gzip,hashlib,json,re,pathlib
here=pathlib.Path(__file__).resolve().parent
base=here.parent/'qwen_a0_reset_1019'/'r3'
s=gzip.open(base/'candidate.v.gz','rt').read()
c=json.load(gzip.open(base/'census.json.gz'))
cells={}
for m in re.finditer(r"\\(\S+)\s+\\(\S+)\s+\((.*?)\);",s,re.S):
    master,name,body=m.groups()
    pins=dict(re.findall(r"\.\\(\S+)\s*\(\\(\S+)\s*\)",body))
    if pins: cells[name]=(master,pins)
assert len(cells)==c['cells'],(len(cells),c['cells'])
rows=c['all_drivers']; bynet={r['net']:r for r in rows}
transparent=lambda master:bool(re.match(r'^(?:BUF|INV|HB)',master))
def canonical(net,seen=None):
    seen=set() if seen is None else seen
    if net in seen:return {'unresolved':'cycle','net':net}
    seen.add(net);r=bynet.get(net)
    if not r:return {'unresolved':'missing driver','net':net}
    if transparent(r['master']):
        name=r['driver'].rsplit('/',1)[0];pins=cells[name][1]
        ins=[v for k,v in pins.items() if k not in ('Y','QN','Q','H','L')]
        assert len(ins)==1,(name,pins)
        return canonical(ins[0],seen)
    return {'driver':r['driver'],'master':r['master'],'clock':r['clock']}
roots=[]
for r in rows:
    if r['clock'] or r['transparent_loads']<=32 or transparent(r['master']):continue
    name=r['driver'].rsplit('/',1)[0];master,pins=cells[name]
    sinks=[]
    for endpoint in r['endpoints']:
        sink,pin=endpoint.rsplit('/',1)
        if sink=='PORT':sinks.append({'endpoint':endpoint,'role':'output port'});continue
        sm,sp=cells[sink]
        semantic=[v for k,v in sp.items() if k in ('Y','QN','Q') and ('u_g.' in v)]
        sinks.append({'endpoint':endpoint,'master':sm,'clock':sp.get('CLK'),
            'semantic_output_nets':semantic,'physical_region':None})
    ins={k:{'net':v,**canonical(v)} for k,v in pins.items() if k not in ('Y','QN','Q','H','L')}
    roots.append({'driver':r['driver'],'master':master,'actual_terminal_inputs':r['transparent_loads'],
        'canonical_native_inputs':ins,'terminal_ownership':sinks,
        'destination_clock_owners':dict(collections.Counter(x.get('clock','comb_or_port') for x in sinks)),
        '24_load_state_count_lower_bound_only':(r['transparent_loads']+23)//24,
        'copies_assigned_to_actual_geometry':False})
report={'schema':'opentallas.a0.exact_ownership_inventory.v1',
 'status':'MODEL_INCOMPLETE_NO_RTL_NO_GATE',
 'candidate_sha256':hashlib.sha256(s.encode()).hexdigest(),
 'census_sha256':hashlib.sha256(gzip.open(base/'census.json.gz','rb').read()).hexdigest(),
 'source_cells':len(cells),'source_ff':sum(v for k,v in c['masters'].items() if k.startswith('DFF')),
 'unsafe_native_rows':70,'unsafe_transparent_rows':58,
 'independent_unsafe_sequential_roots':7,'independent_unsafe_logic_roots':3,
 'independent_unsafe_tie_roots':2,'roots':roots,
 'contract':{'all_native_nonclock_drivers_limit':32,'cohort_design_target':24,
 'retained_contexts':254,'cleared_metadata':6,'steady_edges_added':0,
 'first_use_physical_guard_qualified':False,'geometry_qualified':False,'full_token_delta':None},
 'must_prove_before_source':['Destination lane/region ownership and <=405um actual pin paths',
 'Canonical D, enable, mux, reset and polarity preserved for every useful copy',
 'Arbitrary clone initial state: first-edge convergence is insufficient if downstream retained state samples an unknown copy on that edge',
 'All warm/cold reset epochs and producer configuration-load-before-meaningful-use',
 'Recompute all upstream D/reset/logic/tie input pins to a fixed point',
 'Two face reset stages and source-consistent regional release, boot and clock phases',
 'Full mapped area, clock capacitance, parent slot and every added compiler age']}
(here/'ownership.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('roots','must_prove_before_source')},indent=2))
