"""Extract complete data fanin/fanout endpoints of N59 movable station flops.
Read-only OpenDB geometry: no STA, CTS, placement or routing.
"""
import json,re,sys
from pathlib import Path
import odb

db=odb.dbDatabase.create(); odb.read_db(db,sys.argv[1]); b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
seq={i.getId():i for i in b.getInsts() if re.search(r'DFF|DHL|DLL|SDF',i.getMaster().getName())}
mac={i.getId():i for i in b.getInsts() if i.getMaster().isBlock()}
positions={};boxes=[]
def xy(box):return [(box.xMin()+box.xMax())/(2*u),(box.yMin()+box.yMax())/(2*u)]
for i in seq.values():positions[i.getName()]=xy(i.getBBox())
for i in mac.values():
 z=i.getBBox();boxes.append([z.xMin()/u,z.yMin()/u,z.xMax()/u,z.yMax()/u])
def endpoint(t):
 n=t.getInst().getName()+'/'+t.getMTerm().getName()
 if n not in positions:positions[n]=xy(t.getBBox())
 return n
back={};forward={}
def ends(net,rev,active=None):
 if net is None:return frozenset()
 cache=back if rev else forward;key=net.getId()
 if key in cache:return cache[key]
 active=set() if active is None else active
 if key in active:return frozenset()
 active.add(key);r=set()
 for t in net.getBTerms():
  if t.getIoType()==('INPUT' if rev else 'OUTPUT'):
   n='PORT:'+t.getName();positions[n]=xy(t.getBBox());r.add(n)
 for t in net.getITerms():
  if t.getSigType() in ('POWER','GROUND','CLOCK'):continue
  if t.getIoType()!=('OUTPUT' if rev else 'INPUT'):continue
  i=t.getInst();iid=i.getId()
  if iid in seq:r.add(i.getName());continue
  if iid in mac:r.add(endpoint(t));continue
  for t2 in i.getITerms():
   if t2.getSigType() in ('POWER','GROUND','CLOCK'):continue
   if t2.getMTerm().getName() in ('CLK','CK','CP'):continue
   if t2.getIoType()==('INPUT' if rev else 'OUTPUT'):r.update(ends(t2.getNet(),rev,active))
 active.remove(key);cache[key]=frozenset(r);return cache[key]
targets={}
for i in seq.values():
 n=i.getName()
 if not (re.search(r'(\.u_qb\.f_dd|\.u_svc\.dr_o|\.u_pd[13]_|\.u_qb\.f_lcv)',n) or '.g_w[4].g_stn.u_s1/' in n.replace('\\','')):continue
 d=i.findITerm('D')
 if d is None:continue
 sources=ends(d.getNet(),True);sinks=set()
 for t in i.getITerms():
  if t.getIoType()=='OUTPUT' and t.getSigType() not in ('POWER','GROUND','CLOCK'):sinks.update(ends(t.getNet(),False))
 targets[n]={'src':sorted(sources),'dst':sorted(sinks)}
print('N59_CONES',len(targets),'targets',sum(len(x['src'])+len(x['dst']) for x in targets.values()),'endpoint edges')
Path(sys.argv[2]).write_text(json.dumps(dict(positions=positions,macros=boxes,targets=targets)))
