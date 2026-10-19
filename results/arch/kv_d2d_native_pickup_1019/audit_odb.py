import odb,json,os,collections,hashlib
p=os.environ['ODB']; db=odb.dbDatabase.create(); odb.read_db(db,p); b=db.getChip().getBlock(); rows=[]; macros={};hist=collections.Counter(); functional=set()
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'): continue
 its=list(n.getITerms()); drivers=[];loads=[]
 for t in its:
  i=t.getInst();m=i.getMaster();functional.add(i.getName())
  if m.getType()=='BLOCK':
   macros[i.getName()]={'master':m.getName(),'origin':i.getOrigin(),'orient':i.getOrient(),'width':m.getWidth(),'height':m.getHeight(),'pins':len(list(m.getMTerms()))}
  d=t.getIoType()
  if d=='OUTPUT': drivers.append([i.getName(),m.getName(),t.getMTerm().getName()])
  elif d=='INPUT': loads.append([i.getName(),m.getName(),t.getMTerm().getName()])
 hist[len(loads)]+=1
 if len(loads)>32 and n.getSigType()!='CLOCK':rows.append({'net':n.getName(),'sinks':len(loads),'drivers':drivers,'sample_loads':loads[:8]})
rows.sort(key=lambda x:-x['sinks'])
print(json.dumps({'odb':p,'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'dbu':b.getDbUnitsPerMicron(),'functional_instances':len(functional),'macros':macros,'nonclock_over32':rows,'histogram':hist},indent=2))
