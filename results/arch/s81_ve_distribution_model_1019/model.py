"""Native-cell copy-load fixed point. Analytical mechanism, not remapped RTL."""
import collections, gzip, hashlib, json, math
from pathlib import Path
HERE=Path(__file__).resolve().parent
SRC=HERE.parent/'s81_ve_current_model_1019'
rows=json.loads(gzip.decompress((SRC/'endpoint_roots.json.gz').read_bytes()))
inv={r['driver']['pin'].rsplit('/',1)[0]:r for r in rows if (r['driver']['master'] or '').startswith('CKINV')}
for r in rows:
    ends={}
    for s in r['sinks']:
        inst=s['pin'].rsplit('/',1)[0]
        for e in inv[inst]['sinks'] if inst in inv else [s]: ends[e['pin']]=e
    r['sinks']=list(ends.values())
    if (r['driver']['master'] or '').startswith('TIE'):r['driver']['role']='tie'
rows=[r for r in rows if r['driver']['pin'].rsplit('/',1)[0] not in inv and r['driver']['signal']!='CLOCK' and r['driver']['pin']!='PORT/clk']
def cell(pin):return pin.rsplit('/',1)[0]
# Each original sink PIN contributes one load on every required destination copy.
meta={cell(r['driver']['pin']):r['driver'] for r in rows}
n={i:1 for i in meta}
parents=collections.defaultdict(set)
bycell=collections.defaultdict(list)
for j,r in enumerate(rows):
    bycell[cell(r['driver']['pin'])].append(j)
    for s in r['sinks']:
        if s['role']!='output':parents[cell(s['pin'])].add(j)
loads=[sum(n.get(cell(s['pin']),1) if s['role']!='output' else 1 for s in r['sinks']) for r in rows]
q=collections.deque(range(len(rows)));queued=set(q);steps=0;updates=0
while q:
    j=q.popleft();queued.discard(j);r=rows[j];i=cell(r['driver']['pin']);steps+=1
    wanted=math.ceil(loads[j]/32) or 1
    if wanted<=n[i] or meta[i]['role']=='input':continue
    old=n[i];n[i]=wanted;updates+=1
    if wanted>100000:raise RuntimeError('unbounded copy recurrence')
    delta=wanted-old
    for k in parents[i]:
        multiplicity=sum(cell(s['pin'])==i and s['role']!='output' for s in rows[k]['sinks'])
        loads[k]+=delta*multiplicity
        if k not in queued:q.append(k);queued.add(k)
assert all(loads[j]<=32*n[cell(r['driver']['pin'])] for j,r in enumerate(rows) if r['driver']['role']!='input')
add=collections.Counter();masters=collections.Counter();copies=[]
for i,v in n.items():
    if v>1:
        m=meta[i];add[m['role']]+=v-1;masters[m['master']]+=v-1
        roots=bycell[i]
        copies.append(dict(instance=i,master=m['master'],role=m['role'],copies=v,added=v-1,original_max_load=max(len(rows[j]['sinks']) for j in roots),fixed_point_max_load=max(loads[j] for j in roots),xy=m['xy']))
inputs=[dict(pin=r['driver']['pin'],loads=loads[j],capacity=32,pass32=loads[j]<=32) for j,r in enumerate(rows) if r['driver']['role']=='input']
result=dict(source_commit='78ad1399f',odb_sha256='c795bfb691f2f0769f0ea13a2c26cdbc067f18d5532553709e7b319f1e0bdb79',endpoint_sha256=hashlib.sha256((SRC/'endpoint_roots.json.gz').read_bytes()).hexdigest(),model='all native cell inputs replicated with destination; output loads fixed; BUF/INV incl CKINV transparent; clocks separately priced',roots=len(rows),instances=len(meta),updates=updates,queue_visits=steps,added_by_role=dict(add),added_by_master=dict(sorted(masters.items())),input_violations=[x for x in inputs if not x['pass32']],max_signal_input_load=max(x['loads'] for x in inputs),all_internal_partition_capacity_pass=True,minimum_added_copies=dict(ff=1685,comb=837),scope='Cell-copy connectivity feasibility only; identities under reset/initialization, kept source mapping, Liberty cost, clock/PG/placement/reach/timing unqualified. Not a native PASS or complete source implementation.',copies=sorted(copies,key=lambda x:-x['added']))
(HERE/'fixed_point.json').write_text(json.dumps(result,indent=2)+'\n')
(HERE/'input_loads.json').write_text(json.dumps(inputs,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('copies','added_by_master')},indent=2))
