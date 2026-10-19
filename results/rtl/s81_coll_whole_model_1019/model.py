"""Bounded read-only analytical model; no RTL synthesis or simulation.

Parses the preserved mapped Verilog, expands the one combinational helper,
counts every sink pin, and removes BUF/INV boundaries for a conservative
electrical fanout census. Inverter polarity is irrelevant to load counting.
"""
from pathlib import Path
import collections, gzip, hashlib, json, math, re

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 's81_coll_safe2_param_1019' / 'mapped'
raw = gzip.decompress((BASE / '1_2_yosys.v.gz').read_bytes())
assert hashlib.sha256(raw).hexdigest() == '512e2b3b6362acd91360d73e09d5c9191163e53cb55d4b07cb22cd86a1d75e0e'
txt = re.sub(r'\(\*.*?\*\)', '', raw.decode(), flags=re.S)
modules = dict(re.findall(r'module\s+(\w+)\s*\([^;]*;(.+?)endmodule', txt, re.S))
def bits(expr):
    return [x.lstrip('\\') for x in re.findall(r'\\\S+|[A-Za-z_$][\w$]*(?:\[\d+\])?', expr)]
def cells(body):
    return [(typ, name.lstrip('\\'), {p:bits(e) for p,e in re.findall(r'\.(\w+)\s*\((.*?)\)', ports, re.S)})
            for typ,name,ports in re.findall(r'^\s{2}(\w+)\s+(\\\S+|[\w$]+)\s*\((.*?)\);', body, re.M|re.S)]
top = modules['dsfd_coll_lane_w_safe2']
flat = []
for typ,name,ports in cells(top):
    if typ not in modules:
        flat.append((typ,name,ports)); continue
    assert typ == 'ot_sram_showahead_hit5', typ
    external = {}
    for p,bs in ports.items():
        for i,b in enumerate(reversed(bs)):
            external[f'{p}[{i}]'] = b
        if len(bs)==1: external[p]=bs[0]
    for t,n,ps in cells(modules[typ]):
        flat.append((t,f'{name}/{n}',{p:[external.get(b,f'{name}/{b}') for b in bs] for p,bs in ps.items()}))
parent = {}
def find(a):
    parent.setdefault(a,a)
    if parent[a]!=a: parent[a]=find(parent[a])
    return parent[a]
def join(a,b):
    a,b=find(a),find(b)
    if a!=b: parent[b]=a
for lhs,rhs in re.findall(r'assign\s+(.*?)\s*=\s*(.*?);',top):
    a,b=bits(lhs),bits(rhs)
    if len(a)==len(b):
        for x,y in zip(a,b): join(x,y)
outpins={'Y','Z','ZN','Q','QN','X','H','L','hit','rd_out'}
def transparent(t): return t.startswith(('BUF','INV'))
for t,n,ps in flat:
    if transparent(t):
        ins=[b for p,bs in ps.items() if p not in outpins for b in bs]
        outs=[b for p,bs in ps.items() if p in outpins for b in bs]
        assert len(ins)==len(outs)==1,(t,n,ps)
        join(ins[0],outs[0])
loads=collections.defaultdict(list); drivers=collections.defaultdict(list)
for t,n,ps in flat:
    if transparent(t): continue
    for p,bs in ps.items():
        if p in ('VDD','VSS','VPWR','VGND'): continue
        for b in bs:
            (drivers if p in outpins else loads)[find(b)].append({'cell':n,'type':t,'pin':p,'net':b})
rows=[]
for root,ls in loads.items():
    ds=drivers[root]
    if any(d['type'].startswith('TIE') for d in ds): role='constant'
    elif all(x['pin'].lower() in ('clk','ck','wclk','rclk') for x in ls): role='clock'
    elif any(x['pin'] in ('RESETN','SETN','RESET','RN','SN') for x in ls): role='reset_or_mixed'
    else: role='data_control'
    rows.append({'root':root,'loads':len(ls),'role':role,'drivers':ds,'sinks':ls})
