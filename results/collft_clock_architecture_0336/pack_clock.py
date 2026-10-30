"""Model-only finite actual-row packing; never writes ODB or runs placement."""
import json,gzip,csv,math,bisect,collections
from pathlib import Path
B=Path('/srv/opentallas-scratch2/claude/codex-collft-clock-0336');C=B/'census';plans=json.load(gzip.open(B/'tree_balanced_proposal.json.gz','rt'))
rows=list(csv.DictReader(open(C/'rows.tsv'),delimiter='\t'))
for r in rows:
 for k in r:
  if k not in ('name','orient'):r[k]=int(r[k])
rows.sort(key=lambda r:(r['y0'],r['ordinal']));ys=[r['y0']for r in rows];assert len(set(ys))==len(ys)
occ=[[]for r in rows];bodies=list(csv.DictReader(open(C/'all_bodies.tsv'),delimiter='\t'));kind=collections.Counter()
for b in bodies:
 x0,y0,x1,y1=[int(b[k])for k in ('x0','y0','x1','y1')];kind[b['master']]+=1
 for j in range(max(0,bisect.bisect_right(ys,y0)-1),min(len(rows),bisect.bisect_left(ys,y1))):
  r=rows[j]
  if y0<r['y1']and r['y0']<y1:occ[j].append((x0,x1))
# Keep ALL prior software intervals conservatively, even where a prior movable body later moved.
for q in csv.DictReader(open(C/'software_pre_anchor_occupancy.tsv'),delimiter='\t'):
 j=int(q['row']);assert rows[j]['y0']==4320+j*270;occ[j].append((int(q['lo']),int(q['hi'])))
free=[]
for r,vs in zip(rows,occ):
 merged=[]
 for a,b in sorted(vs):
  if a==b:continue
  if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
  else:merged.append((a,b))
 fs=[];x=r['x0']
 for a,b in merged:
  if a>x:fs.append((x,min(a,r['x1'])))
  x=max(x,b)
 if x<r['x1']:fs.append((x,r['x1']))
 free.append([(a,b)for a,b in fs if b>a])
dims={r['master']:(int(r['width']),int(r['height']))for r in csv.DictReader(open(C/'buffer_masters.tsv'),delimiter='\t')}
allnodes=[(root,n)for root,sl in plans.items()for n in sl['core_tree']['nodes']];allnodes.sort(key=lambda z:(-dims[z[1]['master']][0],z[0],z[1]['name']));moves=[]
for owner,n in allnodes:
 w,h=dims[n['master']];assert h==270;wantx=n['xy_um'][0]*1000-w/2;wanty=n['xy_um'][1]*1000-h/2;best=None
 # Examine candidate rows by vertical distance; exact minimum L1 on current free intervals.
 for j in sorted(range(len(rows)),key=lambda j:abs(rows[j]['y0']-wanty)):
  r=rows[j];dy=abs(r['y0']-wanty)
  if best and dy>best[0]:break
  site=r['site_width'];rx=r['rx']
  for k,(a,b)in enumerate(free[j]):
   lo=rx+math.ceil((a-rx)/site)*site;hi=rx+math.floor((b-w-rx)/site)*site
   if lo>hi:continue
   x=min(hi,max(lo,rx+round((wantx-rx)/site)*site));cost=abs(x-wantx)+dy
   v=(cost,j,k,x)
   if best is None or v<best:best=v
 if best is None:raise ValueError(('NO_LEGAL_CLOCK_SITE',owner,n['name']))
 cost,j,k,x=best;r=rows[j];a,b=free[j][k];free[j][k:k+1]=[(p,q)for p,q in ((a,x),(x+w,b))if q>p]
 old=n['xy_um'];n['body_origin_um']=[x/1000,r['y0']/1000];n['xy_um']=[(x+w/2)/1000,(r['y0']+h/2)/1000];n['orientation']=r['orient'];n['actual_row_name']=r['name'];moves.append(dict(name=n['name'],root=owner,master=n['master'],old_xy_um=old,new_xy_um=n['xy_um'],L1_um=cost/1000))
for owner,sl in plans.items():sl['core_tree']['coordinate_basis']='cell_centres';sl['packing_scope']='MODEL ONLY; final FF5 every-instance body + conservative prior software tails, no ODB installation'
with gzip.open(B/'tree_packed_proposal.json.gz','wt')as f:json.dump(plans,f)
report=dict(scope='MODEL ONLY exact legal row/site/body interval packing, existing bodies held; actual M7/M6 pin/via access and runtime ODB guards remain required',clock_cells=len(allnodes),actual_existing_bodies=len(bodies),actual_rows=len(rows),actual_tap_endcap_bodies=sum(v for k,v in kind.items()if 'TAPCELL' in k),max_clock_cell_L1_movement_um=max(v['L1_um']for v in moves),software_intervals='all pre-anchor intervals conservatively preserved; final actual standard-cell bodies added',no_ODB_write=True,moves=moves)
(B/'packing_report.json').write_text(json.dumps(report,indent=1));print({k:v for k,v in report.items()if k!='moves'})
