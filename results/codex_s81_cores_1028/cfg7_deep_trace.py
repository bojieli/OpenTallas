#!/usr/bin/env python3
"""Account exact cfg7 post-hold paths rejected by the unchanged4-buffer geometry heuristic."""
import sys,json,re,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/autopilot'));import geom_rules as G
D=G.Design(sys.argv[1]);rows=[];unresolved=[]
def walk(p):
 n=D.pin_net.get(p['k']);todo=collections.deque([(n,[],[])]) if n is not None else collections.deque();seen=set();hits=[];other=[]
 while todo:
  ni,path,pts=todo.popleft()
  if ni in seen:continue
  seen.add(ni)
  sig,dr,sk=D.nets[ni]
  refs=[dr] if p['io']=='OUTPUT' else sk
  for q in refs:
   if not q or q[0]!='i' or q[2]:continue
   k=D.kind(q[1]);c=D.cells[q[1]];xy=G.ctr(c)
   if k=='S':hits.append((len(path),q[1],path,pts+[xy]));continue
   if k!='B':other.append((q[1],k));continue
   nxt=[x[0] for x in D.cell_in[q[1]] if not x[1]] if p['io']=='OUTPUT' else D.drives.get(q[1],[])
   for nn in nxt:todo.append((nn,path+[q[1]],pts+[xy]))
 if not hits:return None
 return min(hits,key=lambda h:(h[0],h[1]))
for p in D.pins:
 if p['sig'] in ('POWER','GROUND','CLOCK') or G.CLOCK_PIN_RE.search(p['name']) or re.search(G.STRAP_RE_DEFAULT,p['name']):continue
 h=walk(p)
 if h is None:unresolved.append(p['name']);continue
 depth,reg,path,pts=h
 if depth<=G.PINREG_DEPTH:continue
 coords=[(p['x'],p['y'])]+pts;edges=[abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(coords,coords[1:])]
 rows.append(dict(port=p['name'],direction=p['io'],buffers=depth,register=D.cells[reg][6],register_master=D.cells[reg][1],direct_um=round(abs(coords[0][0]-coords[-1][0])+abs(coords[0][1]-coords[-1][1]),4),path_um=round(sum(edges),4),max_hop_um=round(max(edges),4),chain=[dict(inst=D.cells[i][6],master=D.cells[i][1]) for i in path]))
res=dict(scope='Diagnostic only; default4-buffer classifier unchanged. Traverse onlyBUF/INV/HB, stop at firstsequential data endpoint; no logic/macro traversal.',default_depth=G.PINREG_DEPTH,deep_registered=len(rows),unresolved=unresolved,depth_histogram=dict(collections.Counter(r['buffers'] for r in rows)),masters=dict(collections.Counter(c['master'] for r in rows for c in r['chain'])),max_direct_um=max((r['direct_um'] for r in rows),default=0),max_path_um=max((r['path_um'] for r in rows),default=0),max_hop_um=max((r['max_hop_um'] for r in rows),default=0),paths=rows)
Path(sys.argv[2]).write_text(json.dumps(res,indent=2)+'\n');print(json.dumps({k:v for k,v in res.items() if k!='paths'},indent=2))
