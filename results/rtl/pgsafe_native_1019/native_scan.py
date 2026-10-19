import odb, json, re, sys, hashlib, collections
db=odb.dbDatabase.create(); odb.read_db(db,sys.argv[1]); b=db.getChip().getBlock(); u=b.getDbUnitsPerMicron()
inst={i.getName():i for i in b.getInsts()}
def kind(i):
 t=i.getMaster().getName()
 return 'ff' if re.match(r'(DFF|SDFF)',t) else 'buf' if re.match(r'(BUF|INV)',t) else 'tie' if re.match(r'(TIE)',t) else 'macro' if i.getMaster().isBlock() else 'comb'
def xy(t):
 if hasattr(t,'getAvgXY'):
  z=t.getAvgXY()
  if z[0]: return (z[1]/u,z[2]/u)
 if hasattr(t,'getInst'):
  z=t.getInst().getBBox(); return ((z.xMin()+z.xMax())/(2*u),(z.yMin()+z.yMax())/(2*u))
 z=t.getFirstPinLocation(); return (z[1]/u,z[2]/u) if z[0] else None
def label(t): return t.getInst().getName()+'/'+t.getMTerm().getName() if hasattr(t,'getInst') else 'PORT '+t.getName()
def port(t): return not hasattr(t,'getInst')
def out(t): return str(t.getIoType())=='OUTPUT' if not port(t) else str(t.getIoType())=='INPUT'
def clock(t): return str(t.getSigType())=='CLOCK' if port(t) else str(t.getMTerm().getSigType())=='CLOCK' or t.getMTerm().getName() in ('CLK','CK','CP')
def k(t): return 'port' if port(t) else kind(t.getInst())
nets={}; drivers=[]; disconnected=[]
for n in b.getNets():
 ts=list(n.getITerms())+list(n.getBTerms()); ds=[t for t in ts if out(t)]; ls=[t for t in ts if not out(t)]
 nets[n.getName()]=(ds,ls)
 for d in ds:
  if k(d)!='buf' and not clock(d): drivers.append(d)
def loads(d,transparent=True):
 todo=[d.getNet()]; seen=set(); result={}
 while todo:
  n=todo.pop()
  if n is None or n.getName() in seen: continue
  seen.add(n.getName())
  for t in nets[n.getName()][1]:
   if not port(t) and k(t)=='buf' and transparent:
    todo += [x.getNet() for x in t.getInst().getITerms() if out(x)]
   else: result[label(t)]=t
 return list(result.values())
rows=[]; inputs=[]; outputs=[]; clockroots=[]
for d in drivers:
 ls=loads(d)
 if ls and all(clock(t) for t in ls): clockroots.append({'root':label(d),'loads':len(ls)}); continue
 r={'root':label(d),'kind':k(d),'loads':len(ls),'sink_roles':dict(collections.Counter(('port_out' if port(t) else k(t)+':'+t.getMTerm().getName()) for t in ls)), 'examples':[label(t) for t in ls[:5]]}
 rows.append(r)
 if port(d): inputs.append({**r,'registered':all(not port(t) and k(t)=='ff' and t.getMTerm().getName() in ('D','RESETN','SETN') for t in ls),'unused':not ls})
for t in b.getBTerms():
 if str(t.getIoType())!='OUTPUT': continue
 todo=[t.getNet()]; seen=set(); ds=[]
 while todo:
  n=todo.pop()
  if n is None or n.getName() in seen: continue
  seen.add(n.getName())
  for d in nets[n.getName()][0]:
   if not port(d) and k(d)=='buf': todo += [p.getNet() for p in d.getInst().getITerms() if not out(p)]
   else: ds.append(d)
 outputs.append({'pin':t.getName(),'drivers':[label(d) for d in ds],'roles':[k(d) for d in ds],'registered':bool(ds) and all(k(d)=='ff' for d in ds)})
