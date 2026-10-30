from pathlib import Path
from collections import Counter
import json,re,hashlib
B=Path(__file__).parent;out=[]
r=re.compile(r'^\s+(\w*ASAP7\w*)\s+(\\?\S+)\s*\(')
for p in sorted(B.glob('*.v')):
 groups={k:Counter() for k in range(1,7)};sg={k:Counter() for k in groups};masters=Counter();seq=Counter()
 for line in p.open():
  m=r.match(line)
  if not m:continue
  master,name=m.groups();name=name.lstrip('\\');parts=re.split('[/.]',name);s=bool(re.search('DFF|SDF|DHL|DLL|LQN',master));masters[master]+=1
  if s:seq[master]+=1
  for k in groups:
   g='.'.join(parts[:k]);groups[k][g]+=1
   if s:sg[k][g]+=1
 row=dict(type=p.stem,source=str(p),netlist_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),std=sum(masters.values()),seq=sum(seq.values()),hierarchy={str(k):[dict(prefix=g,std=c,seq=sg[k][g],comb=c-sg[k][g]) for g,c in groups[k].most_common(60)] for k in groups})
 out.append(row);print(p.stem,row['std'],row['seq']);print(json.dumps(row['hierarchy']['3'][:15]))
(B/'census.json').write_text(json.dumps({'scope':'Actual completed native synth ODB export; no count omissions, no cut adoption or physical claim','counts':out},indent=2)+'\n')
