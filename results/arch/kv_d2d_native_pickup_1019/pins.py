import odb,json,os,hashlib,collections
p=os.environ['ODB'];d=odb.dbDatabase.create();odb.read_db(d,p);b=d.getChip().getBlock(); names=set()
for n in b.getNets():
 if n.getSigType() in ('POWER','GROUND'):continue
 for t in n.getITerms():
  i=t.getInst()
  if i.getMaster().getType()=='BLOCK':names.add(i.getName())
res={}
for name in sorted(names):
 i=b.findInst(name); rec={'groups':{},'pg':[],'clock':[]}
 for t in i.getITerms():
  mt=t.getMTerm();n=t.getNet();pin=mt.getName();grp=pin.split('[')[0];g=rec['groups'].setdefault(grp,{'pins':0,'connected':0,'constant':0,'used_outputs':0,'rects':0,'minimum_rect_area_dbu2':None});g['pins']+=1;g['connected']+=int(n is not None)
  if n and mt.getSigType() not in ('POWER','GROUND'):
   ts=list(n.getITerms());g['constant']+=int(any(x.getIoType()=='OUTPUT' and 'TIE' in x.getInst().getMaster().getName() for x in ts));g['used_outputs']+=int(t.getIoType()=='OUTPUT' and (any(x.getIoType()=='INPUT' for x in ts) or bool(list(n.getBTerms()))))
  for mp in mt.getMPins():
   for bx in mp.getGeometry():
    g['rects']+=1
  if mt.getSigType() in ('POWER','GROUND'):rec['pg'].append({'pin':pin,'net':n.getName() if n else None})
  if pin=='clk':rec['clock'].append({'pin':pin,'net':n.getName() if n else None})
 res[name]=rec
print(json.dumps({'odb_sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'macros':res},indent=2))