# Sum Manhattan cell-centre wire spans through the complete combinational stage.
# This conservative placed-stage bound includes the actual native endpoint cells.
reach=[]
for d in drivers:
 if k(d) not in ('port','ff','macro'): continue
 p=xy(d)
 if p is None: continue
 todo=[(d.getNet(),p,0.,frozenset())]; worst=(0,None)
 while todo:
  n,p0,dist,seen=todo.pop()
  if n is None or n.getName() in seen: continue
  seen=seen|{n.getName()}
  for t in nets[n.getName()][1]:
   if clock(t): continue
   q=xy(t)
   if q is None: continue
   dd=dist+abs(q[0]-p0[0])+abs(q[1]-p0[1])
   if port(t) or k(t) in ('ff','macro'):
    if dd>worst[0]: worst=(dd,label(t))
   else:
    for z in t.getInst().getITerms():
     if out(z): todo.append((z.getNet(),q,dd,seen))
 if worst[1]: reach.append({'root':label(d),'um':round(worst[0],6),'sink':worst[1]})
raw={'odb_sha256':hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),'dbu_per_um':u,'die':[b.getDieArea().xMin()/u,b.getDieArea().yMin()/u,b.getDieArea().xMax()/u,b.getDieArea().yMax()/u], 'cells':[], 'ports':[], 'nets':[]}
for i in inst.values():
 raw['cells'].append({'name':i.getName(),'master':i.getMaster().getName(),'type':str(i.getMaster().getType()),'orientation':str(i.getOrient()),'placement_status':str(i.getPlacementStatus()),'bbox':[i.getBBox().xMin()/u,i.getBBox().yMin()/u,i.getBBox().xMax()/u,i.getBBox().yMax()/u], 'pins':[{'name':t.getMTerm().getName(),'direction':str(t.getIoType()),'sigtype':str(t.getMTerm().getSigType()),'net':t.getNet().getName() if t.getNet() else None,'xy':xy(t)} for t in i.getITerms()]})
for t in b.getBTerms(): raw['ports'].append({'name':t.getName(),'direction':str(t.getIoType()),'sigtype':str(t.getSigType()),'net':t.getNet().getName() if t.getNet() else None,'xy':xy(t)})
for n in b.getNets(): raw['nets'].append({'name':n.getName(),'sigtype':str(n.getSigType()),'pins':[label(t) for t in n.getITerms()]+[label(t) for t in n.getBTerms()]})
json.dump(raw,open(sys.argv[2]+'.raw.json','w'),separators=(',',':'))
rows.sort(key=lambda r:-r['loads']); reach.sort(key=lambda r:-r['um'])
direct=[]
for n,(ds,ls) in nets.items():
 for d in ds:
  if clock(d) or (ls and all(clock(t) for t in ls)): continue
  p=xy(d)
  if p is None: continue
  for t in ls:
   q=xy(t)
   if q is not None: direct.append({'net':n,'root':label(d),'sink':label(t),'um':round(abs(q[0]-p[0])+abs(q[1]-p[1]),6)})
direct.sort(key=lambda x:-x['um'])
r={'odb':sys.argv[1],'odb_sha256':hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest(),'cell_roles':dict(collections.Counter(kind(i) for i in inst.values())), 'clock_roots':clockroots,'placed_cells':[[i.getName(),i.getMaster().getName(),i.getLocation()[0]/u,i.getLocation()[1]/u,i.getMaster().getWidth()/u,i.getMaster().getHeight()/u] for i in inst.values()],'direct_wire_max':direct[:20],'direct_wire_over405':[x for x in direct if x['um']>405],'driver_count':len(rows),'maximum_all':rows[0] if rows else None,'over32':[r for r in rows if r['loads']>32], 'maximum_nonconstant':next((r for r in rows if r['kind']!='tie'),None),'inputs':inputs,'outputs':outputs,'reach_method':'complete combinational stage sum of Manhattan native cell-centre segments; cell pin offsets uncharged','reach_max':reach[:20], 'reach_over405':[r for r in reach if r['um']>405], 'rows':rows}
json.dump(r,open(sys.argv[2],'w'),indent=2)
print(json.dumps({key:r[key] for key in ('cell_roles','driver_count','maximum_all','maximum_nonconstant','reach_max')},indent=2)); print('OVER32',len(r['over32']),'REACH405',len(r['reach_over405']),'UNREG_INPUT',sum(not x['registered'] for x in inputs),'UNREG_OUTPUT',sum(not x['registered'] for x in outputs))
