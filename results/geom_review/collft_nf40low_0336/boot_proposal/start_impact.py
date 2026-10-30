from pathlib import Path
from collections import Counter
import sys,json
b=Path('/srv/opentallas-scratch2/claude/codex-collft-0336');sys.path.insert(0,str(b));import geom_rules as G
D=G.Design(b/'planned_geom_nf40low.tsv');out={}
for cid,c in D.cells.items():
 n=c[6]
 if not ('u_cland_origin/' in n or 'u_cland_rst_crec_rx_s1_i/' in n or 'u_rrl_9/' in n):continue
 if c[0]!='S':continue
 todo=[cid];seen={cid};caps=set()
 while todo:
  q=todo.pop()
  for net in D.drives.get(q,[]):
   for e in D.nets[net][2]:
    if e[0]!='i' or e[2]:continue
    k=e[1]
    if D.cells[k][0]=='S':caps.add(k)
    elif D.cells[k][0] in 'BLK' and k not in seen:seen.add(k);todo.append(k)
 cc=[dict(name=D.cells[k][6],xy=G.ctr(D.cells[k]),distance=round(sum(abs(a-z) for a,z in zip(G.ctr(c),G.ctr(D.cells[k]))),3)) for k in sorted(caps)]
 out[n]=dict(xy=G.ctr(c),captures=cc,roles=dict(Counter(x['name'].split('/')[0] for x in cc)))
(b/'start_impact_census.json').write_text(json.dumps(out,indent=2)+'\n')
for n,v in out.items():print(n,v['xy'],len(v['captures']),v['roles'])
