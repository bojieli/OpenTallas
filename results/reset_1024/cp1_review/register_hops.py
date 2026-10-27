import odb,os,json,collections
p=os.environ['ODB'];db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def seq(i):return 'DFF' in i.getMaster().getName().upper()
def xy(i):x,y=i.getLocation();m=i.getMaster();return ((x+m.getWidth()/2)/u,(y+m.getHeight()/2)/u)
cache={};visiting=set()
def sources(n):
 if n is None:return frozenset()
 key=n.getId()
 if key in cache:return cache[key]
 if key in visiting:return frozenset()
 visiting.add(key);out=set()
 if str(n.getSigType()) not in {'POWER','GROUND','CLOCK'}:
  for it in n.getITerms():
   if str(it.getIoType())!='OUTPUT':continue
   i=it.getInst()
   if seq(i):out.add(i.getName())
   else:
    for ip in i.getITerms():
     if str(ip.getIoType())=='INPUT':out.update(sources(ip.getNet()))
 visiting.remove(key);cache[key]=frozenset(out);return cache[key]
regs={i.getName():i for i in b.getInsts() if seq(i)}
hops=[];missing=[]
for name,i in regs.items():
 for pin in i.getITerms():
  if pin.getMTerm().getName()!='D':continue
  for src in sources(pin.getNet()):
   pa,pc=xy(regs[src]),xy(i);d=abs(pa[0]-pc[0])+abs(pa[1]-pc[1]);hops.append([d,src,name,pa,pc])
hops.sort(reverse=True)
r=dict(scope='placed sequential D-to-Q dependencies, tracing through combinational cells and buffers; reset/control D paths included',pairs=len(hops),max_um=hops[0][0] if hops else None,over405=sum(h[0]>405 for h in hops),worst=hops[:20],registers=len(regs),odb=p)
json.dump(r,open(os.environ['OUT'],'w'),indent=2);print('REGISTER_HOPS',r['registers'],r['pairs'],'max',r['max_um'],'over405',r['over405'])
