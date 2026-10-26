#!/usr/bin/env python3
"""Replace only obsolete HC W64 B1 physical contracts with native W128 cuts.

Output is an unqualified placement candidate. Parent remainders stay logic;
no cycle/latency table or partition outline is altered.
"""
import argparse,json,hashlib,shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--templates',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();j=json.loads(a.plan.read_text());m=json.loads((a.templates/'templates.json').read_text());a.out.mkdir(parents=True,exist_ok=True);(a.out/'cores').mkdir(exist_ok=True);changes=[]
for name,master in m['masters'].items():shutil.copyfile(a.templates/master['pins_file'],a.out/'cores'/master['pins_file'])
for tn,placements in m['bank_placements'].items():
 t=j['partition_types'][tn];old=[c for c in t['hard_cores'] if c['module'].startswith('ot_hbm_hc_bankq')];assert len(old)==3,(tn,len(old));prefix=old[0]['inst'].split('_lanes')[0];t['hard_cores']=[c for c in t['hard_cores'] if c not in old]
 for p in placements:
  mod=p['module'];cut='ot_hbm_hc_bank128_pair'+str(p['pair']);t['hard_cores'].append(dict(inst=prefix+'.'+cut,module=mod,origin_um=p['origin_um'],outline_um=p['outline_um'],obs_max='M5',halo_um=8.64,track_offset_um=[0,0],pins_file='cores/'+m['masters'][mod]['pins_file'],parent_instance=prefix,cut_instance=cut,note='Exact current W128 pair cut; original parent remainder retained as logic; zero added cycles'))
 old_area=sum(c['outline_um'][0]*c['outline_um'][1] for c in old);new_area=sum(p['outline_um'][0]*p['outline_um'][1] for p in placements);changes.append(dict(type=tn,old_cores=3,new_cores=8,old_hard_area_um2=old_area,new_hard_area_um2=new_area,delta_hard_area_um2=new_area-old_area))
for tn in ['q_hub_nw','q_hub_ne']:
 t=j['partition_types'][tn];old=[c for c in t['hard_cores'] if c['module']=='ot_hbm_hc_qhub_static'];assert len(old)==1;old=old[0];t['hard_cores'].remove(old);x,y=old['origin_um'];mod='ot_hbm_hc_subtree32_core'
 for k in range(4):
  cut='ot_hbm_hc_subtree32_'+str(k);t['hard_cores'].append(dict(inst=old['inst']+'.u_cen.'+cut,module=mod,origin_um=[round(x+(k%2)*237.6,6),round(y+(k//2)*237.6,6)],outline_um=[220.32,220.32],obs_max='M5',halo_um=8.64,track_offset_um=[0,0],pins_file='cores/'+m['masters'][mod]['pins_file'],parent_instance=old['inst'],cut_instance='u_cen.'+cut,note='Five unchanged registered adder levels; upper two levels and original qhub/client control stay logic'))
 old_area=old['outline_um'][0]*old['outline_um'][1];new_area=4*220.32**2;changes.append(dict(type=tn,old_cores=1,new_cores=4,old_hard_area_um2=old_area,new_hard_area_um2=new_area,delta_hard_area_um2=new_area-old_area))
(a.out/'die_plan.json').write_text(json.dumps(j,indent=1)+'\n');receipt=dict(schema='opentallas.hbm.hc128.physical_overlay.v1',qualification='REPLAN_INPUT_NOT_PHYSICAL_ACCEPTANCE',source_plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),added_cycles=0,outline_growth_um2=0,changes=changes,pending=['parent cut-map integration into exact native body kit','station/FT replan against changed hard-core obstacles','M5 core synthesis/PnR and geometry image review','GRT STA clock/token closure'],model_notes=['Hard-core rectangle areas are placement allocations, not standard-cell area or PPA results.','Pair cut preserves 2x1024x256 weight SRAM and 1x128x256 x SRAM plus768 capture bits; 8 pairs per bank.','Four qhub32-leaf cuts preserve127 total FP adders:124 in subtrees and3 in original logic.','Parent control/client remainders stay in partition logic; no functional cells are deleted.'])
(a.out/'hc128_core_overlay.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(changes))
