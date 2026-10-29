#!/usr/bin/env python3
"""Read actual legal-island ODB geometry for physical PG access; never mutate it."""
import argparse,json
from pathlib import Path
import odb
import sys
sys.path.insert(0,str(Path(__file__).parent))
from pg_census import transformed_rect
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);a=p.parse_args()
d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock();dbu=b.getDbUnitsPerMicron()
obs=[];sup=[];cells=[];masters={};sig=[]
for i in b.getInsts():
 m=i.getMaster();mn=m.getName();isclk=mn.startswith('CKINVDCx16_')
 if isclk:
  bb=i.getBBox();cells.append(dict(inst=i.getName(),master=mn,orient=str(i.getOrient()),bbox_dbu=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()]))
  for nm in ['A','Y']:
   it=i.findITerm(nm)
   if not it:continue
   for mp in it.getMTerm().getMPins():
    for sh in mp.getGeometry():
     lay=sh.getTechLayer()
     if lay and lay.getRoutingLevel()>0:sig.append([i.getName(),nm,lay.getName(),*transformed_rect(i,sh)])
 else:
  for sh in m.getObstructions():
   lay=sh.getTechLayer()
   if lay and 1<=lay.getRoutingLevel()<=9:obs.append([i.getName(),lay.getName(),*transformed_rect(i,sh)])
  for it in i.getITerms():
   mt=it.getMTerm();st=str(mt.getSigType())
   if st not in ['POWER','GROUND']:
    for mp in mt.getMPins():
     for sh in mp.getGeometry():
      lay=sh.getTechLayer()
      if lay and 1<=lay.getRoutingLevel()<=9:sig.append([i.getName(),mt.getName(),lay.getName(),*transformed_rect(i,sh)])
    continue
   net='VDD' if st=='POWER' else 'VSS'
   for mp in mt.getMPins():
    for sh in mp.getGeometry():
     lay=sh.getTechLayer()
     if lay and 1<=lay.getRoutingLevel()<=9:sup.append([net,lay.getName(),*transformed_rect(i,sh)])
for oo in b.getObstructions():
 sh=oo.getBBox();lay=sh.getTechLayer()
 if lay and 1<=lay.getRoutingLevel()<=9:obs.append(['BLOCK',lay.getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()])
for net in b.getNets():
 if str(net.getSigType()) not in ['POWER','GROUND']:continue
 nn='VDD' if str(net.getSigType())=='POWER' else 'VSS'
 for sw in net.getSWires():
  for sh in sw.getWires():
   if sh.isVia():continue
   lay=sh.getTechLayer()
   if lay and 1<=lay.getRoutingLevel()<=9:sup.append([nn,lay.getName(),sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()])
tracks={}
for n in ['M7','M8','M9']:
 lay=d.getTech().findLayer(n);tg=b.findTrackGrid(lay)
 tracks[n]={}
 if tg:
  for axis in ['X','Y']:
   nn=getattr(tg,'getNumGridPatterns'+axis)();tracks[n][axis]=[list(getattr(tg,'getGridPattern'+axis)(k)) for k in range(nn)]
bb=b.getDieArea();o=Path(a.out);o.mkdir(parents=True,exist_ok=True)
json.dump(dict(source=a.odb,dbu=dbu,die_dbu=[bb.xMin(),bb.yMin(),bb.xMax(),bb.yMax()],cells=cells,signal_shapes=sig,obstructions=obs,existing_supplies=sup,tracks=tracks),open(o/'geometry.json','w'),separators=(',',':'))
print(json.dumps(dict(cells=len(cells),signal_shapes=len(sig),obstructions=len(obs),existing_supplies=len(sup),tracks=tracks)))
