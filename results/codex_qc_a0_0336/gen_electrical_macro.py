"""A0 macro branch depth from pure NLDM+geometry; analytic MODEL ONLY.
Signed macro insertion unchanged. No measured clock arrival/hold target is read.
This does not emit an installable core kit.
"""
import sys,json,copy,statistics,collections,math
from pathlib import Path
p=Path.cwd();sys.path.insert(0,str(p/'src'));sys.path.insert(0,str(p/'tool_snapshot/tools/die_plan'))
import die_clock_128 as C
import core_infra_plan_metrics as M
# Reuse the immutable actual clock-pin capacitance/lib input parser.
sys.argv=['qualify2.py','plans/nl_affp.json','data/nl.tsv.gz','kit_nl','unused','unused']
e={"__file__":str(p/"src/qualify2.py")};exec((p/'src/qualify2.py').read_text().split('model=M.predict_tree')[0],e)
sl=e['sl'];libs=e['libs'];pts=e['pts'];caps=e['caps'];t=sl['core_tree'];t['electrical_latency_model_only']=True
# This flag is refused by install in our private modeling copy.
def model():return M.predict_tree(sl,libs,pts,caps,.018515*.8,.17137*.9,input_slew_ps=20.)
def means(m):
 out={}
 for c in ('TT','FF'):
  rows=m['corners'][c]['leaf_means'];target=statistics.median(r['mean_ps'] for r in rows if r['kind']=='register')
  out[c]={'target_ps':target,'macros':{r['node']:r['mean_ps'] for r in rows if r['kind']=='macro'}}
 return out
m=model();baseline=means(m);changes=[]
for iteration in range(12):
 q=means(m);nd={n['name']:n for n in t['nodes']};gd={g['inst']:g for g in t['gates']};allnodes={**nd,**gd}
 kids=collections.defaultdict(list)
 for name,n in allnodes.items():kids[n['parent']].append(name)
 leafnodes={l['node'] for l in t['leaves']};chosen=[]
 for leaf in t['leaves']:
  if leaf.get('load_class')!='macro':continue
  name=leaf['node']
  errs={c:q[c]['macros'][name]+sum(leaf['early_tap_ps'][c].values())/2-q[c]['target_ps'] for c in ('TT','FF')}
  if min(errs.values())<12:continue
  # Remove one unary repeater from the exclusive macro branch, without moving
  # any physical clock island, gate or macro, or crossing a branching point.
  chain=[];cur=name
  while cur in allnodes:
   n=allnodes[cur];parent=n['parent']
   if parent not in allnodes or len(kids[parent])!=1:break
   if parent in nd and parent not in leafnodes:
    grand=allnodes[parent]['parent']
    if grand in allnodes and len(kids[grand])==1:
     xy0=allnodes[grand]['xy_um'];xy1=n['xy_um'];xy=allnodes[parent]['xy_um']
     # Preserve a straight existing corridor: no corner-cutting or halo crossing.
     collinear=(abs(xy0[0]-xy[0])+abs(xy[0]-xy1[0])<=abs(xy0[0]-xy1[0])+1e-7 and abs(xy0[1]-xy[1])+abs(xy[1]-xy1[1])<=abs(xy0[1]-xy1[1])+1e-7)
     leg=abs(xy0[0]-xy1[0])+abs(xy0[1]-xy1[1])
     if collinear and leg<=80:chain.append((leg,parent,cur,grand))
   cur=parent
  if chain:
   leg,remove,child,parent=min(chain);chosen.append((remove,child,parent,errs))
 if not chosen:break
 old=copy.deepcopy(t['nodes']);removed=set()
 for remove,child,parent,errs in chosen:
  if remove in removed:continue
  allnodes[child]['parent']=parent;removed.add(remove);changes.append(dict(iteration=iteration,remove=remove,child=child,parent=parent,prior_error_ps=errs))
 t['nodes']=[n for n in t['nodes'] if n['name'] not in removed]
 m=model()
 print('ELECTRICAL_ROUND',iteration,'removed',len(removed),flush=True)
final=means(m)
report=dict(scope='MODEL ONLY: not a passing electrical candidate',basis=m['basis'],measured_timing_used=False,signed_insertion_unchanged=True,baseline=baseline,final=final,changes=changes)
(p/'plans/nl_electrical_macro.json').write_text(json.dumps(sl,indent=1)+'\n');(p/'nl_electrical_macro_model.json').write_text(json.dumps(m,indent=1)+'\n');(p/'nl_electrical_macro_report.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps(dict(changes=len(changes),baseline=baseline,final=final)),flush=True)
