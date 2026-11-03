import odb,json,re,hashlib
from pathlib import Path
P=Path('/work')
def read(n):
 d=odb.dbDatabase.create();odb.read_db(d,str(P/n));return d,d.getChip().getBlock()
a,A=read('input.odb');b,B=read('3_place.odb')
def flags(o):
 return tuple((n,str(getattr(o,n)()))for n in ['isDoNotTouch','isSpecial']if hasattr(o,n))
def cells(block):
 return {i.getName():(i.getMaster().getName(),i.getOrient(),tuple(i.getLocation()),str(i.getPlacementStatus()),flags(i))for i in block.getInsts()}
def graph(block):
 z=[]
 for n in block.getNets():
  z.append((n.getName(),str(n.getSigType()),flags(n),sorted((i.getInst().getName(),i.getMTerm().getName())for i in n.getITerms()),sorted(t.getName()for t in n.getBTerms())))
 return hashlib.sha256(repr(sorted(z)).encode()).hexdigest()
def pins(block):
 z=[]
 for t in block.getBTerms():
  shapes=[]
  for p in t.getBPins():
   for q in p.getBoxes():shapes.append((q.getTechLayer().getName(),q.xMin(),q.yMin(),q.xMax(),q.yMax()))
  z.append((t.getName(),str(t.getIoType()),str(t.getSigType()),sorted(shapes)))
 return sorted(z)
c0,c1=cells(A),cells(B);errors=[];moved=[];unrelated_ff=0
if set(c0)!=set(c1):errors.append('instance inventory changed')
for n,x in c0.items():
 if n not in c1:continue
 y=c1[n];target=bool(re.search(r'(^|[/.])u_cland_i_kvpc_Q_N_o_next[/.]',n));ff=bool(re.search(r'DFF|DHL|DLL|SDF',x[0]))
 if x[0]!=y[0] or x[4]!=y[4]:errors.append('master/DNT changed '+n)
 if ff and not target:
  unrelated_ff+=1
  if x!=y:errors.append('unrelated FF pose/status changed '+n)
 if x[1:3]!=y[1:3]:moved.append(n)
g0,g1=graph(A),graph(B)
if g0!=g1:errors.append('full CLK/DATA/PG incidence/net flags changed')
if pins(A)!=pins(B):errors.append('BTerm interface/geometry changed')
result={'scope':'HROOT FF-band PLACE only; no CTS/GRT/STA','verdict':'PASS'if not errors else'FAIL','errors':errors[:100],'instances':len(c0),'unrelated_ff_frozen':unrelated_ff,'moved_instances':len(moved),'graph_before':g0,'graph_after':g1,'max_live_variant':'sole codex-hroot-ff-place-2338; oldforeign jobs untouched'}
(P/'guard.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not errors
