#!/usr/bin/env python3
"""OpenDB-only diagnostic of immutable S2 R2 native floorplan and row reservation.
Run using OpenROAD -python. Not a gate, placement, clock or escape qualification.
"""
import hashlib,json,math
from pathlib import Path
import odb
ROOT=Path.cwd()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(ROOT/'2_floorplan.odb')=='84728cae4c655c69a2fdd7d2a870539042272184ed2151caa66d9f81acb97f15','immutable R2 source ODB mismatch'
db=odb.dbDatabase.create();odb.read_db(db,str(ROOT/'2_floorplan.odb'))
b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();old='ot_sram_1r1w_32x128_m1_p192';new=old+'_rc'
oldm=db.findMaster(old)
lef=ROOT/(new+'.lef');odb.read_lef(db,str(lef));newm=db.findMaster(new)
assert oldm and newm
pin_signature=lambda m:{p.getName():(str(p.getIoType()),str(p.getSigType()),sorted((z.getTechLayer().getName(),z.xMin(),z.yMin(),z.xMax(),z.yMax()) for mp in p.getMPins() for z in mp.getGeometry())) for p in m.getMTerms()}
assert pin_signature(oldm)==pin_signature(newm),'native signal/clock/PG pin geometry changed'
assert (oldm.getWidth(),oldm.getHeight())==(newm.getWidth(),newm.getHeight())
macros=[]
for i in b.getInsts():
 if i.getMaster().getName()==old:
  nets={p.getMTerm().getName():p.getNet().getName() if p.getNet() else None for p in i.getITerms()}
  xy=i.getOrigin();orient=i.getOrient();assert i.swapMaster(newm)
  assert nets=={p.getMTerm().getName():p.getNet().getName() if p.getNet() else None for p in i.getITerms()}
  assert xy==i.getOrigin() and orient==i.getOrient()
  box=i.getBBox();macros.append(dict(instance=i.getName(),master=new,orient=str(orient),box_um=[v/u for v in (box.xMin(),box.yMin(),box.xMax(),box.yMax())],connected_pg={k:v for k,v in nets.items() if k in ('VDD','VSS','VDDCE','VDDPE','VSSE')}))
assert len(macros)==6
# Preserve every native BTerm and all mapped-instance connectivity. No new data edge.
def native_pins():
 return {t.getName():dict(direction=str(t.getIoType()),signal_type=str(t.getSigType()),boxes=sorted((x.getTechLayer().getName(),x.xMin(),x.yMin(),x.xMax(),x.yMax()) for p in t.getBPins() for x in p.getBoxes())) for t in b.getBTerms()}
pins_before=native_pins()
# Actual old native clock is near the NE corner. Reserve a free legal M5
# track at face centre beside the north body, without moving any data pin.
ck=b.findBTerm('ck_core');cp=list(ck.getBPins());assert len(cp)==1
boxes=list(cp[0].getBoxes());assert len(boxes)==1
z=boxes[0];layer=z.getTechLayer();assert layer.getName()=='M5'
y0,y1=z.yMin(),z.yMax();half=(z.xMax()-z.xMin())//2
occupied=[(v[1],v[3]) for name,entry in pins_before.items() if name!='ck_core' for v in entry['boxes'] if v[0]=='M5' and v[4]>267000]
for x in sorted(range(151020,151405,48),key=lambda x:abs(x-151200)):
 if all(x+half+48<lo or x-half-48>hi for lo,hi in occupied):break
else:raise RuntimeError('No nonoverlapping centre clock track')
odb.dbBox.destroy(z);odb.dbBox.create(cp[0],layer,x-half,y0,x+half,y1)
clock_pin_move=dict(old=pins_before['ck_core'],new=native_pins()['ck_core'],exact_centre_error_um=abs(x/u-151.2))
pins_expected=native_pins()

D=b.getDieArea();W=D.xMax()/u;H=D.yMax()/u
margin=2.16;depth=5.4;band=(190.08,265.68)
regions=[('body',[margin,band[0],W-margin,band[1]]),('west_face',[margin,margin,margin+depth,band[0]]),('east_face',[W-margin-depth,margin,W-margin,band[0]]),('south_face',[margin+depth,margin,W-margin-depth,margin+depth])]
rows=[(r.getName(),r.getSite(),r.getOrigin(),r.getOrient(),r.getDirection(),r.getSiteCount(),r.getSpacing()) for r in b.getRows()]
old_area=sum(r[5]*r[1].getWidth()*r[1].getHeight()/u**2 for r in rows)
for r in list(b.getRows()):odb.dbRow.destroy(r)
areas={k:0. for k,_ in regions};counts={k:0 for k,_ in regions}
for name,site,(ox,oy),orient,direction,n,spacing in rows:
 assert str(direction)=='HORIZONTAL'
 for label,box in regions:
  x0,y0,x1,y1=[round(v*u) for v in box]
  if oy<y0 or oy+site.getHeight()>y1:continue
  start=max(0,math.ceil((x0-ox)/spacing));stop=min(n,math.floor((x1-ox-site.getWidth())/spacing)+1)
  if stop<=start:continue
  count=stop-start
  odb.dbRow.create(b,name+'__'+label,site,ox+start*spacing,oy,orient,direction,count,spacing)
  areas[label]+=count*site.getWidth()*site.getHeight()/u**2;counts[label]+=1
assert native_pins()==pins_expected
# Cell/region occupancy must be measured after placement; row capacity is not occupancy.
source_mapped_std=12199.21722
report=dict(schema='opentallas.kv_order_s2_body_floorplan.v1',scope='diagnostic_source_pinned_macro_rebind_and_actual_row_capacity_only',input_odb_sha256=sha(ROOT/'2_floorplan.odb'),new_lef_sha256=sha(lef),source_commit='436d6e726a35de882f0d6dd1c067143900e0c529',mapped_netlist_sha256='e8bc20ae54460ce71ee1cda66cb7dd3dddf2058a3a1ddd65f88ef542c3f1c13f',outline_um=[W,H],diagonal_um=math.hypot(W,H),native_macro_geometry_connectivity_equal=True,macros=macros,macro_native_contacts=pin_signature(newm),native_bterm_count=len(pins_before),native_data_pin_geometry_and_connectivity_preserved=True,clock_pin_move=clock_pin_move,native_bterms=pins_before,regions_um=dict(regions),rows_before=len(rows),rows_after=sum(counts.values()),row_counts=counts,row_site_area_before_um2=old_area,row_site_area_after_um2=sum(areas.values()),row_site_area_by_region_um2=areas,mapped_std_area_um2=source_mapped_std,raw_density_over_retained_sites=source_mapped_std/sum(areas.values()),body_only_density_upper_bound=source_mapped_std/areas['body'],physical_qualified=False,placed_occupancy=None,clock_native_spread_TT_FF=None,all_wire_reach=None,remaining=['new coherent source synthesis and exact macro binding','retap pruned rows and regenerate PDN; cloned old PG is diagnostic only','actual face-register placement and body cell occupancy','external macro pin patch/via/min-area/access DRC','actual clock/reset/memory slew and all arcs TT setup FF hold','ROOT geometry/tool review before CTS','new parent GEN slot regrant and native pins'])
odb.write_db(db,str(ROOT/'body_plan.odb'))
report['output_odb_sha256']=sha(ROOT/'body_plan.odb')
(ROOT/'body_plan.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('macro_native_contacts','native_bterms','macros')},indent=2))
