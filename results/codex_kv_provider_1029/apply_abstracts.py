#!/usr/bin/env python3
"""Replace soft master OBS/PG pin boxes only; preserve actual grid and circuits."""
import argparse,collections,hashlib,json
from pathlib import Path
import odb
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--abstracts',required=True);p.add_argument('--tech-lef',required=True);p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True);d=odb.dbDatabase.create();odb.read_db(d,a.source);b=d.getChip().getBlock();donor=odb.dbDatabase.create();odb.read_lef(donor,a.tech_lef);manifest=json.load(open(Path(a.abstracts)/'manifest.json'))
def pin_shapes(mt):return sorted((s.getTechLayer().getName(),s.xMin(),s.yMin(),s.xMax(),s.yMax()) for mp in mt.getMPins() for s in mp.getGeometry() if s.getTechLayer())
def signal_shapes(m):return sorted((mt.getName(),str(mt.getIoType()),str(mt.getSigType()),pin_shapes(mt)) for mt in m.getMTerms() if str(mt.getSigType()) not in ['POWER','GROUND'])
def native():
 return sorted((i.getName(),i.getMaster().getName(),tuple(i.getOrigin()),str(i.getOrient()),str(i.getPlacementStatus()),tuple(sorted((it.getMTerm().getName(),it.getNet().getName() if it.getNet() else None) for it in i.getITerms()))) for i in b.getInsts())
before=native();mods=[]
for row in manifest['records']:
 mod=row['module'];odb.read_lef(donor,str(Path(a.abstracts)/(mod+'.lef')));src=donor.findMaster(mod);dst=d.findMaster(mod);assert src and dst,mod;signals=signal_shapes(dst);oldboxes=[z for z in dst.getObstructions()];oldobs=len(oldboxes);assert len(src.getMTerms())==len(dst.getMTerms()),mod
 for z in oldboxes:odb.dbBox_destroy(z)
 for z in src.getObstructions():
  ly=z.getTechLayer();assert ly,mod;odb.dbBox_create(dst,d.getTech().findLayer(ly.getName()),z.xMin(),z.yMin(),z.xMax(),z.yMax())
 assert sorted((z.getTechLayer().getName(),z.xMin(),z.yMin(),z.xMax(),z.yMax()) for z in dst.getObstructions())==sorted((z.getTechLayer().getName(),z.xMin(),z.yMin(),z.xMax(),z.yMax()) for z in src.getObstructions()),(mod,'OBS readback differs')
 for name in ['VDD','VSS']:
  st=src.findMTerm(name);dt=dst.findMTerm(name);assert st and dt,(mod,name);mpins=[x for x in dt.getMPins()];assert mpins,(mod,name);mp=mpins[0]
  for oldmp in mpins:
   for z in [x for x in oldmp.getGeometry()]:odb.dbBox_destroy(z)
  for layer,x,y,X,Y in pin_shapes(st):odb.dbBox_create(mp,d.getTech().findLayer(layer),x,y,X,Y)
  if pin_shapes(dt)!=pin_shapes(st):
   print('PG_PIN_DIFF',mod,name,'source_dbu',b.getDbUnitsPerMicron(),'donor_dbu',donor.getTech().getDbUnitsPerMicron(),'actual',len(pin_shapes(dt)),pin_shapes(dt)[:3],'expected',len(pin_shapes(st)),pin_shapes(st)[:3],flush=True)
   raise ValueError('actual PG pin geometry differs')
 assert signal_shapes(dst)==signals,(mod,'native signal pins changed');mods.append(dict(module=mod,old_obstructions=oldobs,new_obstructions=len(dst.getObstructions()),signal_pins_preserved=True))
assert native()==before,'cell placement/master/orientation or ITerm net changed'
odb.write_db(d,str(out/'native_full_islands.odb'));receipt=dict(verdict='SOFT_ABSTRACT_RESERVATIONS_UPDATED',source=a.source,source_sha256=hashlib.sha256(Path(a.source).read_bytes()).hexdigest(),output_sha256=hashlib.sha256((out/'native_full_islands.odb').read_bytes()).hexdigest(),instances=len(before),native_instances_connections_preserved=True,signal_pin_shapes_preserved=True,actual_special_PG_wires_edited=False,types=len(mods),records=mods,scope='Common type OBS and native macro PG pin clipping only; actual loaded GRT/PG continuity/STA still required');(out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='records'},indent=1))
