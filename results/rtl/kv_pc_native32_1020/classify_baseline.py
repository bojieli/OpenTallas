import pathlib,json,sys,collections
p=pathlib.Path.cwd();sys.path.insert(0,str(p/'tools'));import textbook_lint as TL
r=json.loads((p/'native_census.json').read_text());mods=TL.parse_verilog(pathlib.Path(r['netlist']['path'].replace('/work/',str(p.parent/'routes/gate/work/orfs')+'/')).read_text());g,t=TL.flatten(mods,'qkd_kvs_pc');rows=[]
for v in sorted(r['violations'],key=lambda x:x['loads'],reverse=True):
 e=[]
 for ci,pn,idx in v['endpoints']:
  if isinstance(ci,int):
   ty,nm,pins=g.cells[ci];outs={k:[g.net_name[g.find(x)] for x in val] for k,val in pins.items()if k in ('Q','QN','Y')};e.append(dict(instance=nm,master=ty,pin=pn,outputs=outs))
 rows.append(dict(driver=v['driver'],net=v['net'],loads=v['loads'],endpoints=e))
uses=collections.defaultdict(list)
for ci,(ty,nm,pins) in enumerate(g.cells):
 for pn,ns in pins.items():
  if pn not in ('Q','QN','Y'):
   for n in ns:uses[g.find(n)].append(ci)
for row in rows:
 seen=set();q=[(g.find(g.net_id[row['net']]),0)];ffs=[]
 while q and len(seen)<20000:
  net,depth=q.pop()
  for ci in uses[net]:
   if ci in seen:continue
   seen.add(ci);ty,nm,pins=g.cells[ci]
   if ty.startswith(('DFF','SDFF','SDF')):ffs.append(nm)
   elif depth<4:
    for pn,ns in pins.items():
     if pn=='Y':q.extend((g.find(n),depth+1) for n in ns)
 row['affected_sequential_families']=dict(collections.Counter(__import__('re').sub(r'\[[^\]]+\]|__qv.*|\$_.*','',n) for n in ffs))
 row['affected_sequential_examples']=ffs[:8]
(p/'classified_roots.json').write_text(json.dumps(rows,indent=1)+'\n');print('CLASSIFIED',len(rows),flush=True)
