"""Read immutable synth ODB only. Run with OpenROAD -python on the fleet."""
import odb,sys,json,gzip,hashlib,collections,re,os
path,out=sys.argv[1:3]; db=odb.dbDatabase.create();odb.read_db(db,path);b=db.getChip().getBlock()
nets={n.getName():n for n in b.getNets()};parent={n:n for n in nets}
def find(n):
 while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
 return n
def union(a,c):
 a,c=find(a),find(c)
 if a!=c:parent[c]=a
cells={}; ff=set(); transparent=set();drivers=collections.defaultdict(list);loads=collections.defaultdict(list)
for i in b.getInsts():
 name=i.getName();master=i.getMaster().getName();pins={p.getMTerm().getName():(p.getNet().getName() if p.getNet() else None,str(p.getIoType())) for p in i.getITerms()};cells[name]={'master':master,'pins':pins}
 if 'DFF' in master.upper():ff.add(name)
 ins=[v[0] for v in pins.values() if v[1]=='INPUT' and v[0]];outs=[v[0] for v in pins.values() if v[1]=='OUTPUT' and v[0]]
 if re.match(r'^(?:BUF|INV)',master) and len(ins)==len(outs)==1:transparent.add(name);union(ins[0],outs[0])
 for p,(n,d) in pins.items():
  if n:(drivers if d=='OUTPUT' else loads)[n].append((name,p))
for p in b.getBTerms():
 n=p.getNet()
 if n:(drivers if str(p.getIoType())=='INPUT' else loads)[n.getName()].append(('@PORT',p.getName()))
endpoints=collections.defaultdict(list);sources=collections.defaultdict(list)
for n in nets:
 for i,p in loads[n]:
  if i not in transparent:endpoints[find(n)].append([i,p])
 for i,p in drivers[n]:
  if i not in transparent:sources[find(n)].append([i,p])
def role(i,p,n):
 if i=='@PORT':return 'top_clock_input' if p in ('ck','hck') or 'hbm_data' in p else 'top_reset_input' if 'rst' in p else 'top_input'
 m=cells[i]['master']
 if i in ff:return 'FF'
 if re.match('TIE|LOGIC',m):return 'constant'
 if cells[i]['master'].startswith(('SRAM','ot_sram')):return 'macro'
 return 'comb_reset' if re.search('rst|reset',n,re.I) else 'comb'
rows=[]
for n in sorted(nets):
 r=find(n);ep=endpoints[r]
 for i,p in drivers[n]:rows.append({'net':n,'driver':[i,p], 'role':role(i,p,n),'transparent_intermediate':i in transparent,'direct_pins':len(loads[n]),'logical_pins':len(ep),'canonical':r})
roots=[{'canonical':r,'drivers':sources[r],'logical_pins':len(ep),'endpoints':ep} for r,ep in sorted(endpoints.items())]
# Every fixed BTerm retains its exact first sequential owners. Logic is followed;
# FF boundaries terminate walks; clocks and data pins remain separate records.
adj=collections.defaultdict(set);rev=collections.defaultdict(set)
for i,c in cells.items():
 if i in ff:continue
 ins=[n for n,d in c['pins'].values() if n and d=='INPUT'];outs=[n for n,d in c['pins'].values() if n and d=='OUTPUT']
 for a in ins:
  for z in outs:adj[a].add(z);rev[z].add(a)
def owners(start,forward):
 seen=set();todo=[start];owners=set();term=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  for i,p in (loads[n] if forward else drivers[n]):
   if i in ff:owners.add((i,p))
   elif i=='@PORT':term.add(p)
  todo.extend((adj if forward else rev)[n]-seen)
 return sorted(owners),sorted(term)
faces=[]
for p in b.getBTerms():
 if not p.getNet():continue
 direction=str(p.getIoType());o,t=owners(p.getNet().getName(),direction=='INPUT');faces.append({'port':p.getName(),'direction':direction,'first_FF_owners':o,'other_ports':t})
summary={'input_odb':path,'sha256':hashlib.sha256(open(path,'rb').read()).hexdigest(),'cells':len(cells),'FF':len(ff),'transparent_cells':len(transparent),'driver_records':len(rows),'canonical_components':len(roots),'logical_endpoint_pins':sum(len(x['endpoints']) for x in roots),'violating_drivers':sum(x['logical_pins']>32 for x in rows),'max_logical_pins':max(x['logical_pins'] for x in rows),'role_summary':{},'ports':len(faces),'multi_face_FF':None}
for role_name in sorted({x['role'] for x in rows}):
 rr=[x for x in rows if x['role']==role_name];summary['role_summary'][role_name]={'drivers':len(rr),'max':max(x['logical_pins'] for x in rr),'over32':sum(x['logical_pins']>32 for x in rr)}
os.makedirs(out,exist_ok=True)
for name,obj in [('drivers',rows),('roots',roots),('boundary',faces),('cells',cells)]:
 with gzip.open(out+'/'+name+'.json.gz','wt') as f:json.dump(obj,f)
json.dump(summary,open(out+'/summary.json','w'),indent=2);print(json.dumps(summary,indent=2))
