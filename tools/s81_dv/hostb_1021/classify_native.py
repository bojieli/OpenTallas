#!/usr/bin/env python3
"""Label actual failed native cones by reachable real FF source state; no waiver."""
import sys,json,re
from pathlib import Path
from collections import defaultdict,Counter,deque
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'ref_tile'))
import native_census as N
r=Path(sys.argv[1]);roles,_=N.liberty_roles(sorted((r/'lib').glob('*.lib')))
reports=[]
for top in ('dsdv_hostb_stage','dsdv_hostb_return','dsdv_hostb_head'):
 d=r/top;x=json.load(open(d/'census.json'));mods=N.TL.parse_verilog((d/'flat.v').read_text());g,_=N.TL.flatten({k:v for k,v in mods.items() if k==top or k not in roles},top)
 aliases=defaultdict(list)
 for name,net in g.net_id.items():
  if not re.fullmatch(r'_\d+_(?:\[\d+\])?',name) and not name.startswith("1'"):aliases[g.find(net)].append(name)
 loads=defaultdict(list);outs={}
 for ci,(master,name,pins) in enumerate(g.cells):
  pr=roles[master]['pins'];on=[]
  for pin,ns in pins.items():
   role=pr[pin]
   if role['direction']=='output':on+=ns
   elif role['direction']=='input' and not role['clock']:
    for n in ns:loads[n].append(ci)
  outs[ci]=on
 rows=[]
 for v in x['violations']:
  root=g.net_id[v['net']];q=deque([(g.find(root),0)]);seen=set();ff=set()
  while q:
   n,dep=q.popleft()
   if n in seen or dep>5:continue
   seen.add(n)
   for ci in loads[n]:
    if roles[g.cells[ci][0]]['sequential']:ff.add(ci)
    else:q.extend((k,dep+1) for k in outs[ci])
  names=[]
  for ci in ff:
   for n in outs[ci]:
    aa=aliases[n];names.append(next((z for z in aa if '.' in z),aa[0] if aa else g.net_name[n]))
  families=Counter(re.sub(r'\[\d+\]','[]',z) for z in names)
  rows.append(dict(driver=v['driver'],net=v['net'],loads=v['loads'],source_aliases=aliases[g.find(root)],reachable_source_FF_families=dict(families)))
 reports.append(dict(top=top,status=x['status'],max_dynamic_loads=x['max_dynamic_loads'],violations=rows))
(r/'classification.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports,indent=2))
