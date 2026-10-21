import odb,json,gzip,hashlib,collections,os
P='/frozen/5_1_grt.odb'; O='/out'
assert hashlib.sha256(open(P,'rb').read()).hexdigest()=='00150f2fb15c550a1b5996031874102edfd5bbd677c98aef31bd87b9b3c38ad2'
db=odb.dbDatabase.create();odb.read_db(db,P);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def pg(p):return p.getSigType() in ('POWER','GROUND')
def ident(p):return p.getInst().getName()+'/'+p.getMTerm().getName() if hasattr(p,'getInst') else 'PORT/'+p.getName()
def tr(i):return i.getMaster().getName().startswith(('BUF','INV'))
def role(p):
 if not hasattr(p,'getInst'):return 'input'
 m=p.getInst().getMaster();n=m.getName();return 'ff' if n.startswith('DFF') else 'tie' if n.startswith('TIE') else 'macro' if m.isBlock() else 'comb'
nets={};drivers=[];masters={}
for i in b.getInsts():
 m=i.getMaster();masters[m.getName()]={'area_um2':m.getWidth()*m.getHeight()/u/u,'pins':{t.getName():[t.getIoType(),t.getSigType()] for t in m.getMTerms()}}
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'):continue
 ds=[p for p in n.getITerms() if not pg(p) and p.getIoType()=='OUTPUT']+[p for p in n.getBTerms() if p.getIoType()=='INPUT']
 ss=[p for p in n.getITerms() if not pg(p) and p.getIoType()=='INPUT']+[p for p in n.getBTerms() if p.getIoType()=='OUTPUT'];nets[n.getId()]=ss
 for p in ds:
  if hasattr(p,'getInst') and tr(p.getInst()):continue
  if n.getSigType()=='CLOCK' or ident(p)=='PORT/ck':continue
  drivers.append(p)
records=[]
for p in drivers:
 es=[];stack=[(p.getNet(),0)];seen={}
 while stack:
  n,inv=stack.pop()
  if n is None:continue
  if n.getId() in seen:assert seen[n.getId()]==inv;continue
  seen[n.getId()]=inv
  for s in nets.get(n.getId(),[]):
   if hasattr(s,'getInst') and tr(s.getInst()):
    ii=s.getInst();v=inv^int(ii.getMaster().getName().startswith('INV'))
    stack.extend((t.getNet(),v) for t in ii.getITerms() if not pg(t) and t.getIoType()=='OUTPUT')
   else:es.append({'pin':ident(s),'inverted':inv})
 records.append({'driver':ident(p),'role':role(p),'master':p.getInst().getMaster().getName() if hasattr(p,'getInst') else None,'endpoints':es})
out={'odb_sha256':hashlib.sha256(open(P,'rb').read()).hexdigest(),'records':records,'masters':masters}
with gzip.open(O+'/graph.json.gz','wt') as f:json.dump(out,f,separators=(',',':'))
print(json.dumps({'roots':len(records),'endpoints':sum(len(r['endpoints']) for r in records),'masters':len(masters),'odb_sha256':out['odb_sha256']}))
