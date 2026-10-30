from pathlib import Path
import sys,json,gzip,collections
r=Path(__file__).resolve().parent;sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-kv-sd-1030/tools/autopilot');from geom_rules import Design
D=Design(r/'kits_anchor_v2/kv3_sys_SD_v1/mapped_net_graph.tsv')
seq={i for i,c in D.cells.items() if c[0] in 'SM'};comb={i for i,c in D.cells.items() if c[0] in 'BLK'}
sources=sorted((i for i,c in D.cells.items() if c[0]=='S'),key=lambda i:D.cells[i][6]);state={i:1<<j for j,i in enumerate(sources)};caps=collections.defaultdict(int);succ=collections.defaultdict(list);indeg=collections.Counter()
for i in comb:
 for n in D.drives.get(i,[]):
  for s in D.nets[n][2]:
   if s[0]=='i' and not s[2] and s[1] in comb:succ[i].append(s[1]);indeg[s[1]]+=1
for i in sources:
 for n in D.drives.get(i,[]):
  for s in D.nets[n][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in seq:caps[s[1]]|=state[i]
   elif s[1] in comb:state[s[1]]=state.get(s[1],0)|state[i]
q=collections.deque(i for i in comb if indeg[i]==0);done=0
while q:
 i=q.popleft();done+=1;v=state.get(i,0)
 for n in D.drives.get(i,[]):
  for s in D.nets[n][2]:
   if s[0]!='i' or s[2]:continue
   if s[1] in seq:caps[s[1]]|=v
   elif s[1] in comb:state[s[1]]=state.get(s[1],0)|v
 for j in succ[i]:
  indeg[j]-=1
  if indeg[j]==0:q.append(j)
def bits(v):
 while v:
  b=v&-v;yield b.bit_length()-1;v-=b
assert len(comb)==done,(len(comb),done)
rows=[{'capture':D.cells[i][6],'source_indices':list(bits(v))} for i,v in caps.items() if v]
out={'scope':'CURRENT R52 actual SYNTH graph structural data/reset overapproximation; NOT STA/phase/legalization; macro boundary pins evaluated separately','source_odb':'kits_anchor_v2/kv3_sys_SD/1_synth.odb','comb_cycles':len(comb)-done,'sources':[D.cells[i][6] for i in sources],'captures':rows}
with gzip.open(r/'sd_v1_r52_all_ff_related_pairs.json.gz','wt') as f:json.dump(out,f)
