#!/usr/bin/env python3
"""Read-only, uncapped native endpoint inventory and conditional copy model.

Run against the immutable qw-f16-selects-1019 directory. No synthesis or RTL
simulation occurs. Every non-clock pin retains its endpoint role. INV polarity
is retained in paths while fanout passes through BUF/INV. Native FF QN is not Q.
"""
import argparse, collections, gzip, hashlib, json, math, re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('inputs', type=Path)
p.add_argument('output', type=Path)
args = p.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
expected = {'native.json':'d5d3e5a82538e4df7203cd8b5eaff2e8ce43e359b3c340bd0692c7381ffa9e2d',
            'generic.json':'2ae8bbc65f94c00c8edcee6f031ba3b2074ea68cdc7d7e09d56bf1318477b6b1',
            'comb.lib':'377a3a261542fb9defb41e3d3df3a0ecce9888629bb16bb4ef735007e66536b8',
            'seq.lib':'57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3'}
for f, h in expected.items():
    assert hashlib.sha256((args.inputs/f).read_bytes()).hexdigest() == h, f
j = json.loads((args.inputs/'native.json').read_text())['modules']['qfd_dv_typed_witness_control']
g = json.loads((args.inputs/'generic.json').read_text())['modules']['qfd_dv_typed_witness_control']
cells = j['cells']
def ff(t): return bool(re.search('DFF|SDFF', t, re.I))
def trans(t): return bool(re.match(r'^(BUF|INV|HB)[x0-9_]', t, re.I))
def role(t): return 'ff' if ff(t) else 'macro' if re.search('sram',t,re.I) else 'tie' if re.search('TIE|LOGIC[01]',t,re.I) else 'comb'
def named(top):
    a = collections.defaultdict(list)
    for n, v in top['netnames'].items():
        if n.startswith('$'): continue
        for k, b in enumerate(v['bits']): a[b].append(f'{n}[{k}]')
    return a
ga, na = named(g), named(j)
ff_names = {}
for n,c in cells.items():
    if ff(c['type']):
        gc=g['cells'][n]
        ff_names[n] = sorted({v for po,bs in gc['connections'].items() if gc['port_directions'][po]=='output' for b in bs for v in ga[b]})
drivers, sinks, transparent = {}, collections.defaultdict(list), collections.defaultdict(list)
roots = {}
for n,v in j['ports'].items():
    for k,b in enumerate(v['bits']):
        label=f'port:{n}[{k}]'
        if v['direction']=='input':
            drivers[b]=label
            roots[label]={'role':'input','type':'port','bit':b,'source_names':[f'{n}[{k}]'],'cell':None}
        else: sinks[b].append({'pin':label,'role':'port','cell':None,'port':n})
for n,c in cells.items():
    outs=[(po,k,b) for po,bs in c['connections'].items() if c['port_directions'][po]=='output' for k,b in enumerate(bs)]
    if trans(c['type']):
        for po,bs in c['connections'].items():
            if c['port_directions'][po]=='input':
                for b in bs:
                    for op,k,ob in outs: transparent[b].append((ob,n, c['type'].startswith('INV')))
        continue
    for po,k,b in outs:
        label=f'{n}/{po}[{k}]'
        assert b not in drivers, (label,drivers.get(b))
        drivers[b]=label
        roots[label]={'role':role(c['type']),'type':c['type'],'bit':b,'source_names':ff_names.get(n,na[b]),'cell':n,'output_port':po}
    for po,bs in c['connections'].items():
        if c['port_directions'][po]!='input' or (ff(c['type']) and po in ('CLK','C','CK','CP')):continue
        for k,b in enumerate(bs):sinks[b].append({'pin':f'{n}/{po}[{k}]','role':role(c['type']),'cell':n,'port':po})
for b in ('0','1','x','z'):
    if b in sinks or b in transparent:
        label='constant:'+b;drivers[b]=label
        roots[label]={'role':'constant','type':'literal','bit':b,'source_names':[label],'cell':None}
roots.pop('port:ck[0]')
bit_root={}
for rn,r in roots.items():
    queue=[(r['bit'],False)];seen={};ep={}
    while queue:
        b,inv=queue.pop()
        if b in seen:
            assert seen[b]==inv, 'inconsistent transparent polarity'
            continue
        seen[b]=inv;bit_root[b]=(rn,inv)
        for v in sinks[b]:ep[v['pin']]={**v,'inverted_from_output':inv}
        for ob,n,iv in transparent[b]:queue.append((ob,inv ^ iv))
    r['endpoints']=sorted(ep.values(),key=lambda v:v['pin'])
    r['loads']=len(ep)
    r['transparent_cells']=sorted({n for b in seen for ob,n,iv in transparent[b]})
    r['aliases']=sorted({a for b in seen for a in na[b]})
for rn,r in roots.items():
    n=r['cell'];r['inputs']=[]
    if n:
        c=cells[n]
        for po,bs in c['connections'].items():
            if c['port_directions'][po]!='input' or (ff(c['type']) and po in ('CLK','C','CK','CP')):continue
            for k,b in enumerate(bs):
                rr,iv=bit_root[b]
                r['inputs'].append({'pin':f'{n}/{po}[{k}]','root':rr,'inverted_from_output':iv})
cell_root={r['cell']:rn for rn,r in roots.items() if r['cell']}
def boundary(rn,forward):
    q=[rn];seen=set();leaves=set()
    while q:
        x=q.pop()
        if x in seen:continue
        seen.add(x);r=roots[x]
        if x!=rn and (r['role']!='comb'):
            leaves.add(x);continue
        if forward:
            for e in r['endpoints']:
                if e['role']=='port':leaves.add(e['pin'])
                elif e['cell'] in cell_root:q.append(cell_root[e['cell']])
        else:q.extend(v['root'] for v in r['inputs'])
    return [{'root':x,'source_names':roots[x]['source_names'] if x in roots else [x]} for x in sorted(leaves)]
