"""Usage: python3 plan.py placed-geom.tsv target-plan.json. Existing flops only; exact comb boundaries."""
import sys,re,json,collections,functools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/autopilot'))
import geom_rules as g
D=g.Design(sys.argv[1])
@functools.lru_cache(None)
def launch(cid):
 if D.kind(cid)=='S':return frozenset([cid])
 if D.kind(cid) not in 'BLK':return frozenset()
 out=set()
 for n,clk in D.cell_in[cid]:
  if clk:continue
  src=D.nets[n][1]
  if src and src[0]=='i':out.update(launch(src[1]))
 return frozenset(out)
adj=collections.defaultdict(set)
for cid,c in D.cells.items():
 if c[0]!='S':continue
 for n,clk in D.cell_in[cid]:
  if clk:continue
  s=D.nets[n][1]
  if s and s[0]=='i':
   for src in launch(s[1]):
    adj[cid].add(src);adj[src].add(cid)
coords={i:g.ctr(c) for i,c in D.cells.items()}
def name(i):return D.cells[i][6].replace('\\','')
mov=[i for i in D.cells if D.kind(i)=='S' and (re.search(r'^u_core[.]u_b[.]g_a\[\d+\][.]g_ais[.]u_a[dv]1/',name(i)) or name(i).startswith(('u_core.u_b.u_x.','u_core.row0_q[','u_core.b_en$','u_core.u_b.res_bits[','u_core.u_b.res_row[','u_bin_i/q','u_cland_origin/','u_cland_agg_1/','u_cland_agg_2/','u_core.rv_q[','u_core.go_q$','u_core.xv_q$','u_core.xvo_q$','u_core.goo_q$')))]
mov=[i for i in mov if name(i)!='u_core.u_b.u_x.genblk1.g_line.line[255]$_DFF_P_']
macros=[c[2:6] for c in D.cells.values() if c[0]=='M']
candidates=[]
for x in range(8,703,9):
 for y in range(8,1031,9):
  if not any(x0-2<x<x1+2 and y0-2<y<y1+2 for x0,y0,x1,y1 in macros):candidates.append((x,y))
def dist(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])
# Pair max + squared-over-reach penalty; retain physical locality if already safe.
for step in range(4):
 changed=0
 for i in mov:
  ns=adj[i]
  if not ns:continue
  pts=[coords[j] for j in ns if j!=i]
  if not pts:continue
  old=coords[i]
  def score(p):
   ds=[dist(p,q) for q in pts];bad=[max(0,d-380) for d in ds]
   return (max(bad),sum(v*v for v in bad),sum(ds),dist(p,old))
  best=min(candidates,key=score)
  if coords[i]!=best:changed+=1;coords[i]=best
 print('ITER',step,'changed',changed,flush=True)
 if changed==0:break
failed=[]
for i in mov:
 ds=[(dist(coords[i],coords[j]),j) for j in adj[i] if i!=j]
 if ds:
  d,j=max(ds)
  if d>405:failed.append((round(d,2),name(i),coords[i],name(j),coords[j]))
print('MOV',len(mov),'FAILED',len(failed));print(*sorted(failed,reverse=True)[:20],sep='\n')
json.dump({'positions':{D.cells[i][6]:coords[i] for i in mov},'failed':failed},open(sys.argv[2],'w'),indent=2)
