"""Opt-in cold final-seed preparation before DRT initialization.

Run with OpenROAD's Python bindings:
  openroad -exit -python prd_filler_preclean.py SOURCE.odb NEW.odb MANIFEST.json

Use an immutable source, preferably mounted read-only. A separate OpenDB database
avoids the DRT callbacks that make final-seed filler removal slow after pin access.
Only typed filler instances whose connected pins are POWER/GROUND are removed.
Nonfiller placements, ports, signal/clock connectivity and exact wire opcode/data
streams must match before/after. Require the successful manifest and output hash
before adopting a derived seed. Ordinary refill, PG, timing, clock, DRC/DRV and
routed equivalence gates remain required. No production path calls this by default.
"""
import collections,hashlib,json,resource,struct,sys,time
from pathlib import Path
import odb
source,dest,manifest=map(Path,sys.argv[1:4])
if len({source.resolve(),dest.resolve(),manifest.resolve()})!=3 or dest.exists() or manifest.exists():raise RuntimeError('refuse input/output alias or existing output')
if not hasattr(odb.dbMaster,'isFiller'):raise RuntimeError('typed filler API required')
destroy=getattr(odb.dbInst,'destroy',None) or getattr(odb,'dbInst_destroy',None)
if destroy is None:raise RuntimeError('dbInst destroy API required')
PG={'POWER','GROUND'}
def sha_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def digest(records):
 h=hashlib.sha256()
 for r in sorted(records):h.update(json.dumps(r,separators=(',',':')).encode()+b'\n')
 return h.hexdigest()
def fingerprint(block):
 insts=[]
 for i in block.getInsts():
  m=i.getMaster()
  if not m.isFiller():insts.append((i.getName(),m.getName(),tuple(i.getOrigin()),str(i.getOrient()),str(i.getPlacementStatus())))
 ports=[]
 for bt in block.getBTerms():
  boxes=[]
  for bp in bt.getBPins():
   for bx in bp.getBoxes():
    layer=bx.getTechLayer();boxes.append((layer.getName() if layer is not None else '',bx.xMin(),bx.yMin(),bx.xMax(),bx.yMax()))
  n=bt.getNet();ports.append((bt.getName(),str(bt.getIoType()),str(bt.getSigType()),n.getName() if n is not None else '',tuple(sorted(boxes))))
 nets=[];clocks=[];wire_ops=0
 for n in block.getNets():
  sig=str(n.getSigType())
  if sig in PG:continue
  pins=sorted((it.getInst().getName(),it.getMTerm().getName()) for it in n.getITerms())
  bterms=sorted(bt.getName() for bt in n.getBTerms());w=n.getWire();wh=hashlib.sha256();length=0
  if w is not None:
   length=w.length();wire_ops+=length
   for k in range(length):
    op=w.getOpcode(k);op=ord(op) if isinstance(op,(str,bytes)) else int(op)
    wh.update(struct.pack('<II',op&255,int(w.getData(k))&0xffffffff))
  r=(n.getName(),sig,tuple(pins),tuple(bterms),length,wh.hexdigest());nets.append(r)
  if sig=='CLOCK':clocks.append(r)
 return {'nonfiller_instances':len(insts),'nonfiller_placement_sha256':digest(insts),'ports':len(ports),'ports_sha256':digest(ports),'nonpg_nets':len(nets),'nonpg_net_connectivity_and_exact_wire_sha256':digest(nets),'clock_nets':len(clocks),'clock_connectivity_and_exact_wire_sha256':digest(clocks),'wire_ops':wire_ops}
t0=time.perf_counter();result={'schema':'opentallas.prd_filler_preclean.v1','source':str(source),'output':str(dest),'mechanism':'separate odb.dbDatabase; no ord-managed STA/DRT database','source_sha256':sha_file(source),'timings':{}}
t=time.perf_counter();db=odb.dbDatabase.create();odb.read_db(db,str(source));block=db.getChip().getBlock();result['timings']['read_s']=time.perf_counter()-t
result['instances_before']=len(block.getInsts());selected=[];masters=collections.Counter();removed_names=hashlib.sha256()
t=time.perf_counter()
for seen,inst in enumerate(block.getInsts(),1):
 master=inst.getMaster()
 if master.isFiller():
  for term in inst.getITerms():
   net=term.getNet()
   if net is not None and str(net.getSigType()) not in PG:raise RuntimeError('refuse filler connected to non-PG net: '+inst.getName()+' '+net.getName())
  selected.append(inst);masters[master.getName()]+=1;removed_names.update(inst.getName().encode()+b'\n')
 if seen%500000==0:print(json.dumps({'phase':'select','seen':seen,'typed_pg_only_fillers':len(selected)}),flush=True)
result['timings']['selection_s']=time.perf_counter()-t
if not selected:raise RuntimeError('refuse empty preclean')
print(json.dumps({'phase':'fingerprint_before','selected':len(selected)}),flush=True)
t=time.perf_counter();before=fingerprint(block);result['timings']['fingerprint_before_s']=time.perf_counter()-t
print(json.dumps({'phase':'delete','selected':len(selected)}),flush=True)
t=time.perf_counter()
for done,inst in enumerate(selected,1):
 destroy(inst)
 if done%500000==0:print(json.dumps({'phase':'delete','deleted':done}),flush=True)
result['timings']['delete_s']=time.perf_counter()-t
result['instances_after']=len(block.getInsts());result['removed']=len(selected);result['removed_by_master']=dict(masters);result['removed_names_sha256']=removed_names.hexdigest()
assert result['instances_before']-result['instances_after']==len(selected)
print(json.dumps({'phase':'fingerprint_after','remaining':result['instances_after']}),flush=True)
t=time.perf_counter();after=fingerprint(block);result['timings']['fingerprint_after_s']=time.perf_counter()-t
if before!=after:raise RuntimeError('refuse changed nonfiller placement, ports, signal/clock connectivity or exact wires')
result['preserved']=before;result['preservation_match']=True
print(json.dumps({'phase':'write','preservation_match':True}),flush=True)
t=time.perf_counter();odb.write_db(db,str(dest));result['timings']['write_s']=time.perf_counter()-t
result.update(status='DERIVED_FINAL_SEED_READY_NOT_ADOPTED',output_sha256=sha_file(dest),output_bytes=dest.stat().st_size,peak_rss_kb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,total_s=time.perf_counter()-t0)
manifest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