viol=[]
for rn,r in roots.items():
    if r['loads']>32:
        viol.append({'root':rn,**r,'backward_boundary':boundary(rn,False),'forward_boundary':boundary(rn,True)})
viol.sort(key=lambda r:(-r['loads'],r['root']))
assert len(roots)==20179 and len(viol)==51
counts={rn:1 for rn in roots}
iterations=[]
for i in range(100):
    loads={rn:sum(counts[cell_root[e['cell']]] if e['cell'] in cell_root else 1 for e in r['endpoints']) for rn,r in roots.items()}
    updated={rn:max(counts[rn], math.ceil(loads[rn]/32)) if r['role'] in ('comb','ff','tie') else 1 for rn,r in roots.items()}
    iterations.append({'iteration':i,'additional_by_role':dict(collections.Counter({ro:sum(updated[rn]-1 for rn,r in roots.items() if r['role']==ro) for ro in ('comb','ff','tie')})), 'changed_roots':sum(counts[rn]!=updated[rn] for rn in roots)})
    if updated==counts:break
    counts=updated
else:raise AssertionError('no bounded fixed point')
copies=[{'root':rn,'type':r['type'],'role':r['role'],'source_names':r['source_names'],'copies':counts[rn],'weighted_loads':loads[rn],'max_partition':math.ceil(loads[rn]/counts[rn])} for rn,r in roots.items() if counts[rn]>1]
external=[{'root':rn,'loads':loads[rn],'role':r['role']} for rn,r in roots.items() if r['role'] not in ('comb','ff','tie') and loads[rn]>32]
lib=(args.inputs/'comb.lib').read_text()+(args.inputs/'seq.lib').read_text()
areas={m[0]:float(m[1]) for m in re.findall(r'cell\s*\(\s*(\S+?)\s*\)\s*\{.*?\barea\s*:\s*([0-9.eE+-]+)',lib,re.S)}
area=sum((x['copies']-1)*areas[x['type']] for x in copies)
ffextra=sum(x['copies']-1 for x in copies if x['role']=='ff')
assert all(x['max_partition']<=32 for x in copies)
def family(r):
    n=r['root']
    if r['role']!='comb':return r['role']
    if n.endswith('$48934/Y[0]'):return 'PW template common admission'
    if n.endswith(('$54039/Y[0]','$54169/Y[0]')):return 'PW partial-word capture'
    if n.endswith('$53913/Y[0]'):return 'round-robin pick'
    if any(n.endswith(f'${x}/Y[0]') for x in (53620,53652,53684,53716)):return 'context start acceptance'
    if any(n.endswith(f'${x}/Y[0]') for x in (60239,60299,60359,60420,62457,62625,62793,62959)):return 'context counter update/start'
    if any(n.endswith(f'${x}/Y[0]') for x in (51535,50738,52150,52963)):return 'pending-user decode'
    fs=[a for b in r['forward_boundary'] for a in b['source_names']]
    assert fs and all(a.startswith(('dut.templates[','dut.loaded[')) for a in fs), (n,fs)
    return 'PW template record write'
for r in viol:r['family']=family(r)
with (args.output/'all_51.tsv').open('w') as f:
    f.write('root\trole\ttype\tloads\tfamily\tsource_names\n')
    for r in viol:f.write('\t'.join(str(r[k]) for k in ('root','role','type','loads','family','source_names'))+'\n')
summary={'source_commit':'ff1a7c518','source_sha256':'8536070ddb594a5b6ae98c3f9ff2d78371cc50ec159ea72d7466142eccd97640','inputs_sha256':expected,'roots':len(roots),'roles':dict(collections.Counter(r['role'] for r in roots.values())),'violations':len(viol),'violating_roles':dict(collections.Counter(r['role'] for r in viol)),'families':dict(collections.Counter(r['family'] for r in viol)),'conditional_fixed_point_iterations':iterations,'conditional_additional_cells':dict(collections.Counter({ro:sum(x['copies']-1 for x in copies if x['role']==ro) for ro in ('comb','ff','tie')})),'conditional_native_cell_area_um2':area,'polarity_inverter_reserve_cells':sum(x['copies']-1 for x in copies),'polarity_inverter_reserve_area_um2':sum(x['copies']-1 for x in copies)*areas['INVx1_ASAP7_75t_R'],'conditional_added_clock_sinks':ffextra,'conditional_added_clock_cap_fF':sum((x['copies']-1)*(.462899 if 'ASR' in x['type'] else .474736) for x in copies if x['role']=='ff'),'external_unresolved':external,'conditions':['Useful canonical gate duplication and actual same-canonical-D FF copies, no independent feedback muxes.','This is a logical endpoint partition model, not synthesis survival or a placement.','Copies add endpoints upstream; fixed point includes every original root, including safe roots.','Inputs and constants are never treated as clonable storage or fictional ties.','Existing parent two-stage reset replacement and complete PW input face capture remain unbound.'],'geometry':None,'native_timing':None,'internal_copy_added_edges':0,'parent_capture_added_edges':None,'reset_release_added_edges':None}
def dump(name,obj):
    b=(json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()
    if name.endswith('.gz'):
        with gzip.GzipFile(filename=str(args.output/name),mode='wb',mtime=0) as f:f.write(b)
    else:(args.output/name).write_bytes(b)
dump('all_roots.json.gz',roots);dump('all_51.json.gz',viol);dump('copies.json',copies);dump('summary.json',summary)
print(json.dumps(summary,indent=2))
