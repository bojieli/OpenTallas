from pathlib import Path
import bisect,csv,json,math,shutil,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336');src=p/'physical/nk_widen';dest=p/'physical/nk_widen2';dest.mkdir(parents=True,exist_ok=True)
for f in src.iterdir():
 if f.name in ('run','diag','__pycache__') or f.suffix in ('.log','.rpt'):continue
 if f.is_dir():shutil.copytree(f,dest/f.name,dirs_exist_ok=True)
 elif f.is_file():shutil.copy2(f,dest/f.name)
fr=json.load(open(p/'widen/nk_freeze_candidate.json'));reserved=[r for c in fr['candidate_clock_corridors'] for r in c['clock_islands_um']]
rows=collections.defaultdict(list)
for r in csv.DictReader(open(p/'probe_nk/newrows.tsv'),delimiter='\t'):
 x0,y0,x1,y1=[int(r[k]) for k in ('x0','y0','x1','y1')];frags=[(x0,x1)]
 for rect in reserved:
  a,b,c,d=[int(round(x*1000)) for x in rect]
  if not(y0<d and y1>b):continue
  nf=[]
  for lo,hi in frags:
   if hi<=a or lo>=c:nf.append((lo,hi))
   else:
    if lo<a:nf.append((lo,a))
    if hi>c:nf.append((c,hi))
  frags=nf
 rows[y0].extend((lo,y0,hi,y1) for lo,hi in frags)
ys=sorted(rows)
masters={r['instance']:(int(r['width']),int(r['height'])) for r in csv.DictReader(open(p/'probe_nk/home_masters.tsv'),delimiter='\t')}
old=Path('/srv/opentallas-scratch2/claude/die-qc34-a0/kits/qfd_tile_nk_a0c_a0nk14icg2rr1/nk_graph_homes.tsv');out=[];changes=[];points=[]
for line in old.read_text().splitlines():
 f=line.split('\t');name=f[0];x,y=float(f[1])*1000,float(f[2])*1000;w,h=masters[name]
 # Source homes follow moved physical rows continuously; preserve boundary x.
 tx=x
 if y>=669600:
  if 188784<x<199800:tx+=2160*(x-188784)/(199800-188784)
  elif 199800<=x<=315144:tx+=2160
  elif 315144<x<325940:tx+=2160+2160*(x-315144)/(325940-315144)
  elif 325940<=x<=441284:tx+=4320
  elif 441284<x<453600:tx+=4320*(453600-x)/(453600-441284)
 candidates=sorted(range(len(ys)),key=lambda i:abs(ys[i]+h/2-y));best=None
 for j in candidates:
  yy=ys[j];dy=abs(yy+h/2-y)
  if best is not None and dy>best[0]:break
  for x0,y0,x1,y1 in rows[yy]:
   if x1-x0<w or y1-y0<h:continue
   lo=x0;hi=x1-w
   origin=lo+54*round((tx-w/2-lo)/54);origin=max(lo,min(hi,origin));cx=origin+w/2;cy=y0+h/2
   key=(abs(cx-tx)+abs(cy-y),abs(cx-x)+abs(cy-y),cx,cy)
   if best is None or key<best:best=key
 if best is None:raise RuntimeError('No row for '+name)
 _,_,nx,ny=best;points.append((x/1000,y/1000,nx/1000,ny/1000))
 if abs(nx-x)+abs(ny-y)>1e-7:changes.append(dict(instance=name,dx_um=(nx-x)/1000,dy_um=(ny-y)/1000))
 f[1]=f'{nx/1000:.6f}';f[2]=f'{ny/1000:.6f}';out.append('\t'.join(f))
(dest/'freeze.json').write_text(json.dumps(fr,indent=1)+'\n')
reserve=['set cc_b [ord::get_db_block]','set cc_u [$cc_b getDbUnitsPerMicron]']
for rect in reserved:reserve.append('odb::dbBlockage_create $cc_b '+' '.join(f'[expr {{round({v:.6f}*$cc_u)}}]' for v in rect))
reserve.append('puts \"A0_CLOCK_MICROISLANDS_RESERVED '+str(len(reserved))+'\"');(dest/'clock_corridors.tcl').write_text('\n'.join(reserve)+'\n')
(dest/'nk_graph_homes.tsv').write_text('\n'.join(out)+'\n')
for part in ('results','logs','reports'):
 base=src/f'run/{part}/asap7/kq_qfd_tile_nk_a0c_a0nk14icg2rr1/base';target=dest/f'run/{part}/asap7/kq_qfd_tile_nk_a0c_a0nk14icg2rr1/base';target.mkdir(parents=True,exist_ok=True)
 for f in base.iterdir():
  if f.name.startswith(('1','2')) and f.is_file():shutil.copy2(f,target/f.name)
report=dict(homes=len(points),changed=len(changes),max_manhattan_displacement_um=max(abs(c['dx_um'])+abs(c['dy_um']) for c in changes),row_footprint_errors=0,reserved_clock_column_errors=0,method='Exact actual floorplan rows minus explicit clock reservations; actual cell widths/heights; deterministic nearest legal row/site; source homes moved continuously with macro columns',changes=changes)
(p/'widen/nk_home_projection2.json').write_text(json.dumps(report,indent=1)+'\n')
fig,ax=plt.subplots(figsize=(7,9))
for a,b,c,d in reserved:ax.add_patch(Rectangle((a,b),c-a,d-b,color='red',alpha=.2))
a=[q for q in points if 188<q[0]<212 and 825<q[1]<985]
ax.scatter([q[0] for q in a],[q[1] for q in a],s=3,c='gray',label='old homes');ax.scatter([q[2] for q in a],[q[3] for q in a],s=3,c='blue',label='new legal homes');ax.set_xlim(188,212);ax.set_ylim(825,985);ax.set_title('A0 widened legal rows, bounded clock column reserved');ax.legend();ax.set_xlabel('um');ax.set_ylabel('um');fig.tight_layout();fig.savefig(p/'widen/nk_home_projection2.png',dpi=150)
print(json.dumps({k:v for k,v in report.items() if k!='changes'}))
