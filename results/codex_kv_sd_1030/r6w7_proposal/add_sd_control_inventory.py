import json,sys
from pathlib import Path
r=Path(__file__).resolve().parent;sys.path.insert(0,str(r/'src/tools/die_plan'))
import schema as S,taps
p=json.load(open(r/'plan_of_record/plan_c_sd_r6w7_candidate.json'));result={}
for tn in ('kv3_sys_SD','kv3_sys_SD_v1'):
 t=p['partition_types'][tn];ck=t['clock'];lc=ck['landing_contract'];rows=[]
 for n in lc['collector_tree']['relays']:rows.append({'name':n['name'],'xy':n['xy'],'count':1})
 for kind in ('reader','writer'):
  for b,cfg in ck['landing_'+kind+'_start']['branches'].items():
   for i,n in enumerate(cfg['stages']):rows.append({'name':'u_cland_'+kind+'_start_'+b+'_'+str(i),'xy':n['xy_um'],'count':1})
 for n in ck['landing_local_resets']:rows.append({'name':'u_cland_local_reset_'+n['name'],'xy':n['xy_um'],'count':1})
 # Exact origin_s PADW1 instantiated native graph: s0,s1,s2,sf and one pd.
 rows.append({'name':'u_cland_origin/{s0,s1,s2,sf,pd[0]}','xy':[190.56,21.6],'count':5})
 ck['sink_sites_um']=[n['xy']+[n['count']] for n in rows]
 result[tn]={'named_actual_new_control_sinks':rows,'qualification':'Conservative supplemental control count over unchanged historical full-bin data. Old control FFs remain double-counted; proposed new ring/PHY primary relocation not reflected. PREP budget only, actual new placement mandatory.'}
P=S.Plan(p,str(r/'plan_of_record/plan_c_sd_r6w7_control_inventory.json'))
for tn in result:
 try:result[tn]['budget_result']=taps.explicit_taps(P,tn)
 except Exception as e:result[tn]['budget_error']=str(e)
(r/'plan_of_record/plan_c_sd_r6w7_control_inventory.json').write_text(json.dumps(p,indent=1))
(r/'sd_r6w7_control_inventory.json').write_text(json.dumps(result,indent=1))
print(json.dumps({k:{a:b for a,b in v.items() if a.startswith('budget')} for k,v in result.items()},indent=1))
