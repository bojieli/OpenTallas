import sys,json
from pathlib import Path
sys.path.insert(0,str(Path('tools/die_plan').resolve()))
import schema as S,taps as T
from placement_obstacles import probe_blockages
r=json.load(open('input.json'));audit={}
for tn in ['q_su00','q_su00__physical_v1']:
 t=r['partition_types'][tn];ck=t['clock'];boxes=S.placed_macro_boxes(t);extra=[]
 for q in probe_blockages(t):
  if q['inst'] not in boxes:
   x,y=q['origin_um'];w,h=q['outline_um'];extra.append([x,y,x+w,y+h])
 ck['keepouts_um']=list({tuple(v)for v in ck.get('keepouts_um',[])+extra})
 ck['control_sinks']=True;ck.update(tap_mode='density',tap_max_sinks=1500,tap_target_sinks=1200,tap_radius_um=220)
 core=[v for v in ck['taps']if v.get('kind')=='core']
 taps=T.density_taps(S.Plan(r),tn,control=False)
 ck['tap_mode']='explicit';ck['taps']=[dict(name=n,xy=[x,y],kind='glue')for n,x,y,load,rad in taps]+core
 final=T.explicit_taps(S.Plan(r),tn)
 audit[tn]=dict(local_inputs=len(final),early_core_inputs=len(core),max_load=max(q[3]for q in final),max_radius=max(q[4]for q in final))
 print(tn,audit[tn],flush=True)
json.dump(r,open('candidate.json','w'));json.dump(audit,open('audit.json','w'),indent=2)
