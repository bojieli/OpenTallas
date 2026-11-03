from pathlib import Path
from collections import deque,Counter,defaultdict
import sys,re,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent;D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv');bus='i_kvpc_Q_N_o_next';prefix='u_cland_'+bus+'/'
# Preserve every real clock-cone cell, including generic BUF/INV names.
clock=set();q=[]
for cid,c in D.cells.items():
 if c[0]!='S':continue
 q.extend(n for n,clk in D.cell_in.get(cid,[])if clk)
seen=set()
while q:
 n=q.pop()
 if n in seen:continue
 seen.add(n);dr=D.nets[n][1]
 if not dr or dr[0]!='i':continue
 cid=dr[1];c=D.cells[cid]
 if c[0]=='S':continue
 clock.add(cid);q.extend(nn for nn,clk in D.cell_in.get(cid,[])if not clk)
comb={cid for cid,c in D.cells.items()if prefix in c[6]and c[0]in'BLK'and cid not in clock}
mask=defaultdict(int);semantic={}
for cid,c in D.cells.items():
 if c[0]!='S'or prefix not in c[6]:continue
 n=c[6].replace(chr(92),'');m=re.search(r's_d\[(\d+)\]\[(\d+)\]',n)
 if m:bit=int(m[2])
 else:
  m=re.search(r'dch\[(\d+)\].u_dsel/y\[(\d+)\]',n)
  if not m:continue
  bit=int(m[1])*64+int(m[2])
 if bit>=300:continue
 semantic[cid]=bit
 for ni,ck in D.cell_in.get(cid,[]):
  if ck:continue
  dr=D.nets[ni][1]
  if dr and dr[0]=='i'and dr[1]in comb:mask[dr[1]]|=1<<bit
prev=defaultdict(set);succ=defaultdict(set)
for cid in comb:
 for ni,ck in D.cell_in.get(cid,[]):
  if ck:continue
  dr=D.nets[ni][1]
  if dr and dr[0]=='i'and dr[1]in comb:prev[cid].add(dr[1]);succ[dr[1]].add(cid)
ind={c:len(prev[c])for c in comb};queue=deque(sorted(c for c in comb if not ind[c]));order=[]
while queue:
 c=queue.popleft();order.append(c)
 for d in succ[c]:
  ind[d]-=1
  if ind[d]==0:queue.append(d)
assert len(order)==len(comb),'comb loop'
for c in reversed(order):
 for p in prev[c]:mask[p]|=mask[c]
groups=defaultdict(list);shared=[];unknown=[]
for cid in sorted(comb):
 b=mask[cid]
 if b and b&(b-1)==0:groups[(b.bit_length()-1)//75].append(cid)
 elif b:shared.append(cid)
 else:unknown.append(cid)
res={'scope':'STATIC ONLY; exact actual hroot completed PLACE connectivity; no CAD/source event','semantic_data_ff':len(semantic),'ring_comb_total':sum(prefix in c[6]and c[0]in'BLK'for c in D.cells.values()),'excluded_real_clock_cone':sum(prefix in D.cells[c][6]for c in clock),'single_bit_group_counts':{str(k):len(v)for k,v in groups.items()},'shared_control_cells':len(shared),'unowned_or_output_buffers':len(unknown),'groups':{str(k):[D.cells[c][6]for c in v]for k,v in groups.items()},'shared_names':[D.cells[c][6]for c in shared],'unknown_names':[D.cells[c][6]for c in unknown]}
(P/'cone_census.json').write_text(json.dumps(res,indent=1)+'\n');print({k:v for k,v in res.items()if k not in['groups','shared_names','unknown_names']})
