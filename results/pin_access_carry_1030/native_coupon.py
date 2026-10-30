import json,odb
from pin_access_carry import GlobalRouteAccessPointCarry,AccessPointCarryError
base='/OpenROAD-flow-scripts/flow/platforms/asap7/lef/'
db=odb.dbDatabase.create()
for name in ('asap7_tech_1x_201209.lef','asap7sc7p5t_28_R_1x_220121a.lef','asap7sc7p5t_28_L_1x_220121a.lef'):
 odb.read_lef(db,base+name)
chip=odb.dbChip.create(db,db.getTech());block=odb.dbBlock.create(chip,'ap_carry_coupon')
r=db.findMaster('BUFx24_ASAP7_75t_R');l=db.findMaster('BUFx24_ASAP7_75t_L')
assert r and l
variants={'RVTN','RVTP','LVTN','LVTP'}
print('AP_API',hasattr(odb.dbMPin,'getPinAccess'),'string-direction-typemap',flush=True)
via=next(v for v in db.getTech().getVias() if v.getBottomLayer().getName()=='M1')
block_via=odb.dbVia.create(block,'coupon_via')
for box in via.getBoxes():
 odb.dbBox.create(block_via,box.getTechLayer(),box.xMin(),box.yMin(),box.xMax(),box.yMax())
catalogs={}
def make_source(name,index=0):
 i=odb.dbInst.create(block,r,name);i.setOrient('R0');i.setLocation(1080,540);i.setPlacementStatus('PLACED');i.setPinAccessIdx(index)
 for it in i.getITerms():
  if it.getSigType() in ('POWER','GROUND'):continue
  net=odb.dbNet.create(block,name+'_'+it.getMTerm().getName());it.connect(net)
  for pin in it.getMTerm().getMPins():
   aps=catalogs.setdefault((pin.getId(),index),[])
   if not aps:
    box=next(iter(pin.getGeometry()));rect=box;x=(rect.xMin()+rect.xMax())//2;y=(rect.yMin()+rect.yMax())//2
    for delta in (0,1):
     ap=odb.dbAccessPoint.create(block,pin,index);ap.setPoint(odb.Point(x+delta,y));ap.setLayer(box.getTechLayer())
     ap.setAccess(True,'EAST');ap.setAccess(True,'UP')
     ap.addTechVia(1,via);ap.addBlockVia(2,block_via);ap.addSegment(odb.Rect(x-2,y-2,x+2,y+2),True,False);aps.append(ap)
   it.setAccessPoint(pin,aps[-1])
 return i
a=make_source('good');b=make_source('reuse')
carry=GlobalRouteAccessPointCarry(db,variant_layers=variants,scope=GlobalRouteAccessPointCarry.SCOPE)
result=carry.swap(a,l);second=carry.swap(b,l)
assert result['cloned_preferred_positions']==2 and second['cloned_preferred_positions']==0
assert result['preferred_APs']==2 and not result['full_AP_catalog_preserved']
c=make_source('wrong_shape')
try: carry.swap(c,db.findMaster('BUFx12_ASAP7_75t_R'))
except AccessPointCarryError: pass
else: raise AssertionError('wrong footprint accepted')
assert c.getMaster().getName()==r.getName() and c.getPinAccessIdx()==0
try: GlobalRouteAccessPointCarry(db,variant_layers=variants,scope='detailed_routing')
except AccessPointCarryError: pass
else: raise AssertionError('DRT scope accepted')
try: GlobalRouteAccessPointCarry(db,variant_layers=variants|{'M1'},scope=carry.SCOPE).swap(c,l)
except AccessPointCarryError: pass
else: raise AssertionError('routing-layer exception accepted')
# A separate session must reject a pre-existing target catalog.
try: GlobalRouteAccessPointCarry(db,variant_layers=variants,scope=carry.SCOPE).swap(c,l)
except AccessPointCarryError: pass
else: raise AssertionError('unknown target catalog accepted')
out=dict(verdict='PASS',scope='synthetic metadata coupon only; no placement/STA/GRT/DRT',first=result,reuse=second,negative_controls=['wrong footprint','DRT scope','routing-layer exception','pre-existing target catalog'])
open('/work/grt_coupon.json','w').write(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2),flush=True)