rows.sort(key=lambda r:(-r['loads'],r['root']))
with gzip.open(HERE/'full_transparent_census.json.gz','wt') as f: json.dump(rows,f,separators=(',',':'))
over=[r for r in rows if r['loads']>32]
with gzip.open(HERE/'over32.json.gz','wt') as f: json.dump(over,f,separators=(',',':'))
# These are allocation lower bounds on copied driver outputs, not mapped proof.
ledger=[]
for r in over:
    if r['role'] in ('clock','constant'): continue
    n=math.ceil(r['loads']/16)
    families=collections.Counter()
    for s in r['sinks']:
        name=s['cell']
        key='gearbox' if 'u_gb' in name else 'endpoint' if 'u_ep' in name else 'credit_rx' if 'g_lcri' in name else 'credit_tx' if 'g_lcro' in name else 'other'
        families[key]+=1
    ledger.append({'root':r['root'],'drivers':r['drivers'],'loads':r['loads'],'receiver_families':dict(families),
                   'minimum_output_copies_at16':n,'upstream_producer_closure':'OPEN: recursively localize same-edge input cones; no common n-load D expression accepted'})
(HERE/'control_ledger.json').write_text(json.dumps(ledger,indent=2)+'\n')
summary={'status':'MODEL_ONLY_NOT_SOURCE_ADMISSION','netlist_sha256':hashlib.sha256(raw).hexdigest(),
         'top_cells':len(cells(top)),'expanded_cells':len(flat),'all_electrical_roots':len(rows),
         'all_over32':len(over),'over32_by_role':dict(collections.Counter(r['role'] for r in over)),
         'output_copy_lower_bound_at16':sum(x['minimum_output_copies_at16'] for x in ledger),
         'no_sink_cap':True,'transparent_buffers_inverters':True,'expanded_combinational_helper':True,
         'storage':{'width':595,'depth':4,'banks':10,'bank_width':64,'bank_depth':32,
                    'physical_bits':20480,'logical_bits':2380,'paid_unused_bits':18100,
                    'last_bank_useful_bits':19,'zero_tail_bits':45,'unreachable_rows':28,
                    'macro_area_um2':10*553.589568,'macro_clock_pins':20,'macro_clock_cap_ff':20*9.3458,
                    'ports_bits_per_cycle':595,'ports_bytes_per_cycle':595/8,
                    'logical_peak_slots_per_cycle':1,'average_sustainable_slots_per_cycle':3/4*1023/1024,
                    'helper_payload_ff':1190,'helper_flags':76,'helper_address_valid_ff':3,
                    'helper_total_ff':1269,'helper_compare_groups':3,'added_edges_proposed':0},
         'admission':{'actual_candidate_mapping':None,'actual_clockcap_std':None,'actual_slot':None,
                      'actual_band_fill':None,'actual_pin_reach':None,'new_boundary_miter':None}}
summary['whole_lane_memory_decision']={
    'status':'BLOCKED_EXISTING_512x128_AND_32x128_CONTACT_DENSITY',
    'preferred_investigation':'actual wider-pitch compiler masters plus primitive escape qualification',
    'bank64_fallback':{'deep_stores':2,'banks_per_deep_store':144,'credit_banks':9,'gearbox_banks':10,
                       'total_banks':307,'raw_bits':307*32*64,'useful_bits':2*553*512+553*8+595*4,
                       'macro_area_um2':307*553.589568,'macro_clock_pins':614,
                       'macro_clock_cap_ff':614*9.3458,'read_merge_inputs_per_deep_store':16,
                       'arithmetic_outline_um':[1166.4,1166.4],'actual_fit':None,'added_edges':None},
    'partial_gearbox_only_outline_um':[648,561.6],
    'partial_outline_full_lane_admission':False,
    'existing_parent_width_lower_bound_um':561.6+475.2+43.2,
    'existing_parent_reserved_width_um':950,
    'producer_copy_graph_complete':False}
assert 9*64<595<=10*64
assert sum(min(64,595-64*b) for b in range(10))==595
assert summary['storage']['physical_bits']-2380==18100
assert len(flat)==66676
assert collections.Counter(r['role'] for r in over)=={'clock':1,'constant':2,'data_control':37,'reset_or_mixed':2}
assert next(r['loads'] for r in rows if any(d['cell']=='u.u_gb.g_f1.sh[0]$_DFFE_PN0P_' for d in r['drivers']))==2382
assert next(r['loads'] for r in rows if any(d['cell']=='u.u_ep.a_rep$_DFF_P_' for d in r['drivers']))==1106
(HERE/'model.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('storage','admission')},indent=2))
