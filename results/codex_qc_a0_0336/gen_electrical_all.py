"""MODEL ONLY A0 electrical clock synthesis: one common target, variable path depths.
No measured arrival, timing slack or useful-skew target is consumed.
"""
import sys,json,copy,statistics,math
from pathlib import Path
p=Path.cwd();sys.path.insert(0,str(p/'src'));sys.path.insert(0,str(p/'tool_snapshot/tools/die_plan'))
import die_clock_128 as C
import core_infra_plan_metrics as M
sys.argv=['qualify2.py','plans/nl_affp.json','data/nl.tsv.gz','kit_nl','unused','unused']
e={'__file__':str(p/'src/qualify2.py')};exec((p/'src/qualify2.py').read_text().split('model=M.predict_tree')[0],e)
sl=e['sl'];libs=e['libs'];pts=e['pts'];caps=e['caps'];t=sl['core_tree'];t['electrical_latency_model_only']=True
from gen_a0_adaptive2 import Planner,lef_geom,HALO
fr=json.load(open('kit_nl/freeze.json'));boxes=[]
for h in fr['hard_children']:
 w,hh,_=lef_geom(p/'kit_nl/macros'/f"{h['master']}.lef");x,y=h['at'];boxes.append((x-HALO[0],y-HALO[1],x+w+HALO[0],y+hh+HALO[1]))
planner=Planner(boxes,150.)
def model():return M.predict_tree(sl,libs,pts,caps,.018515*.8,.17137*.9,input_slew_ps=20.)
def effective(m):
 out={}
 bynode={l['node']:l for l in t['leaves']}
 for c in ('TT','FF'):
  out[c]={}
  for row in m['corners'][c]['leaf_means']:
   l=bynode[row['node']];ins=l.get('early_tap_ps',{}).get(c,{'min':0,'max':0})
   out[c][row['node']]=dict(min=row['min_ps']+ins['min'],max=row['max_ps']+ins['max'],mean=row['mean_ps']+sum(ins.values())/2,pin_min=row['min_ps'],pin_max=row['max_ps'])
 return out
m=model();baseline=effective(m);targets={c:max(r['mean'] for r in baseline[c].values())+20. for c in ('TT','FF')}
# Standard final-stage delay is computed from the same exact ASAP7 NLDM cells,
# at the branch's declared load. Coarse sizing is refined only in this model.
stage={c:C._bilin(libs[c]['BUFx8_ASAP7_75t_R']['delay'],20.,libs[c]['BUFx8_ASAP7_75t_R']['cap']) for c in ('TT','FF')}
changes=[];serial=0
for iteration in range(4):
 ef=effective(m);nd={n['name']:n for n in t['nodes']};added=0
 for leaf in t['leaves']:
  old=leaf['node'];delta={c:targets[c]-ef[c][old]['mean'] for c in ('TT','FF')}
  counts=[max(0,int(math.floor(delta[c]/stage[c]+.5))) for c in ('TT','FF')]
  count=min(range(max(counts+[0])+2),key=lambda n:sum(((delta[c]-n*stage[c])/stage[c])**2 for c in ('TT','FF')))
  if not count:continue
  origin=nd[old]['xy_um'];parent=old
  for k in range(count):
   serial+=1;name=f'mp_electrical_leaf_{serial}'
   # Deterministic plan sites in the leaf's macro-clear island. No sink moves.
   xy=planner.legal([origin[0]+.81*(k%8+1),origin[1]+.54*(k//8)])
   n=dict(name=name,parent=parent,xy_um=xy,master='BUFx8_ASAP7_75t_R');t['nodes'].append(n);nd[name]=n;parent=name
  leaf['node']=parent;added+=count;changes.append(dict(iteration=iteration,old_leaf=old,new_leaf=parent,stages=count,prior_deficit_ps=delta))
 if not added:break
 print('ALLLEAF_ROUND',iteration,'added',added,'target',targets,flush=True);m=model()
final=effective(m);summary={}
for c in ('TT','FF'):
 vals=final[c].values();lo=min(r['min'] for r in vals);hi=max(r['max'] for r in vals)
 summary[c]=dict(effective_min_ps=lo,effective_max_ps=hi,window_ps=hi-lo,target_ps=targets[c],slew_max_ps=m['corners'][c]['slew_max_ps'])
# Model fields for the proposed shared electrical compiler; original source
# stage_basis remains total until the passing shared extension is adopted.
for leaf in t['leaves']:
 leaf['pin_latency_ps']={c:{'min':final[c][leaf['node']]['pin_min'],'max':final[c][leaf['node']]['pin_max']} for c in ('TT','FF')}
t['latency_target_ps']=targets;t['electrical_model']=dict(measured_timing_used=False,model=m['basis'],corners=summary)
report=dict(scope='MODEL ONLY - no physical gates run',basis=m['basis'],signed_insertion_unchanged=True,measured_timing_used=False,clock_nodes=len(t['nodes']),added_nodes=serial,added_buf_area_um2=serial*.648*.27,targets=targets,standard_stage_ps=stage,corners=summary,changes=changes)
(p/'plans/nl_electrical_all.json').write_text(json.dumps(sl,indent=1)+'\n');(p/'nl_electrical_all_model.json').write_text(json.dumps(m,indent=1)+'\n');(p/'nl_electrical_all_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='changes'}),flush=True)
