#!/usr/bin/env python3
"""Source-bound complete placed-contact/PG and pair-geometry census; no STA claim."""
import json,sys,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import check_macro_track_alignment as C

def main():
 base='ot_sram_1r1w_64x512_m1_r2c2_p192';new=base+'_mir';d=ROOT/'physical/asap7_memory_macros';out=ROOT/'results/arch/hbm_pvm_safe2_1019/mirror_geometry';out.mkdir(parents=True,exist_ok=True)
 records={};coords=[]
 for name in [base,new]:
  p=d/name/(name+'.lef');m=C.parse_lef(p.read_text())[0]
  a=C.audit_macro(m,C.ASAP7_TRACKS_NM,C.ASAP7_LAYERS,str(p.relative_to(ROOT)))
  for ori in ['R0','R180']:a['placed_'+ori]=C.check_placement(m,ori,43200,43200)
  records[name]=a
  if name!=new:continue
  byface={'W':0,'E':0};pg=0
  for pin in m['pins']:
   for layer,rect in pin['rects']:
    q=C.transform_rect(rect,'R180',m['W'],m['H']);g=[(v+43200)/1000 for v in q]
    assert 43.2<=g[0]<=g[2]<=214.4880001 and 43.2<=g[1]<=g[3]<=197.1120001
    coords.append(dict(pin=pin['name'],use=pin['use'],layer=layer,bbox_um=g))
    if pin['use'] in ['POWER','GROUND']:pg+=1;continue
    if q[0]==0:byface['W']+=1
    if q[2]==m['W']:byface['E']+=1
  clock=next(x for x in coords if x['pin']=='clk');clock_xy=[(clock['bbox_um'][0]+clock['bbox_um'][2])/2,(clock['bbox_um'][1]+clock['bbox_um'][3])/2]
  density={k:v/(m['H']/1000) for k,v in byface.items()}
 assert records[base]['placed_R180']['layers']['M4']['offtrack']==1585
 assert records[new]['placed_R180']['layers']['M4']['offtrack']==0
 assert max(density.values())<=6
 sheet=json.loads((d/new/(new+'.json')).read_text());old=json.loads((d/base/(base+'.json')).read_text())
 model=dict(schema='opentallas.pvm_mirror_geometry_1019.v1',immutable_source='eda0b1540',macro=new,size_um=[171.288,153.912],origin_um=[43.2,43.2],orientation='R180',macro_bbox_um=[43.2,43.2,214.488,197.112],std_band_um=[2.16,216,300.24,300.24],nominal_band_um=[0,216,302.4,302.4],outline_um=[302.4,302.4],std_area_um2=10343,std_band_fill=10343/(298.08*84.24),face_contacts=byface,fullface_density_per_um=density,power_rectangles=pg,clock_xy_um=clock_xy,clock_gap_to_band_um=216-clock_xy[1],macro_area_um2=sheet['area']['macro_area_um2'],macro_area_delta_um2=sheet['area']['macro_area_um2']-old['area']['macro_area_um2'],outline_area_delta_um2=0,external_data_edge_delta=0,pair='SRAM rd_out -> existing operand capture; whole SRAM R180; source data contract remains unchanged',timing=sheet['timing'],pin_checks=records[new]['pin_checks'],localdriver_assessment=dict(old_clock_xy_um=[43.212,43.980],old_nearest_legal_driver_gap_um=172.020,actual_final_clock_wire_ps=163.821,actual_macro_clock_slew_ps=519.859,actual_TT_setup_ps=-59.94449,actual_FF_hold_ps=20.63885,source='Immutable gatefixedrows+standalone GRT-coordinate estimated-RC STA; not extracted SPEF',finding='Old orientation cannot place local driver beside clock without leaving soleNband; capture-only delay is not assumed safe given FFhold. R180 permits nearclock driver inside sameband; actual CTS/native proof owed'),remaining=['actual external access/via/PG/DRC; raw24x24nm contacts require routepatches for2000nm2 M4 minarea','actual mapped geometry/reach/band census','native TTsetup/FFhold and final parent clockreference','Analytical compiler has no transistor/GDS view; no foundry claim'],qualification=False,views_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (d/new).iterdir()},canonical_macro_unchanged=not bool(subprocess.check_output(['git','status','--porcelain','--',str((d/base).relative_to(ROOT))],cwd=ROOT,text=True)))
 assert model['canonical_macro_unchanged']
 for n,v in [('model.json',model),('track_audit.json',records),('placed_contacts.json',coords)]: (out/n).write_text(json.dumps(v,indent=2)+'\n')
 print(json.dumps({k:model[k] for k in ['face_contacts','fullface_density_per_um','clock_xy_um','clock_gap_to_band_um','macro_area_delta_um2','std_band_fill']}))
if __name__=='__main__':main()
