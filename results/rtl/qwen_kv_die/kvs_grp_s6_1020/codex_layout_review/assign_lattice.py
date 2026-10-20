import json
from pathlib import Path
r=Path(__file__).resolve().parent;a=json.loads((r/'layout_alternatives.json').read_text());g=json.loads((r/'grid.json').read_text());pts=a['every_origin_lattice_fixed_rows20channel']['height432_legal_positions'];ms=g['macros'];assert len(ms)==32 and len(pts)==36
cost=[[round((abs(m['bbox'][0]-p[0])+abs(m['bbox'][1]-p[1]))*1000) for p in pts] for m in ms];levels=sorted({v for row in cost for v in row})
def solve(lim):
 adj=[sorted((j for j,c in enumerate(row) if c<=lim),key=lambda j:row[j]) for row in cost];order=sorted(range(32),key=lambda i:len(adj[i]));owner={}
 def visit(i,seen):
  for j in adj[i]:
   if j in seen:continue
   seen.add(j)
   if j not in owner or visit(owner[j],seen):owner[j]=i;return True
  return False
 for i in order:
  if not visit(i,set()):return None
 return {i:j for j,i in owner.items()}
lo,hi=0,len(levels)-1
while lo<hi:
 mid=(lo+hi)//2
 if solve(levels[mid]) is None:lo=mid+1
 else:hi=mid
ans=solve(levels[lo]);assert ans is not None
out=dict(scope='MODEL ONLY: exact minimum bottleneck source-origin displacement on enumerated36legalpoints, not stage reach proof. Source/bytebank identities fixed; no extra FF/edges. New stage reaches/parent station replans remain unqualified.',outline_um=[388.8,432],minimum_possible_max_origin_L1_shift_um=levels[lo]/1000,preceding_infeasible_threshold_um=levels[lo-1]/1000 if lo else None,assignment=[dict(inst=ms[i]['inst'],master=ms[i]['master'],orient=ms[i]['orient'],old_origin_um=ms[i]['bbox'][:2],new_origin_um=pts[j],origin_L1_shift_um=cost[i][j]/1000) for i,j in sorted(ans.items())],free_origins_um=[p for j,p in enumerate(pts) if j not in ans.values()])
(r/'candidate_origins.json').write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items() if k not in ['assignment','free_origins_um']})
