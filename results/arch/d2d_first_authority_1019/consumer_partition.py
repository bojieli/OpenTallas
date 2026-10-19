import json, collections, hashlib
from pathlib import Path
base=Path('/home/ubuntu/artifacts/kv-d2d-sideband-model-1019')
src=(base/'census.py').read_text().split('    rows=[]')[0]+'    return locals()\n'
ns={};exec(src,ns)
netlist=base/'input/current_sfo_mapped.v.gz'
a=ns['census'](netlist)
cells,loads,ends=a['cells'],a['loads'],a['ends']
outputs={'QN','Q','Y','Z','CON','SN','H','L','rd_out'}
def desc(n,p,j,path=None):
 if n=='OUTPUT':return dict(cell=n,pin=p,bit=j,kind='output',path=path)
 t,ps=cells[n]
 return dict(cell=n,master=t,pin=p,bit=j,kind='sequential' if t.startswith('DFF') else 'macro' if t.startswith('ot_sram') else 'comb',reset_pins={k:v for k,v in ps.items() if k in ('RESETN','SETN')},path=path)
rows=[]
for clone in json.loads(Path('/home/ubuntu/artifacts/d2d-copy-startup-1019/constructor_plan.json').read_text())['clones']:
 n=clone['cell'];t,p=cells[n];v=p['QN'][0]
 logical=[desc(*e) for e in ends(v)]
 # Directed combinational reachability, stopping at the first sequential cell / macro / output. One shortest path per endpoint.
 q=collections.deque([(v,[])]);seen=set();targets={}
 while q:
  w,path=q.popleft()
  if w in seen:continue
  seen.add(w)
  for cn,pn,j in loads[w]:
   if cn=='OUTPUT':targets.setdefault((cn,pn,j),desc(cn,pn,j,path));continue
   ct,cp=cells[cn];np=path+[dict(cell=cn,pin=pn,master=ct)]
   if ct.startswith(('DFF','ot_sram')):
    targets.setdefault((cn,pn,j),desc(cn,pn,j,np));continue
   for op,vs in cp.items():
    if op in outputs:
     for z in vs:q.append((z,np))
 ts=list(targets.values())
 reset_groups=collections.Counter(tuple((k,tuple(v)) for k,v in sorted(x.get('reset_pins',{}).items())) for x in ts)
 reset_summary=[dict(pins={k:list(v) for k,v in group},first_endpoints=count) for group,count in reset_groups.items()]
 rows.append(dict(root=n,master=t,source_pins=p,transparent_logical_endpoint_count=len(logical),transparent_logical_endpoints=logical,first_state_or_output_count=len(ts),first_state_or_output=ts,reset_group_summary=reset_summary,direct_sequential_endpoint_count=sum(x['kind']=='sequential' for x in logical),first_state_summary=dict(collections.Counter(x['master'] if 'master' in x else 'OUTPUT' for x in ts)),unreset_first_state_count=sum(x['kind']=='sequential' and not x['reset_pins'] for x in ts),notes='Graph reachability is not Boolean sensitization. Reset pins are exact mapped connections, not a guarantee of assertion at the first clock. Equal D/CLK does not establish equal initial Q.'))
result=dict(status='HOLD_FIRST_AUTHORITY_NOT_PROVEN',scope='Read-only exact mapped graph; no constructor, synthesis or simulation',source_sha256=hashlib.sha256(a['s'].encode()).hexdigest(),netlist=str(netlist),rows=rows,global_notes=['ot_rst_pipe has unreset stages: regional reset low cannot be assumed at edge 1; parent must derive its actual first assertion.','First-state graph paths include gate conditions but do not prove sensitivity or reset masking.','No independent initial Q equality assumed.'])
out=Path('/home/ubuntu/artifacts/d2d-first-authority-1019/consumer_partition.json');out.write_text(json.dumps(result,indent=2)+'\n')
for r in rows:print(r['root'],r['transparent_logical_endpoint_count'],r['first_state_or_output_count'],r['unreset_first_state_count'],r['first_state_summary'])
