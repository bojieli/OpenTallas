"""Exact native pointer canonical-D and reset-stage owner ledger, model only."""
from pathlib import Path
import collections,gzip,json
P=Path(__file__).resolve().parent
rows=json.loads(gzip.decompress((P.parent/'s81_ve_current_model_1019/endpoint_roots.json.gz').read_bytes()))
def inst(p):return p.rsplit('/',1)[0]
inv={inst(r['driver']['pin']):r for r in rows if (r['driver']['master'] or '').startswith('CKINV')}
for r in rows:
    end={}
    for s in r['sinks']:
        for t in inv[inst(s['pin'])]['sinks'] if inst(s['pin']) in inv else [s]:end[t['pin']]=t
    r['sinks']=list(end.values())
rows=[r for r in rows if inst(r['driver']['pin']) not in inv]
roots={r['driver']['pin']:r for r in rows}
incoming=collections.defaultdict(dict)
for r in rows:
    for s in r['sinks']:
        if s['signal']=='CLOCK':continue
        old=incoming[inst(s['pin'])].get(s['pin'].rsplit('/',1)[1]);assert old is None or old==r['driver']['pin']
        incoming[inst(s['pin'])][s['pin'].rsplit('/',1)[1]]=r['driver']['pin']
copies={x['instance']:x['copies'] for x in json.loads((P/'fixed_point.json').read_text())['copies']}
def cone(start):
    todo=[start];seen=set();boundary=[];comb=[]
    while todo:
        p=todo.pop()
        if p in seen:continue
        seen.add(p);r=roots[p];d=r['driver'];m=d['master'] or ''
        if d['role'] in ('ff','input','macro') or m.startswith('TIE'):
            boundary.append(d);continue
        comb.append(d)
        todo.extend(incoming[inst(p)].values())
    return dict(combinational_cells=sorted(comb,key=lambda d:d['pin']),state_input_tie_boundaries=sorted(boundary,key=lambda d:d['pin']))
pointers=[];resets=[];group=collections.defaultdict(list)
for r in rows:
    d=r['driver'];i=inst(d['pin'])
    if d['role']!='ff':continue
    if '.wptr' in i:
        deps=incoming[i];assert 'D' in deps
        c=cone(deps['D']);ring=i.split('.wptr')[0]
        assert all('.wptr' not in b['pin'] or b['pin'].split('.wptr')[0]==ring for b in c['state_input_tie_boundaries'])
        item=dict(original_state_pin=d['pin'],canonical_owner=d['pin']+' copy0',required_total_copies=copies.get(i,1),common_next_state_driver=deps['D'],common_next_state_cone=c,nonclock_input_dependencies=deps,ring=ring)
        pointers.append(item);group[ring].append(item)
    if 'reset_leaf' in i or 'rst_n__ot_rl' in i:
        deps=incoming[i]
        resets.append(dict(state_pin=d['pin'],master=d['master'],required_total_copies=copies.get(i,1),incoming_sources=deps,D_cone=cone(deps['D']) if 'D' in deps else None,contract='All retained copies receive equivalent same-age D and identical existing clear/set; preserve inherited stage age. No extra relay stage.'))
ringrecords=[]
for ring,items in group.items():
    ringrecords.append(dict(ring=ring,pointer_bits=len(items),canonical_vector=[p['canonical_owner'] for p in sorted(items,key=lambda x:x['original_state_pin'])],added_pointer_ff=sum(p['required_total_copies']-1 for p in items),owner_rule='Next-state function reads only this complete canonical vector. Every retained pointer copy captures its corresponding canonical next-state bit. Read and write address copies may differ only before first fill; both must use this vector after edge1.'))
# Reserve ONE canonical next-state cone and ALL pointer-copy D inputs on it.
# Remaining address/decode loads may consume other retained copies.
canon_cells={inst(c['pin']) for x in pointers for c in x['common_next_state_cone']['combinational_cells']}
ptr_cells={inst(x['original_state_pin']):x['required_total_copies'] for x in pointers}
reserved=[]
for r in rows:
    if r['driver']['pin']=='PORT/clk' or r['driver']['signal']=='CLOCK':continue
    count=0
    for t in r['sinks']:
        if t['signal']=='CLOCK':continue
        ti=inst(t['pin']);pin=t['pin'].rsplit('/',1)[1]
        if ti in canon_cells:count+=1
        elif ti in ptr_cells and pin=='D':count+=ptr_cells[ti]
    if count:reserved.append(dict(driver=r['driver']['pin'],reserved_canonical_load=count))
assert all(x['reserved_canonical_load']<=32 for x in reserved)
out=dict(pointer_bits=len(pointers),rings=len(group),added_pointer_ff=sum(x['required_total_copies']-1 for x in pointers),ring_owners=ringrecords,pointer_bit_owners=pointers,reset_state_owners=resets,canonical_next_state_cone_cells=len(canon_cells),canonical_reserved_max_load=max(x['reserved_canonical_load'] for x in reserved),canonical_reserved_loads=reserved,canonical_partition_verdict='PASS abstract pin capacities: one canonical next-state cone plus all pointer-copy D loads fit one <=32-load copy per root. Remaining loads partition across remaining capacity. Does not prove RTL retention.',scope='Exact original native D/input owner names, not RTL-cell correspondence or actual copied netlist. Read/write decoder and final copy load partition must be implemented and checked against canonical ownership. Clock is intentionally excluded from D/clear dependency map.')
(P/'authoritative.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('ring_owners','pointer_bit_owners','reset_state_owners','canonical_reserved_loads')},indent=2));print('reset states',len(resets))
