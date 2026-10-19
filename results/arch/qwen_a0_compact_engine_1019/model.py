"""Finite source and necessary geometry model. No EDA, placement, or routing."""
import collections, functools, gzip, hashlib, io, json, pathlib, re
P = pathlib.Path(__file__).resolve().parent
A = P.parent
source = gzip.open(A/'qwen_a0_reset_1019/r3/candidate.v.gz', 'rt').read()
abstracts = json.load(gzip.open(A/'qwen_a0_ownership_1019/native_abstracts.json.gz'))['masters']
old = json.load(A.joinpath('qwen_a0_ownership_1019/ownership.json').open())
areas = json.load(A.joinpath('qwen_a0_ownership_1019/native_area.json').open())['master_area_um2']
transforms = json.load(gzip.open(A/'qwen_a0_topology_firstuse_1019/transformed_pins.json.gz'))
region = [561.6, 349.92, 604.8, 375.84]

def bits(expr):
    """Return MSB first; refuse unsupported slices/replication/expression/aliases."""
    expr = expr.strip()
    if expr.startswith('{'):
        assert expr.endswith('}') and '{' not in expr[1:], expr
        return sum((bits(t) for t in expr[1:-1].split(',')), [])
    if expr.startswith('\\'):
        assert re.fullmatch(r'\\\S+\s*', expr), expr
        return [expr[1:].strip()]
    match = re.fullmatch(r"(\d+)'b([01]+)", expr)
    if match:
        width, values = match.groups()
        assert len(values) == int(width)
        return ['CONST/'+b for b in values]
    raise ValueError('Unsupported expression: '+expr)

def connect(port, expr):
    values = bits(expr)
    return {port if len(values) == 1 else f'{port}[{i}]': net
            for i, net in zip(range(len(values)-1, -1, -1), values)}

assert connect('a', r'{\n2 ,\n1 ,\n0 }') == {'a[2]':'n2','a[1]':'n1','a[0]':'n0'}
assert connect('a', "3'b101") == {'a[2]':'CONST/1','a[1]':'CONST/0','a[0]':'CONST/1'}
assert connect('a', r'\escaped\[3\] ') == {'a':'escaped\\[3\\]'}
for bad in [r'{2{\n }}', r'\a + \b', 'some_alias', "2'bx1"]:
    try: bits(bad)
    except (ValueError, AssertionError): pass
    else: raise AssertionError(bad)
assert not re.search(r'\bassign\b', source), 'Aliases require explicit bit-order resolution'

cells, omitted = {}, []
for master, name, body in re.findall(r'\\(\S+)\s+\\(\S+)\s+\((.*?)\);', source, re.S):
    pins = {}
    for port, expr in re.findall(r'\.\\(\S+)\s*\((.*?)\)', body, re.S):
        expanded = connect(port, expr)
        assert not set(pins).intersection(expanded)
        pins.update(expanded)
        if expr.strip().startswith('{'):
            omitted.append({'cell':name,'master':master,'port':port,'bits':len(expanded),
                            'MSB_first_nets':bits(expr)})
    if pins: cells[name] = (master, pins)
assert len(cells) == old['source_cells'] == 38609

def outs(master, pins):
    if master in abstracts:
        assert set(pins) == {p for p,i in abstracts[master]['pins'].items() if i['signal_type'] not in ('POWER','GROUND')}, master
        return {p for p in pins if abstracts[master]['pins'][p]['direction']=='OUTPUT'}
    return set(pins).intersection({'Y','QN','Q','H','L'})

drivers, consumers = collections.defaultdict(list), collections.defaultdict(list)
for name,(master,pins) in cells.items():
    for p,n in pins.items():
        (drivers if p in outs(master,pins) else consumers)[n].append((name,p))
for net, ds in drivers.items():
    # A ROM result bus is shared by the two actual column macros in this source.
    if len(ds)>1:
        assert all(cells[n][0] in abstracts for n,p in ds), (net,ds)

def boundary(master): return master.startswith(('DFF','TIE')) or master in abstracts
@functools.lru_cache(None)
def upstream(net):
    if net.startswith('CONST/'): return frozenset([net])
    if net not in drivers: return frozenset(['PORT/'+net])
    result=set()
    for name,pin in drivers[net]:
        master,pins=cells[name]
        if boundary(master): result.add(name+'/'+pin)
        else:
            for p,n in pins.items():
                if p not in outs(master,pins): result.update(upstream(n))
    return frozenset(result)

@functools.lru_cache(None)
def downstream(net):
    result=set()
    for name,p in consumers.get(net,[]):
        master,pins=cells[name]
        if master.startswith('DFF') or master in abstracts: result.add(name+'/'+p)
        else:
            for op in outs(master,pins):result.update(downstream(pins[op]))
    return frozenset(result)

