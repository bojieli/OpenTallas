#!/usr/bin/env python3
"""Trace real storage D cones and a measured overloaded cut before redesign."""
import odb,json,re,os
from collections import defaultdict,Counter
from pathlib import Path
db=odb.dbDatabase.create();odb.read_db(db,os.environ['DVM_ODB']);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
def name(i):return i.getName().replace('\\','')
def seq(i):return bool(re.search('DFF|SDFF|LATCH',i.getMaster().getName()))
def storage(i):
 m=re.search(r'g_t\[([01])\].*g_bank\[([0-3])\].*g_e\[(\d+)\]',name(i))
 if m and seq(i):return int(m[1])*4+int(m[2])
 m=re.search(r'g_t\[([01])\].g_e\[(\d+)\]',name(i))
 return int(m[1])*4+int(m[2])//32 if m and seq(i) else None
roots=defaultdict(list)
for i in b.getInsts():
 k=storage(i)
 if k is not None:roots[k].append(i)
cones={};owner=defaultdict(set);objects={}
for k,rr in roots.items():
 seen=set();queue=list(rr);boundary=set()
 while queue:
  i=queue.pop();n=i.getName()
  if n in seen:continue
  if re.search('TIE(HI|LO)|TIE[01]|LOGIC[01]',i.getMaster().getName(),re.I):continue
  if seq(i) and storage(i)!=k:boundary.add(n);continue
  seen.add(n);owner[n].add(k);objects[n]=i
  for it in i.getITerms():
   mt=it.getMTerm()
   if mt.getIoType()!='INPUT' or mt.getSigType()=='CLOCK':continue
   if seq(i) and mt.getName().upper() not in ('D','DATA'):continue
   net=it.getNet()
   if net:queue.extend(d.getInst() for d in net.getITerms() if d.getMTerm().getIoType()=='OUTPUT')
 cones[k]=seen
readgroups={int(r.getName().rsplit('_',1)[1]):{i.getName() for i in r.getGroups()[0].getInsts()} for r in b.getRegions() if r.getName().startswith('dvm_local_bank_')}
rows=[]
for k,c in sorted(cones.items()):
 local={n for n in c if len(owner[n])==1};shared=c-local
 union=local|readgroups[k]
 area=sum(objects[n].getMaster().getWidth()*objects[n].getMaster().getHeight()/u**2 if n in objects else b.findInst(n).getMaster().getWidth()*b.findInst(n).getMaster().getHeight()/u**2 for n in union)
 rows.append(dict(bank=k,storage_flops=len(roots[k]),write_cone_cells=len(c),write_shared_cells=len(shared),write_unique_cells=len(local),combined_read_plus_unique_write_cells=len(union),combined_area_um2=area))
cut=float(os.environ.get('DVM_CUT_Y_UM','29.97'))*u;counts=Counter();examples=defaultdict(list)
for net in b.getNets():
 if net.getSigType() in ('POWER','GROUND'):continue
 pp=[];its=list(net.getITerms())
 for it in its:
  xy=it.getAvgXY()
  if xy[0]:pp.append(xy[2])
 for bt in net.getBTerms():
  for bp in bt.getBPins():
   for q in bp.getBoxes():pp.append((q.yMin()+q.yMax())/2)
 if not pp or not min(pp)<cut<max(pp):continue
 drivers=[it.getInst() for it in its if it.getMTerm().getIoType()=='OUTPUT']
 loads=[it.getInst() for it in its if it.getMTerm().getIoType()=='INPUT']
 if net.getSigType()=='CLOCK' or any('CLK'==it.getMTerm().getName().upper() for it in its):tag='clock'
 elif any(storage(i) is not None for i in loads):tag='storage_data_or_enable'
 elif any(name(i).startswith('ot_inhold') or name(i).startswith('ot_ih') for i in drivers):tag='input_hold_to_captures'
 elif any(seq(i) for i in drivers):tag='registered_data'
 else:tag='combinational'
 counts[tag]+=1
 if len(examples[tag])<8:examples[tag].append(dict(net=net.getName(),drivers=[name(i) for i in drivers],loads=[name(i) for i in loads[:3]]))
# Actual capture-flop output polarity: a remote shared inverter can make
# both QN and restored Q cross the same strip cut. Measure before constraining.
polarity=[];sink_refs=Counter()
for inst in b.getInsts():
    m=re.search(r'(?:^|\.)wd\[(\d+)\]',name(inst))
    if not m or not seq(inst):continue
    q=inst.getBBox();cx,cy=(q.xMin()+q.xMax())/2,(q.yMin()+q.yMax())/2
    sinks=[]
    for it in inst.getITerms():
        if it.getMTerm().getIoType()!='OUTPUT':continue
        net=it.getNet()
        if not net:continue
        for load in net.getITerms():
            if load.getMTerm().getIoType()!='INPUT':continue
            li=load.getInst();master=li.getMaster().getName();sink_refs[master]+=1
            box=li.getBBox();x,y=(box.xMin()+box.xMax())/2,(box.yMin()+box.yMax())/2
            sinks.append(dict(inst=li.getName(),master=master,xy_um=[x/u,y/u],distance_um=(abs(x-cx)+abs(y-cy))/u))
    polarity.append(dict(bit=int(m[1]),capture_inst=inst.getName(),capture_xy_um=[cx/u,cy/u],sinks=sinks))
out=dict(schema='opentallas.qwen.dvm.actual_write_cone.v1',odb=os.environ['DVM_ODB'],banks=rows,fill_polarity=polarity,fill_QN_sink_master_counts=dict(sink_refs),shared_write_cells=len([n for n,v in owner.items() if len(v)>1]),cut_y_um=cut/u,cut_counts=dict(counts),examples=dict(examples),route_admitted=False)
Path(os.environ['DVM_AUDIT_OUT']).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:out[k] for k in ['banks','shared_write_cells','cut_counts']}))
