from pathlib import Path
from collections import deque,Counter
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/head-wave-path-query-1102/hd_st_n3_turn/geom5/geom.tsv');by={c[6].replace(chr(92),''):i for i,c in D.cells.items()};root=by['u_cland_u1_i/_09276_'];q=deque(D.drives[root]);seen=set();buf=set();leaves=[];ports=[];boundary=[]
while q:
 n=q.popleft()
 if n in seen:continue
 seen.add(n)
 for s in D.nets[n][2]:
  if s[0]=='p':ports.append(D.pin_by_k[s[1]]['name']);continue
  i=s[1];c=D.cells[i];ins=[nn for nn,ck in D.cell_in.get(i,[])if not ck]
  if not s[2]and c[1].startswith('BUFx')and len(ins)==1and ins[0]==n:
   buf.add(i);q.extend(D.drives.get(i,[]))
  else:leaves.append(dict(instance=c[6],id=i,master=c[1],kind=c[0],clock=s[2],old_net_id=n,xy=list(g.ctr(c))))
res=dict(scope='Conditional same-function DATA BUF-tree alternative only; sourceframe still unqualified; no CAD/RTL/FF/cycle or clock edits',root=dict(name=D.cells[root][6],master=D.cells[root][1],xy=list(g.ctr(D.cells[root])),inputs=[dict(net_id=n,clock=ck,driver=str(D.nets[n][1]))for n,ck in D.cell_in[root]]),noninverting_existing_buffers=[dict(name=D.cells[i][6],master=D.cells[i][1],xy=list(g.ctr(D.cells[i])))for i in sorted(buf)],leaf_sink_pins=len(leaves),distinct_leaf_instances=len({r['instance']for r in leaves}),leaf_types=dict(Counter(r['master']for r in leaves)),clock_leafs=sum(r['clock']for r in leaves),public_ports=ports,old_internal_net_ids=sorted(seen),leaves=leaves)
(P/'forest.json').write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in['leaves','noninverting_existing_buffers']});print('existing BUF',len(buf))
