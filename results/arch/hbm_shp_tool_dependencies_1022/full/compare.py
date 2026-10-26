from pathlib import Path
import re,json
root=Path(__file__).resolve().parent
out={};new=[]
for suite in ('closure_loop','ref_tile','hier_contract','tt_views'):
 data={}
 for side in ('baseline','candidate'):
  p=root/(side+'.'+suite+'.log')
  if not p.exists():continue
  s=p.read_text();cases=re.findall(r'^(?:ERROR|FAIL): (.*)$',s,re.M)
  data[side]={'problems':sorted(cases),'summary':re.findall(r'^Ran .*|^OK.*|^FAILED.*',s,re.M)}
 if len(data)==2:
  data['new_problems']=sorted(set(data['candidate']['problems'])-set(data['baseline']['problems']))
  data['removed_problems']=sorted(set(data['baseline']['problems'])-set(data['candidate']['problems']))
  new += [suite+': '+p for p in data['new_problems']]
 out[suite]=data
out['new_problems']=new
print(json.dumps(out,indent=2))
