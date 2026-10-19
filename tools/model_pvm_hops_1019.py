#!/usr/bin/env python3
"""Model Manhattan contact/register hop bounds under explicit placement regions.
These regions are necessary constraints, not measured placement assertions.
"""
from pathlib import Path
import json,re,hashlib,csv,math
ROOT=Path(__file__).resolve().parents[1]

def corners(r):return [(r[i],r[j]) for i in [0,2] for j in [1,3]]
def worst(a,b):return max(abs(x-u)+abs(y-v) for x,y in corners(a) for u,v in corners(b))
def main():
 d=ROOT/'results/arch/hbm_pvm_safe2_1019';contacts=json.loads((d/'mirror_geometry_mapped/placed_contacts.json').read_text());src=ROOT/'rtl/hbm_accel/sm/attn/ot_hbm_sm_pv_merge_s3.sv';s=src.read_text();binding=re.search(r'u_stack\s*\((.*?)\);',s,re.S).group(1)
 const={'r_ce_in':"1'b1",'w_mask_in':"{512{1'b1}}",'rr_en':"2'b00",'rr_addr':"12'd0",'cr_en':"2'b00",'cr_sel':"18'd0"}
 for p,v in const.items():assert '.'+p+'('+v+')' in binding,(p,v)
 body=[86.4,230.04,259.2,247.32];io=[2.16,229.23,300.24,300.24];boundary=[85.32,229.23,260.28,300.24];tieW=[86.4,229.23,172.8,229.77];tieE=io
 actual=d/'hop_model/inputs'
 cones=list(csv.DictReader((actual/'macro_functional_cones.tsv').open(),delimiter='\t'))
 regs=set(re.findall(r'\breg(?:\s+\[[^]]+\])?\s+(\w+__ot_q)\s*;', (actual/'ot_pin_regs_wrapper.v').read_text()))
 boundary_names={x['cell'] for x in csv.DictReader((actual/'pvm_region_boundary.tsv').open(),delimiter='\t')}
 def boundary_cell(name):return name in boundary_names
 areas=list(csv.DictReader((actual/'critical_cell_areas.tsv').open(),delimiter='\t'))
 critical_area=sum(float(x['area_um2']) for x in areas if not int(x['is_block']) and not boundary_cell(x['instance']))
 assert 1322<critical_area<1324
 starts={}
 for row in cones:
  if row['role'] in ['startpoint','endpoint']:
   starts.setdefault(row['macro_pin'],[]).append(row['object'])
 rows=[]
 for c in contacts:
  if c['use'] in ['POWER','GROUND'] or c['pin']=='clk':continue
  port=c['pin'].split('[')[0];r=c['bbox_um'];isconst=port in const
  if isconst:target=tieW if r[0]<100 else tieE
  else:
   points=starts.get(c['pin'],[])
   assert points,c['pin']
   has_boundary=any(boundary_cell(x.rsplit('/',1)[0]) for x in points)
   target=boundary if has_boundary else body
  w=worst(r,target);assert w<=386,(c['pin'],w)
  rows.append(dict(pin=c['pin'],contact_bbox_um=r,register_or_tie_region_um=target,max_manhattan_um=round(w,6),connection='constant:'+const[port] if isconst else 'functional:'+port))
 reset_source=(actual/'ot_pin_regs_wrapper.v').read_text();assert 'rst_n__ot_rl0 <= rst_n;' in reset_source and 'rst_n__ot_rl1 <= rst_n__ot_rl0;' in reset_source and 'rst_n__ot_rlc <= {15{rst_n__ot_rl0}};' in reset_source
 r=dict(schema='opentallas.pvm_hop_reset_model_1019.v1',source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),source_binding=binding,metric='Worst Manhattan endpoint bound from allrectcorner pairs, including24nm contacts. Realroute detours/nativeSTA remainmeasured requirements. No halfcycle/multicycle exceptions.',body_region_um=body,fullface_pin_register_band_um=io,tieW_region_um=tieW,tieE_region_um=tieE,required_constraints=['Actual connectivity-selected internalmacrocone cells, area recomputed from OpenDB, confined to nonoverlapping44.31%density FENCE inside soleband; otherstdcells freeinband','546single-sink Wmacroconstantties in51.19%density two-row FENCE; remainingconstantcells freeinband','Clockbuffers legal within soleNband, modeledmacroclockcontact32.898um away; actualclock RC/slew/native notproved'],status='SOURCE-BOUND FEASIBILITY MODEL with runtime-connectivity fence hook; HOLD CTS until freshplacement and fullfaceIO coordinate audit proves actualregions',critical_region_fill=critical_area/((body[2]-body[0])*(body[3]-body[1])),critical_cell_count=sum(not int(x['is_block']) and not boundary_cell(x['instance']) for x in areas),boundary_cone_registers=len(boundary_names),boundary_source_ports=['sum','ev','fold_a','fold_start','pub_slot','pub_start','tag_d'],boundary_source_pin_range_um=[86.4,259.2],constW_cell_count=546,constW_region_fill=(546*.04374)/(86.4*.54),source_cone_sha256=hashlib.sha256((actual/'macro_functional_cones.tsv').read_bytes()).hexdigest(),constraint_hook_sha256=hashlib.sha256((ROOT/'physical/ref_tile/smh_pvm_ref_s3/macro_regions.tcl').read_bytes()).hexdigest(),max_functional_macro_hop_um=max(x['max_manhattan_um'] for x in rows if x['connection'].startswith('functional')),max_constant_macro_hop_um=max(x['max_manhattan_um'] for x in rows if x['connection'].startswith('constant')),max_body_to_fullface_reg_hop_um=worst(body,io),max_reg_to_reg_hop_um=worst(io,io),macro_hops=rows,reset=dict(actual_wrapper_sha256=hashlib.sha256(reset_source.encode()).hexdigest(),equations=['L0[n+1] = rst_n[n]','L1[n+1] = L0[n]','C[j,n+1] = L0[n], j=0..14','family[n]={C[14:0,n],L1[n]}','For n>=2 and identical reset-domain boot: EVERY familybit[n]=rst_n[n-2]'],depth=2,copy_extra_depth=0,boot='As with original2stageface landing, parent holdsrst low for>=2sampled edges; no newstartupguard/dataedge',sink_rewire='ot_rst_copies.py verifies identical register type/clock/D/reset percopybefore391sink redistribution; generated script+TSV recorded in mapped_census',newdata_edge_delta=0),physical_qualified=False)
 out=d/'hop_model';out.mkdir(exist_ok=True);(out/'model.json').write_text(json.dumps(r,indent=2)+'\n');print({k:r[k] for k in ['max_functional_macro_hop_um','max_constant_macro_hop_um','max_body_to_fullface_reg_hop_um','max_reg_to_reg_hop_um','critical_region_fill','constW_region_fill']})
if __name__=='__main__':main()
