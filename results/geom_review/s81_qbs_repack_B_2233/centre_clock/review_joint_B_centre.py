from pathlib import Path
import json,sys,math,collections
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');C=json.load(open(P/'repack_B_centre_complete.json'));A=json.load(open(P/'legal_joint_B_centre.json'));D=G.Design(P/'geom.tsv');fixed={r['cid']for r in C['fixed']};sx=.054;sy=.270;rows=C['rows'];xs=min(r['origin'][0]for r in rows);ys=min(r['origin'][1]for r in rows);nx=11850;ny=2372;occ=np.zeros((ny,nx),np.uint8);rowranges=collections.defaultdict(list)
def reserve(b):
 i0=max(0,math.floor((b[0]-xs)/sx+1e-6));i1=min(nx,math.ceil((b[2]-xs)/sx-1e-6));j0=max(0,math.floor((b[1]-ys)/sy+1e-6));j1=min(ny,math.ceil((b[3]-ys)/sy-1e-6));occ[j0:j1,i0:i1]=1
for r in rows:
 i=round((r['origin'][0]-xs)/sx);j=round((r['origin'][1]-ys)/sy);rowranges[j].append((i,i+r['count'],r['orient']))
for f in C['fixed']:
 if f['cid']in D.cells and D.kind(f['cid'])=='S':continue
 b=f['bbox_um'];m=4.32 if f['cid']in D.cells and D.kind(f['cid'])=='M'else 0;reserve([b[0]-m,b[1]-m,b[2]+m,b[3]+m])
reserve(C['proposal']['clock_entry']['driver_bay_um']);errors=[];moved=0
for a in sorted(A['anchors'],key=lambda a:a['cid']not in fixed):
 cid=a['cid'];x,y=a['origin_um'];w,h=a['size_um'];i=round((x-xs)/sx);j=round((y-ys)/sy);n=round(w/sx);r=[v for v in rowranges[j]if v[0]<=i and i+n<=v[1]]
 if abs(xs+i*sx-x)>1e-6 or abs(ys+j*sy-y)>1e-6 or len(r)!=1 or occ[j,i:i+n].any():errors.append([cid,'ROW_SITE_OR_OVERLAP'])
 if not a['preserve_original']and len(r)==1 and a['orient']!=r[0][2]:errors.append([cid,'ORIENT'])
 if cid in fixed and tuple(a['origin_um'])!=D.cells[cid][2:4]:errors.append([cid,'FIXED_FACE_MOVED'])
 occ[j,i:i+n]=2
 if not a['preserve_original']:moved+=1
 c=D.cells[cid];D.cells[cid]=(c[0],c[1],x,y,x+w,y+h,c[6])
for m in C['macros'].values():
 c=D.cells[m['cid']];D.cells[m['cid']]=(c[0],c[1],*m['bbox_um'],c[6])
metric=G.r2r_metrics(D)
S=dict(A['summary'],independent_occupancy_errors=len(errors),actual_lattice_rows=len(rows),movedFF=moved,preserved_fixed_faceFF=1801,historical_tapcells=36783,macrohalos_um=4.32,independent_full_G_r2r=metric,errors=errors)
(P/'review_joint_B_centre.json').write_text(json.dumps(S,indent=2));print(json.dumps(S,indent=2))
with(P/'projected_geom_joint_B_centre.tsv').open('w')as out:
 for l in(P/'geom.tsv').read_text().splitlines():
  f=l.split('\t')
  if f[0]=='C'and int(f[1])in D.cells:f[4:8]=[f'{v:.4f}'for v in D.cells[int(f[1])][2:6]];l='\t'.join(f)
  out.write(l+'\n')
fig,axs=plt.subplots(1,2,figsize=(15,8));base=G.Design(P/'geom.tsv');am={a['cid']:a for a in A['anchors']};changed={c['cid']for c in C['proposal']['changes']}
for ax,new in zip(axs,(False,True)):
 dd=D if new else base
 for cid,c in dd.cells.items():
  if c[0]=='M':
   ax.add_patch(Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3],facecolor='#e0c192'if cid in changed else'#e7dfd3',edgecolor='#634627',lw=.7))
   if new and cid in changed:
    old=base.cells[cid];p=G.ctr(old);q=G.ctr(c);ax.annotate('',xy=q,xytext=p,arrowprops=dict(arrowstyle='->',color='#b04533',lw=.9))
 for preserve,color,size in ((True,'#b7c2cb',.6),(False,'#1266b5',1.1)):
  pp=[G.ctr(dd.cells[cid])for cid,a in am.items()if a['preserve_original']==preserve and cid not in fixed];ax.scatter([p[0]for p in pp],[p[1]for p in pp],s=size,c=color,rasterized=True)
 pp=[G.ctr(dd.cells[cid])for cid in am if cid in fixed];ax.scatter([p[0]for p in pp],[p[1]for p in pp],s=1,c='black')
 ax.set_xlim(0,648);ax.set_ylim(0,648);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title('Original: 939 FF captures >405um'if not new else'B model: all31,847 FFs anchored; 0 FF/macro hops >405um')
b=C['proposal']['clock_entry']['driver_bay_um'];axs[1].add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],facecolor='#30bb66',edgecolor='green',lw=1));axs[1].annotate('M5 ck + driver bay',xy=(324.012,331.212),xytext=(190,345),color='green',arrowprops=dict(arrowstyle='->',color='green'));fig.suptitle('DISABLED zero-cycle internal repack B — 16/32 macros move; data/reset face FFs/pins unchanged; physical ck entry moved\nModel on historical row/tap capacity only; future rows/taps/PG/CTS regeneration required; NO CAD')
fig.tight_layout();fig.savefig(P/'repack_B_centre_model.png',dpi=150)
