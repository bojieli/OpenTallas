import odb,sys,statistics as st
db=odb.read_db(odb.dbDatabase.create(),sys.argv[1]);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def loc(n):
  i=b.findInst(n)
  if i is None: i=b.findInst(n.replace('[','\\[').replace(']','\\]'))
  if i is None: return None
  x,y=i.getLocation(); return x/u,y/u
def drvloc(netn):
  n=b.findNet(netn)
  for t in n.getITerms():
    if t.isOutputSignal():
      x,y=t.getInst().getLocation(); return x/u,y/u
d=[];dl=[];dc=[]
for l in open(sys.argv[2]):
  f=l.rstrip('\n').split('\t')
  a=loc(f[5].rsplit('/',1)[0]); c=loc(f[6].rsplit('/',1)[0])
  if a and c:
    d.append(abs(a[0]-c[0])+abs(a[1]-c[1]))
    la=drvloc(f[1]); lc=drvloc(f[2])
    dl.append(abs(la[0]-lc[0])+abs(la[1]-lc[1])); dc.append(abs(c[0]-la[0])+abs(c[1]-la[1]))
q=lambda v: "%.1f/%.1f/%.1f"%tuple(sorted(v)[int(len(v)*p)] for p in (0.1,0.5,0.9))
print("n",len(d),"launch-capture flop dist p10/50/90",q(d),"| leaf-driver dist",q(dl),"| capture to launch-leaf driver",q(dc))
