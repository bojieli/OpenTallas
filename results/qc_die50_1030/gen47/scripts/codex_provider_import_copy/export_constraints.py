#!/usr/bin/env python3
"""Read actual OpenDB placement constraints; never mutate or waive source OBS."""
import argparse,collections,hashlib,json,sys
from pathlib import Path
import odb

def tr(i,s):
 sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(i.getOrient())];x,y=i.getOrigin();xx=sorted([x+sx*s.xMin(),x+sx*s.xMax()]);yy=sorted([y+sy*s.yMin(),y+sy*s.yMax()]);return[xx[0],yy[0],xx[1],yy[1]]
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--inventory',required=True);p.add_argument('--die-plan',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools);import schema,die_trial
inv=json.load(open(a.inventory));P=schema.Plan(schema.load(a.die_plan),Path(a.die_plan));S=die_trial.SiteMap(P,halo=2.16);d=odb.dbDatabase.create();odb.read_db(d,a.source);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron();bb=b.getDieArea();masters={}
for name in sorted({c['master'] for c in inv['cells']}):
 m=d.findMaster(name)
 if not m:raise ValueError('source lacks required actual LEF master '+name)
 pins={}
 for mt in m.getMTerms():
  rects=[]
  for mp in mt.getMPins():
   for s in mp.getGeometry():
    l=s.getTechLayer()
    if l and l.getRoutingLevel()>0:rects.append([l.getName(),s.xMin(),s.yMin(),s.xMax(),s.yMax()])
  pins[mt.getName()]=dict(direction=str(mt.getIoType()),sigtype=str(mt.getSigType()),rects_dbu=rects)
 masters[name]=dict(wh_dbu=[m.getWidth(),m.getHeight()],pins=pins)
existing=[];soft=[];hard=[];pg=[];rows=[]
for i in b.getInsts():
 m=i.getMaster();bb=i.getBBox();r=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()]
 if str(m.getType()) not in ['BLOCK','BLOCK_BLACKBOX']:existing.append([i.getName(),m.getName(),*r]);continue
 for s in m.getObstructions():
  l=s.getTechLayer()
  if l and 1<=l.getRoutingLevel()<=3:soft.append([i.getName(),l.getName(),*tr(i,s)])
for q in b.getBlockages():
 z=q.getBBox();hard.append(['actual_placement_blockage',z.xMin(),z.yMin(),z.xMax(),z.yMax()])
for r in S.forb:hard.append([r[4],*[round(v*D) for v in r[:4]]])
for n in b.getNets():
 if str(n.getSigType()) not in ['POWER','GROUND']:continue
 for sw in n.getSWires():
  for z in sw.getWires():
   if z.isVia():
    v=z.getTechVia() or z.getBlockVia();x,y=z.getViaXY()
    for s in v.getBoxes():
     l=s.getTechLayer()
     if l and 1<=l.getRoutingLevel()<=3:pg.append([n.getName(),l.getName(),x+s.xMin(),y+s.yMin(),x+s.xMax(),y+s.yMax()])
   else:
    l=z.getTechLayer()
    if l and 1<=l.getRoutingLevel()<=3:pg.append([n.getName(),l.getName(),z.xMin(),z.yMin(),z.xMax(),z.yMax()])
for r in b.getRows():
 bb=r.getBBox();rows.append(dict(name=r.getName(),orient=str(r.getOrient()),site=r.getSite().getName(),origin=list(r.getOrigin()),spacing=r.getSpacing(),sites=r.getSiteCount(),bbox=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()]))
out=dict(schema='ot_provider_source_constraints/1',source=a.source,die_plan=a.die_plan,dbu=D,die_dbu=[0,0,round(P.W*D),round(P.H*D)],masters=masters,existing_cells=existing,hard_forbidden=hard,actual_lower_OBS=soft,actual_lower_PG=pg,rows=rows,policy='Proposal may request soft-partition islands; apply MUST check fresh actual OBS. Never cut hard cores or move existing cells.')
o=Path(a.out);o.mkdir(parents=True,exist_ok=True);json.dump(out,open(o/'constraints.json','w'),separators=(',',':'));print(json.dumps(dict(actual_masters=len(masters),existing_cells=len(existing),hard_rectangles=len(hard),lower_OBS=len(soft),lower_PG=len(pg),actual_rows=len(rows),die_um=[P.W,P.H]),indent=2))
