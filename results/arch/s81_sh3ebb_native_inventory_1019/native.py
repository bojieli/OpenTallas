import odb,json,hashlib,collections,math,gzip,os
P='/frozen/5_1_grt.odb'; OUT='/out'
db=odb.dbDatabase.create();odb.read_db(db,P);b=db.getChip().getBlock();U=b.getDbUnitsPerMicron()
def ident(p): return p.getInst().getName()+'/'+p.getMTerm().getName() if hasattr(p,'getInst') else 'PORT/'+p.getName()
def xy(p):
 if hasattr(p,'getInst'):
  v=p.getAvgXY();return [v[1]/U,v[2]/U] if v[0] else None
 boxes=[r for bp in p.getBPins() for r in bp.getBoxes()]
 return [(boxes[0].xMin()+boxes[0].xMax())/2/U,(boxes[0].yMin()+boxes[0].yMax())/2/U] if boxes else None
def typ(p):
 if not hasattr(p,'getInst'):return 'input'
 m=p.getInst().getMaster();n=m.getName()
 return 'FF' if n.startswith('DFF') else 'tie' if n.startswith('TIE') else 'macro' if m.isBlock() else 'comb'
def trans(i):return i.getMaster().getName().startswith(('BUF','INV'))
def pg(p):return p.getSigType() in ('POWER','GROUND')
nets={};drivers=[];clockroots=[];instances=collections.Counter();undriven=[];multi=[]
for i in b.getInsts():instances[i.getMaster().getName()]+=1
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'):continue
 ds=[p for p in n.getITerms() if not pg(p) and p.getIoType()=='OUTPUT']+[p for p in n.getBTerms() if p.getIoType()=='INPUT']
 ss=[p for p in n.getITerms() if not pg(p) and p.getIoType()=='INPUT']+[p for p in n.getBTerms() if p.getIoType()=='OUTPUT'];nets[n.getId()]=(ds,ss)
 if ss and not ds:undriven.append(n.getName())
 if len(ds)>1:multi.append(n.getName())
 for p in ds:
  if hasattr(p,'getInst') and trans(p.getInst()):continue
  if n.getSigType()=='CLOCK' or ident(p)=='PORT/ck':clockroots.append(p)
  else:drivers.append(p)
def endpoints(p):
 out=[];seen=set();stack=[p.getNet()]
 while stack:
  n=stack.pop()
  if n is None or n.getId() in seen:continue
  seen.add(n.getId())
  for s in nets.get(n.getId(),([],[]))[1]:
   if hasattr(s,'getInst') and trans(s.getInst()):stack.extend(t.getNet() for t in s.getInst().getITerms() if not pg(t) and t.getIoType()=='OUTPUT')
   else:out.append(s)
 return out
unsafe=[];far=[];inbad=[];outbad=[];maxima=collections.defaultdict(int);roles=collections.Counter();missingxy=[];allends=0;maxreach=0
with gzip.open(OUT+'/logical_roots.jsonl.gz','wt') as f:
 for p in drivers:
  es=endpoints(p);pos=xy(p);role=typ(p);roles[role]+=1;maxima[role]=max(maxima[role],len(es));allends+=len(es)
  row={'driver':ident(p),'role':role,'source_xy_um':pos,'loads':len(es),'endpoints':[]}
  if len(es)>32:unsafe.append({'driver':ident(p),'role':role,'loads':len(es),'master':p.getInst().getMaster().getName() if hasattr(p,'getInst') else None})
  for s in es:
   q=xy(s);r={'pin':ident(s),'role':typ(s),'xy_um':q,'distance_um':None}
   if pos is not None and q is not None:
    dist=abs(pos[0]-q[0])+abs(pos[1]-q[1]);r['distance_um']=dist;maxreach=max(maxreach,dist)
    if dist>405:far.append({'driver':ident(p),'sink':ident(s),'role':role,'distance_um':dist})
   else:missingxy.append([ident(p),ident(s)])
   if role=='input' and ident(p)!='PORT/rst_n' and typ(s)!='FF':inbad.append([ident(p),ident(s),typ(s)])
   if not hasattr(s,'getInst') and role!='FF':outbad.append([ident(s),ident(p),role])
   row['endpoints'].append(r)
  f.write(json.dumps(row)+'\n')
pgcounts=collections.Counter();pgviol=[];macro=[]
with gzip.open(OUT+'/all_pg_terminals.jsonl.gz','wt') as f:
 for i in b.getInsts():
  m=i.getMaster();mts=[t for t in m.getMTerms() if pg(t)]
  if not mts:pgcounts['masters_without_pg_instances']+=1
  for mt in mts:
   it=i.findITerm(mt.getName());n=it.getNet() if it else None;expected=mt.getSigType();actual=n.getSigType() if n else None
   state='MISSING_ITERM' if not it else 'UNBOUND' if not n else 'WRONG_SIGTYPE' if actual!=expected else 'CONNECTED'
   r={'instance':i.getName(),'master':m.getName(),'mterm':mt.getName(),'expected':expected,'net':n.getName() if n else None,'actual':actual,'status':state}
   f.write(json.dumps(r)+'\n');pgcounts[state]+=1
   if state!='CONNECTED':pgviol.append(r)
  if m.isBlock():
   pins=[]
   for mt in m.getMTerms():
    it=i.findITerm(mt.getName());rects=[{'layer':g.getTechLayer().getName(),'box_um':[g.xMin()/U,g.yMin()/U,g.xMax()/U,g.yMax()/U]} for mp in mt.getMPins() for g in mp.getGeometry() if g.getTechLayer()]
    pins.append({'name':mt.getName(),'signal_type':mt.getSigType(),'net':it.getNet().getName() if it and it.getNet() else None,'rects':rects})
   macro.append({'instance':i.getName(),'master':m.getName(),'origin_dbu':i.getOrigin(),'orient':i.getOrient(),'width_um':m.getWidth()/U,'height_um':m.getHeight()/U,'pins':pins})
box=b.getDieArea();summary={'scope':'Final GRT read-only native inventory; no STA or geometry-rule qualification','odb_sha256':hashlib.sha256(open(P,'rb').read()).hexdigest(),'dbu_per_um':U,'outline_um':[box.xMin()/U,box.yMin()/U,box.xMax()/U,box.yMax()/U],'instances':sum(instances.values()),'instance_masters':dict(instances),'roles':dict(roles),'max_loads':dict(maxima),'logical_endpoint_count':allends,'unsafe_count':len(unsafe),'unsafe_by_role':dict(collections.Counter(x['role'] for x in unsafe)),'far_pair_count':len(far),'max_source_pin_centroid_manhattan_um':maxreach,'missing_pin_centroid_pairs':len(missingxy),'input_nonff_count':len(inbad),'output_nonff_count':len(outbad),'undriven_nets':undriven,'multidriven_nets':multi,'pg':dict(pgcounts),'clock_roots':[{'driver':ident(p),'loads':len(endpoints(p))} for p in clockroots],'std_cell_area_um2':sum(i.getMaster().getWidth()*i.getMaster().getHeight()/U/U for i in b.getInsts() if not i.getMaster().isBlock())}
for name,data in [('summary',summary),('unsafe',unsafe),('far_pairs',far),('input_nonff',inbad),('output_nonff',outbad),('pg_violations',pgviol),('macros',macro),('missing_pin_centroids',missingxy)]:
 with open(OUT+'/'+name+'.json','x') as f:json.dump(data,f,indent=2)
print(json.dumps(summary,indent=2))
