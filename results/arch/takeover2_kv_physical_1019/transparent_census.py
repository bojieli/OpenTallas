import collections, hashlib, json, re, sys
from functools import lru_cache
src_path, out_path = sys.argv[1:3]
src = open(src_path).read()
cell_re = re.compile(r'^\s*(?:\(\*[^*]*\*\)\s*)?(\w+)\s+(c\w+)\s*\((.*)\);\s*$', re.M)
outs = {'Y','QN','Q','H','L','CON','SN'}
cells = {n:(m,dict((k,v.strip()) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',p))) for m,n,p in cell_re.findall(src)}
assigns = re.findall(r'^\s*assign\s+(\S+)\s*=\s*(\S+?)\s*;',src,re.M)
parent = {}
def find(x):
    parent.setdefault(x,x)
    if parent[x] != x: parent[x] = find(parent[x])
    return parent[x]
def union(a,b):
    a,b=find(a),find(b)
    if a!=b: parent[a]=b
for a,b in assigns: union(a,b)
inputs={find(a):b for a,b in assigns if re.fullmatch(r'n\d+',a)}
output_ports={a:find(b) for a,b in assigns if not re.fullmatch(r'n\d+',a)}
loads=collections.defaultdict(list); drivers=collections.defaultdict(list)
for name,(master,pins) in cells.items():
    for pin,net in pins.items():
        net=find(net)
        (drivers[net] if pin in outs else loads[net]).append((name,pin))
for port,net in output_ports.items(): loads[net].append(('PORT',port))
def transparent(master): return master.startswith(('BUF','INV','HB'))
visiting=set()
@lru_cache(None)
def terminal(net):
    if net in visiting: raise RuntimeError('Transparent cycle: '+net)
    visiting.add(net); answer=set()
    for name,pin in loads.get(net,[]):
        if name=='PORT': answer.add((name,pin)); continue
        master,pins=cells[name]
        if transparent(master):
            output=[find(v) for p,v in pins.items() if p in outs]
            if len(output)!=1: raise RuntimeError('Ambiguous transparent cell '+name)
            answer.update(terminal(output[0]))
        elif pin not in ('CLK','CK'): answer.add((name,pin))
    visiting.remove(net); return frozenset(answer)
records=[]
for net,ds in drivers.items():
    for name,pin in ds:
        master=cells[name][0]
        role='ff' if master.startswith('DFF') else 'tie' if master.startswith('TIE') else 'transparent' if transparent(master) else 'comb'
        endpoints=terminal(net)
        records.append(dict(net=net,driver=name,pin=pin,master=master,role=role,count=len(endpoints),endpoints=sorted(endpoints)))
for net,port in inputs.items():
    records.append(dict(net=net,driver=port,pin='PORT',master='PORT',role='input',count=len(terminal(net)),endpoints=sorted(terminal(net))))
records.sort(key=lambda r:(-r['count'],r['driver'],r['pin']))
roles=collections.defaultdict(list)
for r in records: roles[r['role']].append(r)
functional=[r for r in records if r['role']!='transparent']
result=dict(schema='opentallas.transparent_all_driver_native_census.v1',source=src_path,source_sha256=hashlib.sha256(src.encode()).hexdigest(),cells=len(cells),ff=sum(m.startswith('DFF') for m,p in cells.values()),native_cell_lines=len(re.findall(r'^.*_ASAP7_.*;',src,re.M)),drivers=len(records),max_by_role={k:max(r['count'] for r in rs) for k,rs in roles.items()},over32=[r for r in functional if r['count']>32],top=records[:30],multidriven=[dict(net=n,drivers=d) for n,d in drivers.items() if len(d)>1],unresolved_loads=[n for n in loads if n not in drivers and n not in inputs and not n.startswith("1'")])
json.dump(result,open(out_path,'w'),indent=2)
print(json.dumps({k:v for k,v in result.items() if k not in ('top','over32','unresolved_loads','multidriven')}))
print('OVER32',len(result['over32']),'MULTIDRIVEN',len(result['multidriven']),'UNRESOLVED',len(result['unresolved_loads']))
for r in result['over32'][:20]: print(r['role'],r['driver'],r['pin'],r['net'],r['count'])
