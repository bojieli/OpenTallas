#!/usr/bin/env python3
"""Refresh exact native OBS/PG-pin inventories while retaining unchanged actual top PG metal."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from apply_access import non_pg_hash
from native_rect import transformed_rect
from infra_replay import route_shapes

def export(source,old_native,terms_path,reservations,expected_hash,out):
 import odb
 d=odb.dbDatabase.create();odb.read_db(d,source);b=d.getChip().getBlock();D=b.getDbUnitsPerMicron();sha=non_pg_hash(b)
 if sha!=expected_hash:raise ValueError('Union source changed cells, signal/clock pins, connections or routing')
 wanted={(ly,*[round(v*D) for v in r]) for _,ly,*r in json.load(open(reservations))};obs=[];native=[];owned={};removed=0
 for inst in b.getInsts():
  name=inst.getName();m=inst.getMaster();std=m.getName().endswith('_ASAP7_75t_R')
  for sh in m.getObstructions():
   ly=sh.getTechLayer()
   if ly and 1<=ly.getRoutingLevel()<=9:obs.append([name,ly.getName(),*transformed_rect(inst,sh)])
  for it in inst.getITerms():
   if str(it.getMTerm().getSigType()) not in ('POWER','GROUND'):continue
   n=it.getNet().getName() if it.getNet() else it.getMTerm().getName();ss=[]
   for mp in it.getMTerm().getMPins():
    for sh in mp.getGeometry():
     ly=sh.getTechLayer()
     if ly and ly.getRoutingLevel()>0:ss.append([ly.getName(),*transformed_rect(inst,sh)])
   if std:owned[name,it.getMTerm().getName()]=ss
   elif n in ('VDD','VSS'):native.extend([[n,*r] for r in ss])
   else:obs.extend([[name+'/'+n,*r] for r in ss])
 for ob in b.getObstructions():
  sh=ob.getBBox();ly=sh.getTechLayer();key=(ly.getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax())
  if key in wanted:removed+=1
  else:obs.append(['BLOCK',*key])
 for n in b.getNets():
  if str(n.getSigType()) not in ('POWER','GROUND') or n.getName() in ('VDD','VSS'):continue
  obs.extend([[n.getName(),ly.getName(),*r] for ly,r,_ in route_shapes(n)])
 expected={(t['inst'],t['pin']):t['shapes_dbu'] for t in json.load(open(terms_path))['terms']}
 if owned!=expected:raise ValueError('Actual standard-cell supply rails changed during OBS union repair')
 old=json.load(open(old_native))['existing_supplies']
 result=dict(schema='opentallas.native_pg_obstruction_overlay.v1',source=source,non_pg_sha256=sha,obstructions=obs,old_native_supplies=old,new_native_supplies=native,owned_supply_terms=len(owned),owned_pg_capacity_obstructions=removed,scope='Native soft OBS/PG pins only refreshed from actual union ODB; actual top PG geometry retained from original export')
 Path(out).write_text(json.dumps(result,separators=(',',':')))
 print(json.dumps({k:v for k,v in result.items() if k not in ('obstructions','old_native_supplies','new_native_supplies')}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--old-native',required=True);p.add_argument('--terms',required=True);p.add_argument('--reservations',required=True);p.add_argument('--non-pg-sha',required=True);p.add_argument('--out',required=True);a=p.parse_args();export(a.odb,a.old_native,a.terms,a.reservations,a.non_pg_sha,a.out)
