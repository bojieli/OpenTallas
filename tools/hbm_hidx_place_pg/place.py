"""One diagnostic placement: connectivity-guided legal seed + one native DPL.
All rows retained, no region, fence, filler, optimization, CTS or routing.
"""
import openroad as O, odb, json, gzip, hashlib, math, collections, re
from pathlib import Path
P=Path('/work'); out=P/'output'; out.mkdir(exist_ok=True)
tech=O.Tech(); platform='/OpenROAD-flow-scripts/flow/platforms/asap7'
for family in ['AO','OA','INVBUF','SIMPLE']:
 for fn in sorted(Path(platform+'/lib/NLDM').glob(f'asap7sc7p5t_{family}_RVT_TT_*.lib.gz')):tech.readLiberty(str(fn))
tech.readLiberty(platform+'/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib')
tech.readLef(str(P/'input/canonical/tech.lef'));tech.readLef(str(P/'input/canonical/cells.lef'))
d=O.Design(tech);d.readVerilog(str(P/'input/netlist.v'));d.link('hidx_coupon1')
def tcl(s):return d.evalTclString(s)
tcl('initialize_floorplan -die_area {0 0 140.4 140.4} -core_area {2.16 2.16 138.24 138.24} -site asap7sc7p5t')
b=d.getBlock(); u=b.getDbUnitsPerMicron();rows=sorted(b.getRows(),key=lambda r:r.getOrigin()[1]);assert len(rows)==504,len(rows)
band=rows[200:304];assert abs(band[0].getBBox().yMin()/u-56.16)<1e-8
assert abs(band[-1].getBBox().yMax()/u-84.24)<1e-8
for layer in ['M2','M3','M4','M5']:
 tcl(f'make_tracks {layer} -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048')
pinmodel=json.loads((P/'input/pin_geometry_model.json').read_text())
anchors={}
for p in pinmodel['pins']:
 bt=b.findBTerm(p['port']);assert bt,p['port'];bp=odb.dbBPin_create(bt)
 rect=[round(z*u) for z in p['rect_um']]
 odb.dbBox_create(bp,tech.getDB().getTech().findLayer(p['layer']),*rect);bp.setPlacementStatus('PLACED')
 anchors[bt.getNet().getId()]=((rect[0]+rect[2])/2/u,(rect[1]+rect[3])/2/u)
assert len(b.getInsts())==11145
# Birth binding precedes placement protection and any PDN generation.
tcl('add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power')
tcl('add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground')
tcl('source /work/kit/vendor/native_pg_binding.tcl')
tcl('set block [ord::get_db_block]; set mapping [ot_pg_prepare $block]; foreach inst [$block getInsts] {ot_pg_bind_before_protect $mapping $inst}; ot_pg_assert_all_native $block $mapping')
insts=sorted(b.getInsts(),key=lambda i:i.getName());names={i.getName():i for i in insts}
nets=collections.defaultdict(list);links={};positions={}
for i in insts:
 h=int(hashlib.sha256(i.getName().encode()).hexdigest()[:8],16)
 positions[i.getName()]=(2.16+(h%10000)/10000*136.08,56.16+((h>>16)%10000)/10000*28.08)
 ids=[]
 for t in i.getITerms():
  # Clock omitted from placement objective only; strict audit retains its pins.
  if str(t.getMTerm().getSigType()) in ('POWER','GROUND','CLOCK'):continue
  if t.getNet():nets[t.getNet().getId()].append(i.getName());ids.append(t.getNet().getId())
 links[i.getName()]=ids
for iteration in range(16):
 centers={}
 for net,ns in nets.items():
  ps=[positions[n] for n in ns]
  if net in anchors:ps.extend([anchors[net]]*4)
  centers[net]=(sum(p[0] for p in ps)/len(ps),sum(p[1] for p in ps)/len(ps))
 for n,ids in links.items():
  if ids:
   x=sum(centers[z][0] for z in ids)/len(ids);y=sum(centers[z][1] for z in ids)/len(ids)
   positions[n]=(.25*positions[n][0]+.75*x,max(56.16,min(84.24,.25*positions[n][1]+.75*y)))
# Equal native-width quantiles use all104 rows, then preserve connectivity x order.
ordered=sorted(insts,key=lambda i:(positions[i.getName()][1],i.getName()))
total=sum(i.getMaster().getWidth() for i in ordered);assigned=[[] for _ in band];running=0
for i in ordered:
 w=i.getMaster().getWidth();row=min(103,int((running+w/2)*104/total));assigned[row].append(i);running+=w
initial={}
for row,cells in zip(band,assigned):
 cells.sort(key=lambda i:(positions[i.getName()][0],i.getName()))
 bbox=row.getBBox();width=sum(i.getMaster().getWidth() for i in cells);site=row.getSite().getWidth()
 assert width<bbox.dx(),(width,bbox.dx())
 left=bbox.xMin()+((bbox.dx()-width)//(2*site))*site
 for i in cells:
  i.setOrient(row.getOrient());i.setLocation(left,bbox.yMin());i.setPlacementStatus('PLACED')
  initial[i.getName()]=[str(i.getOrient()),list(i.getLocation())];left+=i.getMaster().getWidth()
(out/'initial_placement.json').write_text(json.dumps(initial))
# Exactly ONE detailed placement call, no optimize/retry.
tcl('detailed_placement');tcl('check_placement -verbose')
escaped=[]
for i in insts:
 box=i.getBBox()
 if box.yMin()<round(56.16*u) or box.yMax()>round(84.24*u):escaped.append(i.getName())
assert not escaped,escaped
assert len(b.getRows())==504 and len(b.getInsts())==11145
tcl('ot_pg_assert_all_native $block [ot_pg_prepare $block]')
# Save placement checkpoint before PDN or optional reports; never overwrite.
d.writeDb(str(out/'placement_checkpoint.odb'))
(out/'placement.status').write_text('PLACEMENT_LEGAL_ALL504ROWS_CENTRAL104ROWS_NATIVE_PG_BOUND_NO_CTS\n')
tcl('set_voltage_domain -name CORE -power VDD -ground VSS')
tcl('define_pdn_grid -name top -voltage_domains CORE -pins M5')
tcl('add_pdn_stripe -grid top -layer M1 -width 0.018 -pitch 0.54 -offset 0 -followpins')
tcl('add_pdn_stripe -grid top -layer M2 -width 0.018 -pitch 0.54 -offset 0 -followpins')
tcl('add_pdn_stripe -grid top -layer M5 -width 0.12 -spacing 0.072 -pitch 5.4 -offset 0.300')
tcl('add_pdn_connect -grid top -layers {M1 M2}')
tcl('add_pdn_connect -grid top -layers {M2 M5}')
tcl('pdngen')
tcl('ot_pg_assert_all_native $block [ot_pg_prepare $block]')
d.writeDb(str(out/'pg_checkpoint.odb'));tcl('write_verilog /work/output/pg_checkpoint.v')
(out/'checkpoint.status').write_text('PLACEMENT_PG_CHECKPOINT_COMPLETE_CONDUCTOR_AUDIT_PENDING_NO_CTS\n')
print('HIDX_SINGLE_PLACEMENT_PG_CHECKPOINT_COMPLETE')
