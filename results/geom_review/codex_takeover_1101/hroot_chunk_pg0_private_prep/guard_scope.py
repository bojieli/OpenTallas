import odb,json,hashlib
from pathlib import Path
P=Path('/work')
def read(path):
 d=odb.dbDatabase.create();odb.read_db(d,path);return d,d.getChip().getBlock()
a,A=read('/input/hroot_pg_bound.odb');b,B=read('/work/3_place.odb')
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
err=[];c0,c1=cells(A),cells(B);names=set(json.load(open(P/'mobile_names.json')));clean=lambda n:n.replace(chr(92),'')
if len(names)!=4609:err.append('Expected4609exactmobile names')
if set(c0)!=set(c1):err.append('Instance inventory changed')
mobile={n for n in c0 if clean(n)in names}
if len(mobile)!=4609:err.append('Actual mobile membership differs')
changed=0
for n,v in c0.items():
 w=c1.get(n)
 if w is None:continue
 if n in mobile:
  if (v[0],v[3:])!=(w[0],w[3:]):err.append('Mobile master/status/flags changed:'+n)
  changed+=v[1:3]!=w[1:3]
 elif v!=w:err.append('Protected instance changed:'+n)
if net_inventory(A)!=net_inventory(B):err.append('Net inventory/roles/flags changed')
g0,g1=signals(A),signals(B)
if g0!=g1:err.append('Full DATA/CLOCK incidence changed')
if pins(A)!=pins(B):err.append('BTerm interface/net/geometry changed')
p0,p1=pg(A),pg(B)
if p0!=p1:err.append('PG terminal binding changed')
result={'scope':'Private bothmodesOFF/no-birth same-source4609COMB pose-only continuation; no reach/clock/route waiver','verdict':'PASS'if not err else'FAIL','errors':err[:30],'total_errors':len(err),'instances':len(c0),'mobile_exact':len(mobile),'mobile_pose_changed':changed,'DATA_CLOCK_before':g0,'DATA_CLOCK_after':g1,'PG_terminal_count':len(p0)}
(P/'full_scope_guard.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not err
