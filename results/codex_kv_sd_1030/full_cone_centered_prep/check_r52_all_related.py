from pathlib import Path
import sys,json,gzip,collections
r=Path(__file__).resolve().parent;sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-kv-sd-1030/tools/autopilot');from geom_rules import Design
D=Design(r/'kits_anchor_v2/kv3_sys_SD/mapped_net_graph.tsv')
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
with gzip.open(r/'sd_r52_all_ff_related_pairs.json.gz','wt') as f:json.dump(out,f)
positions={z['instance']:z for z in json.load(open(r/'sd_r52_split_txup_full_xy_inventory.json'))};assert len(sources)==len(positions)==14000
bad=[];maxd=0;pairs=0;matrix=collections.Counter()
for row in rows:
 c=row['capture']
 if c not in positions:continue
 C=positions[c]
 for j in row['source_indices']:
  n=out['sources'][j];S=positions[n];dist=abs(S['xy_um'][0]-C['xy_um'][0])+abs(S['xy_um'][1]-C['xy_um'][1]);pairs+=1;maxd=max(maxd,dist);matrix[S['clock_net']+'->'+C['clock_net']]+=1
  if dist>405+1e-6:bad.append({'source':n,'capture':c,'L1_um':dist,'source_xy':S['xy_um'],'capture_xy':C['xy_um'],'source_basis':S['basis'],'capture_basis':C['basis']})
bad.sort(key=lambda z:-z['L1_um']);report={'qualified':False,'actual_current_ff_sources':len(sources),'actual_comb_cycles':0,'ff_pairs':pairs,'clock_domain_matrix':dict(matrix),'FFpair_max_L1_um':maxd,'over405':len(bad),'worst':bad[:60],'note':'All current FFs; includes reset/status overapproximation, no timing exceptions waived. XY remains proposed+old fallback as explicitly tagged. Macro per-pin and combinational path geometry pending.'}
(r/'sd_r52_split_related_reach.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='worst'},indent=2));print(json.dumps(bad[:15],indent=1))
