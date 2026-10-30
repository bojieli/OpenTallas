import subprocess,json
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-hbm-1030');p=r/'load_lot';results=[]
for w,h in [(201.6,226.8),(162,282.96)]:
 for order in ['normal','reverse']:
  name=f'shape_{w}_{h}_{order}';f=p/(name+'.json')
  cmd=['python3',str(p/'allocate_load_shapes.py'),str(r/'model_src'),str(r/'hh_seams2/die_plan.json'),'/srv/opentallas-scratch2/claude/codex-hbm-bind-1030/current_raw_vmdel_plan_facts.json',str(f),'1600',str(w),str(h),order]
  with open(p/(name+'.log'),'w')as out:rc=subprocess.call(cmd,stdout=out,stderr=subprocess.STDOUT)
  d=json.load(open(f))if rc==0 else{};good=[x for x in d.get('proposals',[])if x['verdict']=='ESTIMATE_SPACE_ONLY'];row=dict(outline_um=[w,h],order=order,rc=rc,fit_count=len(good),total_fill_extension_bound=sum(x['fill_bus_extension_upper_um']for x in good));results.append(row);print(json.dumps(row),flush=True)
(p/'shape_batch_summary.json').write_text(json.dumps(results,indent=2)+'\n')