# The issue assignment is the union of each real unsafe control's combinational
# forward cone up to its first storage input, all those storage cells, and each
# canonical D cone with its actual upstream storage/reset operands. No renaming.
issue=set(); frontier=set(); protected=set()
def forward(net,seen):
    if net in seen:return
    seen.add(net)
    for name,p in consumers[net]:
        master,pins=cells[name]
        if master in abstracts:
            frontier.add(name+'/'+p);continue
        issue.add(name)
        if not master.startswith('DFF'):
            for op in outs(master,pins):forward(pins[op],seen)
def canonical(net,seen):
    if net in seen:return
    seen.add(net)
    for name,op in drivers.get(net,[]):
        master,pins=cells[name]
        if master in abstracts:frontier.add(name+'/'+op);continue
        issue.add(name);protected.add(name)
        if not boundary(master):
            for p,n in pins.items():
                if p not in outs(master,pins):canonical(n,seen)
for root in old['roots']:
    if root['master'].startswith('TIE'):continue
    name,op=root['driver'].rsplit('/',1)
    issue.add(name)
    forward(cells[name][1][op],set())
    for p,item in root['canonical_native_inputs'].items():
        if p!='CLK':canonical(item['net'],set())

def distance(a,b):return max(a[0]-b[2],b[0]-a[2],0)+max(a[1]-b[3],b[1]-a[3],0)
def overlap(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
children={}
for name,(master,pins) in cells.items():
    if master not in abstracts:continue
    clk=pins['clk']
    child='node' if clk=='ck_node' else ('rom'+clk[5:] if clk.startswith('ck_rp') else 'lsl'+clk[6:])
    children[child]=name
assert len(children)==19
hardrows=[]
for child in transforms:
    name=children[child['child']];master,pins=cells[name]
    for pin in child['pins']:
        row={'child':child['child'],'cell':name,'pin':pin['pin'],'type':pin['signal_type'],
             'direction':pin['direction'],'actual_shapes':pin['shapes'],
             'necessary_min_L1_to_compact_um':min(distance(x['rect_um'],region)for x in pin['shapes'])}
        if pin['pin'] in pins:
            net=pins[pin['pin']]; row['net']=net
            row['actual_upstream_boundaries']=sorted(upstream(net)) if pin['direction']=='INPUT' else []
            row['upstream_clock_owners']={e:cells[e.rsplit('/',1)[0]][1].get('CLK')
                 for e in row['actual_upstream_boundaries'] if e.rsplit('/',1)[0] in cells}
            row['input_boundary_in_issue']=[e for e in row['actual_upstream_boundaries']if e.rsplit('/',1)[0] in issue]
        else:
            assert pin['signal_type'] in ('POWER','GROUND'), (name,pin['pin'])
            row['unbound_in_source']=True
        hardrows.append(row)

cut=[]
for net in sorted(set(drivers)|set(consumers)):
    ds=drivers.get(net,[]); cs=consumers.get(net,[])
    inside_d=[n+'/'+p for n,p in ds if n in issue]
    inside_c=[n+'/'+p for n,p in cs if n in issue]
    outside_d=[n+'/'+p for n,p in ds if n not in issue]
    outside_c=[n+'/'+p for n,p in cs if n not in issue]
    if (inside_d and outside_c) or (inside_c and (outside_d or not ds)):
        cut.append({'net':net,'inside_drivers':inside_d,'inside_consumers':inside_c,
                    'outside_drivers':outside_d or (['PORT/'+net]if not ds else []),
                    'outside_consumers':outside_c,'new_crossing_latency':None,
                    'outside_endpoint_coordinates':None,
                    'actual_upstream_storage_or_port':sorted(upstream(net)),
                    'actual_downstream_first_storage':sorted(downstream(net)),
                    'outside_direct_endpoint_clocks':{n+'/'+p:cells[n][1].get('CLK',cells[n][1].get('clk'))for n,p in ds+cs if n not in issue}})

origins=json.load(A.joinpath('qwen_a0_topology_firstuse_1019/inherited_origins.json').open())['children']
obs_area=0;halo_area=0
for child in origins:
    x,y=child['at'];w,h=child['size'];halo_area+=overlap(region,[x-20,y-20,x+w+20,y+h+20])
    master='ot_qwen_tile_node'if child['name']=='node'else ('ot_qwen_tile_romleaf'if child['name'].startswith('rom')else'ot_qwen_tile_lsl_fp1')
    for shape in abstracts[master]['obs']:
        r=shape['rect_um'];obs_area+=overlap(region,[r[0]+x,r[1]+y,r[2]+x,r[3]+y])
area=sum(areas[cells[n][0]]for n in sorted(issue))
summary={'status':'MODEL_SOURCE_ASSIGNMENT_EXACT_GEOMETRY_NECESSARY_ONLY',
 'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
 'parsed_cells':len(cells),'newly_expanded_bus_connections':len(omitted),
 'newly_expanded_hard_pin_bits':sum(r['bits']for r in omitted),
 'multiple_hard_drivers':sum(len(v)>1 for v in drivers.values()),
 'region_um':region,'region_area_um2':(region[2]-region[0])*(region[3]-region[1]),
 'region_L1_diameter_um':region[2]-region[0]+region[3]-region[1],
 'issue_cells':len(issue),'issue_FF':sum(cells[n][0].startswith('DFF')for n in issue),
 'issue_native_area_um2':area,'issue_clock_owners':dict(collections.Counter(cells[n][1].get('CLK')for n in issue if cells[n][0].startswith('DFF'))),
 'issue_fill_fraction':area/((region[2]-region[0])*(region[3]-region[1])),
 'issue_plus_inherited_copy_floor_fill_fraction':(area+20.4849)/((region[2]-region[0])*(region[3]-region[1])),
 'local_ck_root_proposed_um':[(region[0]+region[2])/2,(region[1]+region[3])/2],
 'protected_cells':len(protected),'root_forward_hard_boundary_count':len(frontier),
 'root_forward_hard_boundaries':sorted(frontier),'compact_OBS_overlap_um2':obs_area,'compact_20um_bbox_halo_overlap_um2':halo_area,
 'all_hard_pin_shapes':len(hardrows),'all_signal_pins':sum(r['type']=='SIGNAL'for r in hardrows),
 'input_pins_with_issue_boundary':sum(bool(r.get('input_boundary_in_issue'))for r in hardrows),
 'issue_to_hard_geometric_obstructions':[{'child':r['child'],'pin':r['pin'],'minimum_L1_um':r['necessary_min_L1_to_compact_um'],'source_boundaries':r['input_boundary_in_issue']}for r in hardrows if r.get('input_boundary_in_issue')and r['necessary_min_L1_to_compact_um']>405],
 'all_signal_pins_beyond405_from_compact':sum(r['type']=='SIGNAL'and r['necessary_min_L1_to_compact_um']>405 for r in hardrows),
 'cut_nets':len(cut),'cut_endpoint_coordinates_qualified':False,
 'cut_direction_counts':dict(collections.Counter('outgoing'if r['inside_drivers']else'incoming'for r in cut)),
 'cut_direct_endpoint_clock_counts':dict(collections.Counter(str(clock)for r in cut for clock in r['outside_direct_endpoint_clocks'].values())),
 'cut_with_no_outside_driver':sum(any(e.startswith('PORT/')for e in r['outside_drivers'])for r in cut),
 'hard_input_upstream_clock_counts':dict(collections.Counter(str(clock)for r in hardrows for clock in r.get('upstream_clock_owners',{}).values())),
 'new_clock_roots':0,'new_reset_stages':0,'new_landing_bits':None,'added_cycles':None,
 'reset_leafs_in_region':[n for n in sorted(issue)if n.startswith('a0_reset_leaf')],
 'issue_ASR_FF':sum(cells[n][0].startswith('DFFASR')for n in issue),
 'site_rows_PG_access_parent121_endpoints_native_phase_firstuse':'UNRESOLVED',
 'inherited_copy_FF_lower_bound':59,'inherited_copy_area_lower_bound_um2':20.4849}

def gz(name,data):
    with (P/name).open('wb')as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0)as compressed:
            with io.TextIOWrapper(compressed)as f:json.dump(data,f,sort_keys=True)
gz('omitted_bus_inventory.json.gz',omitted)
gz('hard_pin_ownership.json.gz',hardrows)
gz('issue_assignment.json.gz',[{'cell':n,'master':cells[n][0],'pins':cells[n][1],'protected_canonical_operand_or_cone':n in protected,'region':region}for n in sorted(issue)])
gz('crossing_ledger.json.gz',cut)
gz('first_use_ports.json.gz',[
    {'cell':n,'clock':cells[n][1]['CLK'],'actual_D':cells[n][1].get('D'),
     'actual_D_source_boundaries':sorted(upstream(cells[n][1]['D'])),
     'actual_async_controls':{p:net for p,net in cells[n][1].items()if p in ('RESETN','SETN')},
     'first_consuming_storage':sorted(set().union(*(downstream(cells[n][1][op])for op in outs(*cells[n])))),
     'qualified_first_use_edge':None,'reset_or_valid_overwrite_proof':None}
    for n in sorted(issue)if cells[n][0].startswith('DFF')])
(P/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
