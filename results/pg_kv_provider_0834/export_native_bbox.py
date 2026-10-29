#!/usr/bin/env python3
"""Export actual mixed KV infrastructure supply rails and all obstructing native metal."""
import argparse,json,sys
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).parent))
from native_rect import transformed_rect
for root in (Path(__file__).resolve().parents[1],Path(__file__).resolve().parents[2]):
 sys.path.insert(0,str(root/"tools/die_plan"))
from infra_replay import route_shapes

def supply_shapes(net):
 """Actual PG wire rectangles plus conservative per-layer via-array enclosures.
 Cache array masters once; never expand every cut-array metal box per instance.
 """
 cache={}
 for sw in net.getSWires():
  for sh in sw.getWires():
   if not sh.isVia():
    ly=sh.getTechLayer()
    if ly and ly.getRoutingLevel()>0:yield ly,(sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()),'special_wire'
    continue
   via=sh.getTechVia() or sh.getBlockVia();key=via.getName()
   if key not in cache:
    bounds={}
    for box in via.getBoxes():
     ly=box.getTechLayer()
     if ly and ly.getRoutingLevel()>0:
      n=ly.getName();r=(box.xMin(),box.yMin(),box.xMax(),box.yMax())
      if n in bounds:
       l,q=bounds[n];r=(min(q[0],r[0]),min(q[1],r[1]),max(q[2],r[2]),max(q[3],r[3]))
      bounds[n]=(ly,r)
    cache[key]=list(bounds.values())
   x,y=sh.getViaXY()
   for ly,(x0,y0,x1,y1) in cache[key]:yield ly,(x+x0,y+y0,x+x1,y+y1),'via_enclosure'

def export(source,out,pg_reservations=None):
 import odb
 db=odb.dbDatabase.create();odb.read_db(db,str(source));b=db.getChip().getBlock();D=b.getDbUnitsPerMicron()
 obs=[];sup=[];sig=[];terms=[];cells=[];masters=Counter();grid=[];clock=[]
 reserved={(ly,*[round(v*D) for v in r]) for _,ly,*r in json.load(open(pg_reservations))} if pg_reservations else set()
 owned_obs=0
 for inst in b.getInsts():
  m=inst.getMaster();mn=m.getName();owned=mn.endswith('_ASAP7_75t_R')
  if owned:
   masters[mn]+=1;bb=inst.getBBox();cells.append(dict(inst=inst.getName(),master=mn,orient=str(inst.getOrient()),bbox_dbu=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()]))
   if str(inst.getOrient())!='R0':raise ValueError('Owned infrastructure is not R0: '+inst.getName())
  for sh in m.getObstructions():
   ly=sh.getTechLayer()
   if ly and 1<=ly.getRoutingLevel()<=9:obs.append([inst.getName(),ly.getName(),*transformed_rect(inst,sh)])
  for it in inst.getITerms():
   mt=it.getMTerm();st=str(mt.getSigType());ss=[]
   for mp in mt.getMPins():
    for sh in mp.getGeometry():
     ly=sh.getTechLayer()
     if ly and 1<=ly.getRoutingLevel()<=9:ss.append([ly.getName(),*transformed_rect(inst,sh)])
   if st in ('POWER','GROUND'):
    n='VDD' if st=='POWER' else 'VSS'
    if owned:
     if mt.getName()!=n or len(ss)!=1 or ss[0][0]!='M1' or ss[0][4]-ss[0][2]!=18:raise ValueError('Unexpected exact native rail '+inst.getName()+'/'+mt.getName())
     terms.append(dict(inst=inst.getName(),pin=n,master=mn,orient='R0',shapes_dbu=ss,connected_net=it.getNet().getName() if it.getNet() else None))
    else:
     actual=it.getNet().getName() if it.getNet() else mt.getName()
     if actual in ('VDD','VSS'):sup.extend([[actual,*r] for r in ss])
     else:obs.extend([[inst.getName()+'/'+actual,*r] for r in ss])
   else:sig.extend([[inst.getName(),mt.getName(),*r] for r in ss])
 for ob in b.getObstructions():
  sh=ob.getBBox();ly=sh.getTechLayer()
  if ly and 1<=ly.getRoutingLevel()<=9:
   key=(ly.getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax())
   if key in reserved:owned_obs+=1
   else:obs.append(['BLOCK',*key])
 for bt in b.getBTerms():
  for bp in bt.getBPins():
   for sh in bp.getBoxes():
    ly=sh.getTechLayer()
    if ly and 1<=ly.getRoutingLevel()<=9:sig.append(['BTERM',bt.getName(),ly.getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()])
 for net in b.getNets():
  st=str(net.getSigType());n=net.getName()
  for lyobj,r,kind in (supply_shapes(net) if st in ("POWER","GROUND") else route_shapes(net)):
   ly=lyobj.getName()
   if st in ('POWER','GROUND'):
    if n in ('VDD','VSS'):sup.append([n,ly,*r])
    else:obs.append([n,ly,*r])
    if kind!='via_enclosure' and ly in ('M8','M9') and n in ('VDD','VSS'):grid.append([n,ly,*[v/D for v in r]])
   else:sig.append([n,'WIRE',ly,*r]);clock.append([n,ly,*[v/D for v in r]])
 vias={v.getName():[[s.getTechLayer().getName(),s.xMin(),s.yMin(),s.xMax(),s.yMax()] for s in v.getBoxes() if s.getTechLayer()] for v in db.getTech().getVias() if v.getName() in {f'VIA{i}{i+1}' for i in range(1,9)}}
 bb=b.getDieArea();out=Path(out);out.mkdir(parents=True,exist_ok=True)
 docs={'geometry':dict(source=str(source),dbu=D,die_dbu=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()],cells=cells,signal_shapes=sig,obstructions=obs,existing_supplies=sup),'power_terms':dict(dbu=D,terms=terms),'endpoints':dict(endpoints={}), 'pg_rects':grid,'clock_seed':clock,'probe_census':dict(tech_vias_dbu=vias)}
 for k,v in docs.items():(out/(k+'.json')).write_text(json.dumps(v,separators=(',',':')))
 result=dict(source=str(source),cells=len(cells),masters=dict(masters),terms=len(terms),grid_rectangles=len(grid),signal_rectangles=len(sig),obstructions=len(obs),existing_supplies=len(sup),regular_wired_nets=sum(net.getWire() is not None for net in b.getNets()),owned_pg_capacity_obstructions=owned_obs,pg_via_representation='conservative exact per-layer array-master bounding enclosure; no cut-array expansion')
 (out/'export_receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
 if not grid:raise ValueError('No actual canonical M8/M9 grid; materialize plan PG before access planning')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);p.add_argument('--pg-reservations');a=p.parse_args();export(a.odb,a.out,a.pg_reservations)
