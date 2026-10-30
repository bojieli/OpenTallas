"""Nominal planned clock-skew bound on actual placed data connectivity.
No timing/signoff claim. Macro spans use real characterized insertion, retained.
"""
from pathlib import Path
import sys,json,collections
p=Path.cwd();sys.path.insert(0,str(p/'geom_tools'));import geom_rules as G
plan,model,dump,out=sys.argv[1:];sl=json.load(open(plan));m=json.load(open(model));D=G.Design(dump);t=sl['core_tree'];norm=lambda n:n.replace(chr(92),'');clock={};lmap={l['node']:l for l in t['leaves']}
for corner in ('TT','FF'):
 cm={}
 for row in m['corners'][corner]['leaf_means']:
  l=lmap[row['node']];ins=l.get('early_tap_ps',{}).get(corner,dict(min=0,max=0));span=(row['min_ps']+ins['min'],row['max_ps']+ins['max'])
  for sink in l['sinks']:cm[norm(sink.rsplit('/',1)[0])]=span
 clock[corner]=cm
seq={c for c,v in D.cells.items()if v[0]=='S' or (v[1].startswith('ot_qwen_tile_'))};gates={c for c,v in D.cells.items()if v[1].startswith('ICG')};comb={c for c,v in D.cells.items()if v[0]in'BLK'}-gates
sources=collections.defaultdict(set);succ=collections.defaultdict(list);indeg=collections.Counter();E=set();enable=set()
for c in comb:
 for n in D.drives.get(c,[]):
  for s in D.nets[n][2]:
   if s[0]=='i' and not s[2] and s[1]in comb:succ[c].append(s[1]);indeg[s[1]]+=1
for c in seq:
 for n in D.drives.get(c,[]):
  for s in D.nets[n][2]:
   if s[0]!='i' or s[2]:continue
   if s[1]in seq:E.add((c,s[1]))
   elif s[1]in gates:enable.add((c,s[1]))
   elif s[1]in comb:sources[s[1]].add(c)
q=collections.deque(c for c in comb if indeg[c]==0);visited=0
while q:
 c=q.popleft();visited+=1;src=sources.get(c,set())
 for n in D.drives.get(c,[]):
  for s in D.nets[n][2]:
   if s[0]!='i'or s[2]:continue
   if s[1]in seq:E.update((a,s[1])for a in src)
   elif s[1]in gates:enable.update((a,s[1])for a in src)
   elif s[1]in comb:sources[s[1]]|=src
 for b in succ.get(c,[]):
  indeg[b]-=1
  if indeg[b]==0:q.append(b)
if visited!=len(comb):raise ValueError('Combinational loop/missing graph order')
answer={};missing=set()
for corner in ('TT','FF'):
 worst=[];classes=collections.defaultdict(list)
 for a,b in E:
  na,nb=norm(D.cells[a][6]),norm(D.cells[b][6])
  if na not in clock[corner]or nb not in clock[corner]:missing.add((na,nb));continue
  amin,amax=clock[corner][na];bmin,bmax=clock[corner][nb];skew=max(abs(amax-bmin),abs(bmax-amin));kind=('macro'if D.cells[a][1].startswith('ot_')else'FF')+'->'+('macro'if D.cells[b][1].startswith('ot_')else'FF')
  classes[kind].append(skew);worst.append((skew,kind,na,nb))
 answer[corner]=dict(pairs=len(worst),worst_ps=max(x[0]for x in worst),over80=sum(x[0]>80 for x in worst),by_class={k:dict(pairs=len(v),worst_ps=max(v),over80=sum(x>80 for x in v))for k,v in classes.items()},worst=sorted(worst,reverse=True)[:30])
report=dict(scope='Conservative NOMINAL PLAN skew bound from exact placed data connectivity; NOT SIGNOFF/CPPR/OCV',measured_timing_used=False,macro_real_insertion_spans_included=True,comb_cells=visited,physical_data_pairs=len(E),clock_gate_enable_pairs=len(enable),missing_clock_pairs=len(missing),missing_sample=sorted(missing)[:20],corners=answer)
Path(out).write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='corners'}));print(json.dumps({c:{k:v for k,v in r.items()if k!='worst'}for c,r in answer.items()}))
