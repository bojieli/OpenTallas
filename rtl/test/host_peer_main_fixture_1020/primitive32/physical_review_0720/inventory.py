"""Actual frozen3_place footprint inventory for protected source-bound fences."""
from pathlib import Path
import json,gzip,re,hashlib
import odb
out=Path('/out');c=json.load(open('/model_src/classification.json'));g=json.load(gzip.open('/model_base/reset_graph_profile.json.gz','rt'))
p=next(Path('/gate/routes/gate/work/orfs/results/asap7').glob('*/base/3_place.odb'));db=odb.dbDatabase.create();odb.read_db(db,str(p));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron();insts={x.getName():x for x in b.getInsts()};ff={n:x for n,x in insts.items() if re.fullmatch(r'DFF(?:HQN|ASRHQN)x\d+_ASAP7_75t_R',x.getMaster().getName())};assert len(ff)==20507
boundary={x.rsplit('/',1)[0] for z in c['port_bits'] for k in ('data_input_flops','data_output_flops') for x in z[k]};assert len(boundary)==6025
outer={z['instance'].replace('.','/') for z in g['conditioners'] if z['stage']=='outer_S2'};assert len(outer)==128
missing=sorted((boundary|outer)-set(ff));protected=(boundary|outer)&set(ff);eligible=set(ff)-protected
area=lambda i:i.getMaster().getWidth()*i.getMaster().getHeight()/u**2
std=[x for x in insts.values() if not x.getMaster().isBlock()];masters={}
for x in std:
 m=x.getMaster();n=m.getName();a=masters.setdefault(n,{'count':0,'width_um':m.getWidth()/u,'height_um':m.getHeight()/u,'area_um2':area(x)});a['count']+=1
rect=[124.2,209.25,351,294.03];rectarea=(rect[2]-rect[0])*(rect[3]-rect[1]);stdarea=sum(area(x)for x in std);active=[x for x in std if any(t.getSigType() not in ('POWER','GROUND') for t in x.getITerms())];activearea=sum(area(x)for x in active);protectedarea=sum(area(ff[n])for n in protected)
r={'schema':'peer.actual_protected_fence_inventory.v1','odb_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'Actual3_place footprint only; exact source boundary/outerS2 protections, no permission to move multistage stations or proof of clock/reset/packing. Combinational footprint and clock-route cells may need additional physical partitions.','counts':{'standard_cells':len(std),'FF':len(ff),'boundary_FFs':len(boundary),'outer_S2_expected':len(outer),'outer_S2_present':len(outer&set(ff)),'protected_total':len(protected),'eligible_by_subtraction_ONLY':len(eligible)},'missing_expected_FFs':missing,'standardcell_area_um2':stdarea,'active_standardcell_count':len(active),'active_standardcell_area_um2':activearea,'power_ground_only_cell_area_um2':stdarea-activearea,'active_remaining_stdcell_area_um2':activearea-protectedarea,'active_remaining_over_rectangle_util':(activearea-protectedarea)/rectarea,'protected_FF_area_um2':protectedarea,'all_remaining_stdcell_area_um2':stdarea-protectedarea,'central_rectangle_um':rect,'central_rectangle_area_um2':rectarea,'all_remaining_stdcell_over_rectangle_util':(stdarea-protectedarea)/rectarea,'eligible_FFs':sorted(eligible),'protected_FFs':sorted(protected),'master_footprints':masters}
(out/'protected_fence_inventory.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ('eligible_FFs','protected_FFs','master_footprints')})
