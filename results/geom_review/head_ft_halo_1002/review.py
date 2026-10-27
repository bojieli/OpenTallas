import sys,json,math
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/wt/codex-head-tree-0830/tools/die_plan')
import schema as S,gen_phys as G,taps as T,die_clock_mesh as D
base=Path('/srv/opentallas-scratch2/claude/codex-head-ft-review-0958');P=S.Plan(S.load('/srv/opentallas-scratch2/claude/wt/codex-head-tree-0830/physical/die_plan/s81_head/die_plan.json'));spec=json.load(open('/srv/opentallas-scratch2/claude/codex-head-tree-0830/physical_interval_my_8fcd/explicit_tree.json'))
# Planning reconstruction of first-column face FF sites with exact pin order;
# core inset8.64, physical cell1.404x.27 envelope. Missing netlist sharing/DPL
# means positives are planning conflicts, absence is not physical signoff.
boxes={}; footprints={}
for tn,t in P.types.items():
 slots={s['name']:s for s in t.get('ft_slots',[])};pts=[];w,h=t['outline_um'];occ=set();pins=G.type_pins(P,tn)
 for name,bit,lay,x,y,face in pins:
  if name.endswith('_o') and name[:-2] in slots:continue
  if face in ('W','E'):
   row=int((y-8.64)/.27);got=None
   for c in range(400):
    for dr in [0,1,-1,2,-2]:
     r=row+dr
     if r<0 or (face,r,c) in occ:continue
     occ.add((face,r,c));xx=8.64+c*2.16 if face=='W' else w-8.64-c*2.16-1.404;yy=8.64+r*.27;got=(xx,yy);break
    if got:break
  else:
   col=int((x-8.64)/2.16);got=None
   for r in range(400):
    for dc in [0,1,-1]:
     c=col+dc
     if c<0 or (face,r,c) in occ:continue
     occ.add((face,r,c));xx=min(8.64+c*2.16,w-8.64-1.404);yy=8.64+r*.27 if face=='S' else h-8.64-(r+1)*.27;got=(xx,yy);break
    if got:break
  xx,yy=got;pts.append((xx,yy,xx+1.404,yy+.27,f'{name}[{bit}]','face_reconstruction'))
 # Exact per-bit slots are actual allocated envelopes, not centroid approximations.
 for sl in slots.values():
  if sl.get('bit_sites_um'):
   cw,ch=sl['bit_site_cell_um']
   for j,stage in enumerate(sl['bit_sites_um'],1):
    for bit,(x,y) in enumerate(stage):pts.append((x,y,x+cw,y+ch,f'{sl["name"]}:s{j}[{bit}]','exact_bit_site'))
 # Centroid-only station declarations cannot demonstrate zero halo conflicts.
 footprints[tn]=pts
hits=[];seen=set();rows=[]
for name,c in spec['cell_sites'].items():
 pn=c['part'];tn=P.parts[pn]['type'];x,y=c['origin_um'];cw=D.BUF_WIDTHS[c['master']];corners=[P.to_type(pn,v) for v in [(x,y),(x+cw,y+.27)]];a,b=min(q[0] for q in corners),min(q[1] for q in corners);X,Y=max(q[0] for q in corners),max(q[1] for q in corners)
 for xx,yy,XX,YY,fn,basis in footprints[tn]:
  if a<XX+2-1e-6 and X>xx-2+1e-6 and b<YY+2-1e-6 and Y>yy-2+1e-6:
   key=(name,fn)
   if key in seen:continue
   seen.add(key);hits.append(dict(clock=name,part=pn,type=tn,orient=P.orient(pn),clock_rect=[a,b,X,Y],ft=fn,ft_rect=[xx,yy,XX,YY],basis=basis,physical_overlap=a<XX and X>xx and b<YY and Y>yy))
 rows.append(dict(clock=name,part=pn,type=tn,orient=P.orient(pn),rect=[a,b,X,Y]))
from collections import Counter
out=dict(verdict='FAIL_PLANNING_HALO',halo_um=2,clock_cells=len(rows),conflict_pairs=len(hits),clock_cells_with_conflicts=len({v['clock'] for v in hits}),by_type=dict(Counter(v['type'] for v in hits)),physical_overlap_pairs=sum(v['physical_overlap'] for v in hits),caveat='Face reconstruction assumes full wrapper bus register census/core inset8.64,1.404x.27 envelope. Actual synthesized sharing/DPL not available; centroid-only FT internal banks not cleared by this check.',hits=hits,rows=rows)
(base/'ft_halo_review.json').write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items() if k not in ('hits','rows')});print(hits[:4])
