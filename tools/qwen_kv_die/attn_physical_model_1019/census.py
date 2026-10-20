import pathlib,importlib.util,json,collections,hashlib,re
r=pathlib.Path('.')
s=importlib.util.spec_from_file_location('T',r/'tools/textbook_lint.py');T=importlib.util.module_from_spec(s);s.loader.exec_module(T)
p=next((r/'synth/results/asap7').glob('*/base/1_2_yosys.v'));g,top=T.flatten(T.parse_verilog(p.read_text()),None);A=T.build(g,None)
fp=json.loads((r/'src/physical/ref_tile/qkd_kvs_attn_ba4/floorplan.json').read_text());faces={p:f for f,ps in fp['pins'].items() for p in ps}
rows=[];facecounts=collections.Counter();owners=collections.defaultdict(list)
def frontier(x,direction):
 todo=[x];seen=set();ends=set()
 while todo:
  z=todo.pop()
  if z in seen:continue
  seen.add(z)
  if z<4:ends.add(('constant',str(z),'constant'));continue
  if direction=='output':
   ci,pin=A['driver'].get(z,(-2,'missing'))
   if ci>=0 and A['kind'][ci]=='buf':todo.extend(v for pn,bs in g.cells[ci][2].items() if A['pin_dir'][ci][pn]=='in' for v in bs)
   else:ends.add((A['kind'][ci] if ci>=0 else 'port',g.cells[ci][1] if ci>=0 else pin,pin))
  else:
   for ci,pin,bit in A['loads'].get(z,[]):
    if A['kind'][ci]=='buf':todo.extend(v for pn,bs in g.cells[ci][2].items() if A['pin_dir'][ci][pn]=='out' for v in bs)
    else:ends.add((A['kind'][ci],g.cells[ci][1],pin))
 return sorted(ends)
for port,(direction,x) in g.ports.items():
 base=port.split('[')[0];face=faces.get(base,'UNASSIGNED');facecounts[face]+=1
 ends=frontier(x,direction);rows.append({'port':port,'direction':direction,'face':face,'ends':ends})
 for kind,n,pin in ends:
  if kind=='ff' and pin not in T.SEQ_CLK_PINS and pin not in T.ASYNC_PINS:owners[n].append({'port':port,'face':face,'direction':direction,'pin':pin})
result={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'top':top,'cells':len(g.cells),'FF':A['kind'].count('ff'),'face_counts':dict(facecounts),'boundary_kind_counts':dict(collections.Counter(k for row in rows for k,n,pin in row['ends'])),'distinct_boundary_FF':len(owners),'shared_boundary_FF':{n:v for n,v in owners.items() if len(v)>1},'cross_face_FF':{n:v for n,v in owners.items() if len({z['face'] for z in v})>1},'ports':rows}
(r/'census.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ('ports','shared_boundary_FF','cross_face_FF')}));print('shared',len(result['shared_boundary_FF']),'cross_face',len(result['cross_face_FF']))

allroots=[]
for x in sorted(set(A['loads'])|set(A['driver'])):
 ci,pn=A['driver'].get(x,(-3,'constant' if x<4 else 'undriven'))
 kind=A['kind'][ci] if ci>=0 else 'constant' if x<4 else 'top_input' if ci==-1 else 'undriven'
 if kind=='buf':continue
 todo=[x];seen=set();ends=set()
 while todo:
  z=todo.pop()
  if z in seen:continue
  seen.add(z)
  for li,lp,bit in A['loads'].get(z,[]):
   if A['kind'][li]=='buf':todo.extend(v for op,bs in g.cells[li][2].items() if A['pin_dir'][li][op]=='out' for v in bs)
   else:ends.add((li,lp,bit))
 sinks=[]
 for li,lp,bit in sorted(ends):
  role='clock' if lp in T.SEQ_CLK_PINS else 'reset' if lp in T.ASYNC_PINS else 'FF_data' if A['kind'][li]=='ff' else 'macro' if A['kind'][li]=='macro' else 'comb'
  sinks.append({'instance':g.cells[li][1],'master':g.cells[li][0],'pin':lp,'role':role})
 role='clock' if x in {v for b,(dr,v) in g.ports.items() if b=='ck'} else 'reset' if sinks and all(z['role']=='reset' for z in sinks) else kind
 allroots.append({'net':g.net_name[x] if x>=4 else str(x),'source_instance':g.cells[ci][1] if ci>=0 else None,'source_master':g.cells[ci][0] if ci>=0 else None,'source_pin':pn,'source_kind':kind,'source_role':role,'direct_loads':len(A['loads'].get(x,[])),'logical_pin_loads':len(sinks),'distinct_FF':len({z['instance'] for z in sinks if z['role'] in ('FF_data','reset','clock')}),'sink_roles':dict(collections.Counter(z['role'] for z in sinks)),'sinks':sinks})
summary={'source_sha256':result['source_sha256'],'root_count':len(allroots),'kind_counts':dict(collections.Counter(z['source_kind'] for z in allroots)),'role_counts':dict(collections.Counter(z['source_role'] for z in allroots)),'above32_by_role':dict(collections.Counter(z['source_role'] for z in allroots if z['logical_pin_loads']>32)),'max_by_role':{role:max(z['logical_pin_loads'] for z in allroots if z['source_role']==role) for role in sorted({z['source_role'] for z in allroots})},'all_roots':allroots}
(r/'all_driver_census.json').write_text(json.dumps(summary));print(json.dumps({k:v for k,v in summary.items() if k!='all_roots'}))
