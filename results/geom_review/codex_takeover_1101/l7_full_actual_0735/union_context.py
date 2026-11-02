from pathlib import Path
import json,sys
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
P=Path(__file__).parent/'result';D=g.Design(str(P/'geom.tsv'));h=json.loads((P/'sram_pincol_halo.json').read_text());rs=[tuple(r)for s in h['strips']for r in s['rects']];bs=[tuple(s['rect'])for s in h['strips']];ms=[tuple(c[2:6])for c in D.cells.values()if c[0]=='M']
def union(rs):
 xs=sorted({v for r in rs for v in(r[0],r[2])});out=0
 for x,y in zip(xs,xs[1:]):
  seg=sorted((r[1],r[3])for r in rs if r[0]<y and r[2]>x);length=0;lo=hi=None
  for a,b in seg:
   if hi is None:lo,hi=a,b
   elif a>hi:length+=hi-lo;lo,hi=a,b
   else:hi=max(hi,b)
  if hi is not None:length+=hi-lo
  out+=(y-x)*length
 return out
hits=[]
for c in D.cells.values():
 if c[0]=='M':continue
 for r in rs:
  if min(c[4],r[2])>max(c[2],r[0])+1e-7 and min(c[5],r[3])>max(c[3],r[1])+1e-7:hits.append(c[6]);break
out=dict(scope='Exact canonical source strip rects union, not broad overlapping strip bbox area; no native gate rewrite',macro_body_union_um2=union(ms),pincol_canonical_rects=len(rs),pincol_canonical_union_um2=union(rs),pincol_bbox_union_um2=union(bs),macro_plus_pincol_canonical_union_um2=union(ms+rs),functional_cells_intersecting_canonical_pincol_union=len(hits),sample=hits[:20],native_block_obstacle_records=sum(1 for s in(P/'native_obstacles.tsv').read_text().splitlines()if s.startswith('BLOCK_OBS')),note='Actual gate metrics computed from native macro body/OBS and actual connectivity. Pincol rects are preserved canonical row-cut context, not inflated bbox strip demands. Physical TAP excluded by normal geom dump; PG native audit separate.')
(P/'canonical_union_context.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=1))
