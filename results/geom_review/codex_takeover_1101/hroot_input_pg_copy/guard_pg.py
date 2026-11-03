import odb,json,hashlib
from pathlib import Path
P=Path('/work')
def read(path):
 d=odb.dbDatabase.create();odb.read_db(d,path);return d,d.getChip().getBlock()
a,A=read('/input/3_place.odb');b,B=read('/work/hroot_pg_bound.odb')
def flags(o):return tuple((n,str(getattr(o,n)()))for n in ['isDoNotTouch','isSpecial']if hasattr(o,n))
def cells(block):return {i.getName():(i.getMaster().getName(),i.getOrient(),tuple(i.getLocation()),str(i.getPlacementStatus()),flags(i))for i in block.getInsts()}
def net_inventory(block):return sorted((n.getName(),str(n.getSigType()),flags(n))for n in block.getNets())
def signals(block):
 z=[]
 for n in block.getNets():
  if str(n.getSigType())in['POWER','GROUND']:continue
  z.append((n.getName(),str(n.getSigType()),flags(n),sorted((i.getInst().getName(),i.getMTerm().getName())for i in n.getITerms()),sorted(t.getName()for t in n.getBTerms())))
 return hashlib.sha256(repr(sorted(z)).encode()).hexdigest()
def pins(block):
 z=[]
 for t in block.getBTerms():
  shapes=[]
  for p in t.getBPins():
   for q in p.getBoxes():shapes.append((q.getTechLayer().getName(),q.xMin(),q.yMin(),q.xMax(),q.yMax()))
  n=t.getNet();z.append((t.getName(),str(t.getIoType()),str(t.getSigType()),None if n is None else n.getName(),sorted(shapes)))
 return sorted(z)
def pg(block):
 out={}
 for i in block.getInsts():
  for t in i.getITerms():
   if str(t.getMTerm().getSigType())not in['POWER','GROUND']:continue
   n=t.getNet();out[(i.getName(),t.getMTerm().getName())]=''if n is None else n.getName()
 return out
err=[];c0,c1=cells(A),cells(B)
if c0!=c1:err.append('Instance/master/pose/orient/status/DNT changed')
if net_inventory(A)!=net_inventory(B):err.append('Net inventory/roles/flags changed')
g0,g1=signals(A),signals(B)
if g0!=g1:err.append('Full DATA/CLOCK incidence changed')
if pins(A)!=pins(B):err.append('BTerm interface/net/geometry changed')
p0,p1=pg(A),pg(B);expected={(r['instance'],r['pin']):r['expected_net']for r in json.load(open(P/'pg_before_repair.json'))['failures']};changed={k for k in p0 if p0[k]!=p1.get(k)}
if changed!=set(expected):err.append('Changed PG terminal set differs from exact existing opens')
for k in changed:
 if p0[k]!=''or p1[k]!=expected[k]:err.append('PG mutation outside unbound-to-existing-rule class')
result={'scope':'Guarded saved-copy existing-rule PG binding only; no native module/placement/STA','verdict':'PASS'if not err else'FAIL','errors':err,'instances':len(c0),'PG_changed_exact':len(changed),'DATA_CLOCK_before':g0,'DATA_CLOCK_after':g1,'protected_net_count':len(net_inventory(A))};(P/'pg_scope_guard.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not err
