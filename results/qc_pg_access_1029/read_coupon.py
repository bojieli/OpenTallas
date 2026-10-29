#!/usr/bin/env python3
"""Read physical conductors/vias and native contact metal back from coupon ODB."""
import argparse,json,odb
from pathlib import Path
from pg_census import transformed_rect
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--plan',required=True);p.add_argument('--out',required=True);a=p.parse_args();d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock();plan=json.load(open(a.plan));records=[];contacts=[];via_count=0;wire_count=0
for n in ['VDD','VSS']:
 net=b.findNet(n);assert net
 for sw in net.getSWires():
  for s in sw.getWires():
   rid=len(records)
   if s.isVia():
    tv=s.getTechVia();assert tv,'Only technology vias qualified';x,y=s.getViaXY();rr=[]
    for q in tv.getBoxes():
     ly=q.getTechLayer()
     if ly and ly.getRoutingLevel()>0:rr.append([ly.getName(),x+q.xMin(),y+q.yMin(),x+q.xMax(),y+q.yMax()])
    records.append(dict(net=n,kind='via',name=tv.getName(),xy=[x,y],rects=rr));via_count+=1
   else:
    ly=s.getTechLayer();records.append(dict(net=n,kind='wire',rects=[[ly.getName(),s.xMin(),s.yMin(),s.xMax(),s.yMax()]]));wire_count+=1
for q in plan['paths']:
 for nm in q['members']:
  inst=b.findInst(nm);it=inst.findITerm(q['net']);assert it.getNet().getName()==q['net'];rr=[]
  for mp in it.getMTerm().getMPins():
   for sh in mp.getGeometry():
    ly=sh.getTechLayer()
    if ly and ly.getRoutingLevel()>0:rr.append([ly.getName(),*transformed_rect(inst,sh)])
  contacts.append(dict(inst=nm,pin=q['net'],record=len(records)));records.append(dict(net=q['net'],kind='contact',rects=rr))
json.dump(dict(source=a.odb,records=records,contacts=contacts,via_count=via_count,wire_count=wire_count),open(a.out,'w'),separators=(',',':'));print(dict(contacts=len(contacts),actual_vias=via_count,actual_wires=wire_count))
