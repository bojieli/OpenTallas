#!/usr/bin/env python3
"""Actual frozen mapped ODB all-driver census, following only INV/BUF transparent cells."""
import odb,sys,json,hashlib,re
p,out=sys.argv[1:];db=odb.dbDatabase.create();odb.read_db(db,p);b=db.getChip().getBlock()
def trans(i):
 m=i.getMaster().getName().upper()
 return ('INV' in m or 'BUF' in m) and not any(x in m for x in ['TIE','DFF'])
def loads(net,visited=None):
 visited=set() if visited is None else visited
 if net.getName() in visited:return []
 visited=visited|{net.getName()};r=[]
 for t in net.getITerms():
  if str(t.getIoType())!='INPUT':continue
  if t.getMTerm().getName().upper() in ['CLK','CK','CP']:continue
  inst=t.getInst()
  if trans(inst):
   for q in inst.getITerms():
    if str(q.getIoType())=='OUTPUT' and q.getNet():r+=loads(q.getNet(),visited)
  else:r.append(inst.getName()+'/'+t.getMTerm().getName())
 return sorted(set(r))
a=[];ties=[];clock_loads=[]
for net in b.getNets():
 sinks=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in net.getITerms() if str(t.getIoType())=='INPUT' and t.getMTerm().getName().upper() in ['CLK','CK','CP']]
 if sinks:clock_loads.append(dict(net=net.getName(),loads=len(sinks),sinks=sinks))
for net in b.getNets():
 if str(net.getSigType()) in ['POWER','GROUND','CLOCK']:continue
 ds=[t for t in net.getITerms() if str(t.getIoType())=='OUTPUT']
 ps=list(net.getBTerms())
 if not ds and not any(str(p.getIoType())=='INPUT' for p in ps):continue
 if ds and all(trans(t.getInst()) for t in ds):continue # count at true driver, across transparent cone
 sinks=loads(net)
 if not sinks:continue
 rec=dict(net=net.getName(),driver=[t.getInst().getName()+'/'+t.getMTerm().getName() for t in ds] or [p.getName() for p in ps],masters=[t.getInst().getMaster().getName() for t in ds],loads=len(sinks),sinks=sinks)
 (ties if any('TIE' in x.upper() for x in rec['masters']) else a).append(rec)
a.sort(key=lambda x:-x['loads'])
r=dict(schema='opentallas.dcal-bc3safe-source-census.v1',odb_sha256=hashlib.sha256(open(p,'rb').read()).hexdigest(),clock_loads=clock_loads,ff_count=sum('DFF' in i.getMaster().getName() for i in b.getInsts()),functional_source_over32=[x for x in a if x['loads']>32],functional_max_load=max(x['loads'] for x in a),static_ties=ties,all_sources=a)
open(out,'w').write(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['all_sources','static_ties','clock_loads']},indent=2))
