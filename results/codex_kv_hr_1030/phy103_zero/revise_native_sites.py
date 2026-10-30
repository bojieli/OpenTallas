from pathlib import Path
import json,collections,math,copy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;WT=Path('/srv/opentallas-scratch/claude/wt/codex-kv-hr-1030/results/codex_kv_hr_1030/phy103_zero')
d=json.load(open(WT/'mux1_ff_plan.json'));raw=[l.split('\t')for l in(P/'native_sites.tsv').read_text().splitlines()];u=int(next(a[1]for a in raw if a[0]=='U'));rows=[{'orient':a[2],'b':list(map(int,a[3:7])),'sw':int(a[7]),'rh':int(a[8])}for a in raw if a[0]=='R'];cells={a[1]:{'m':a[2],'status':a[3],'orient':a[4],'b':list(map(int,a[5:9]))}for a in raw if a[0]=='C'};names={c['cell']for c in d['cells']};obs=[c['b']for n,c in cells.items()if n not in names and c['status']in['FIRM','FIXED','LOCKED']];halo=[round(v*u)for v in d['halo_bbox']]
def over(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
static_by_y={};occ_by_y={}
def legal(b,occ):
 key=(b[1],b[3])
 if key not in static_by_y:static_by_y[key]=[o for o in obs+[halo]if b[1]<o[3] and b[3]>o[1]]
 return not any(over(b,o)for o in static_by_y[key]+(occ_by_y.get(b[1],[])if occ else []))
occ=[];new={};moved=[];needs=[]
for c in d['cells']:
 n=c['cell'];b=cells[n]['b']
 if legal(b,[]):new[n]=b;occ.append(b);occ_by_y.setdefault(b[1],[]).append(b)
 else:needs.append(n)
for n in needs:
 b=cells[n]['b'];w=b[2]-b[0];h=b[3]-b[1];choices=[]
 for r in rows:
  a=r['b']
  if abs(a[1]-b[1])>round(2.16*u):continue
  x0=a[0];low=x0;hi=a[2]-w
  xx=x0+round((b[0]-x0)/r['sw'])*r['sw']
  # All native sites within2.16um, then allow larger ifno local legal home.
  for j in range(-240,241):
   x=xx+j*r['sw'];bb=[x,a[1],x+w,a[1]+h]
   if x<low or x>hi or bb[3]>a[3] or not legal(bb,occ):continue
   cost=abs(x-b[0])+abs(a[1]-b[1]);choices.append((cost,abs(a[1]-b[1]),x,a[1],bb))
 if not choices:raise RuntimeError(('no free localhome',n))
 z=min(choices);new[n]=z[-1];occ.append(z[-1]);occ_by_y.setdefault(z[-1][1],[]).append(z[-1]);moved.append({'cell':n,'old_bbox':[v/u for v in b],'new_bbox':[v/u for v in z[-1]],'L1_um':z[0]/u})
# Native rows/sites/obstacles andall686pairAABBgates.
for n,b in new.items():
 assert any(b[1]==r['b'][1] and b[0]>=r['b'][0] and b[2]<=r['b'][2] and b[3]<=r['b'][3] and(b[0]-r['b'][0])%r['sw']==0 for r in rows),n
 assert not any(over(b,o)for o in obs+[halo]),n
for a,n in enumerate(new):
 for m in list(new)[a+1:]:assert not over(new[n],new[m]),(n,m)
nd=copy.deepcopy(d)
def bboxdist(p,b):return max(b[0]-p[0],0,p[0]-b[2])+max(b[1]-p[1],0,p[1]-b[3])
for c in nd['cells']:
 c['bbox']=[v/u for v in new[c['cell']]];c['estimated_bbox_L1_um']=bboxdist(c['target'],c['bbox'])
for path in nd['write_paths']:
 c=next(c for c in nd['cells']if c['cell']==path['capture_ff']);pts=path['points'];old=pts[0][:];pts[0]=c['bbox'][:2]
 if len(pts)>1 and abs(pts[1][1]-old[1])<1e-5:pts[1][1]=pts[0][1]
 path['estimated_L1_um']=sum(abs(b[0]-a[0])+abs(b[1]-a[1])for a,b in zip(pts,pts[1:]))
nd.update(status='NATIVE_FLOORPLAN_TAP_LEGAL_ESTIMATE_NOT_PLACED',max_public_pin_to_capture_bbox_estimate_um=max(c['estimated_bbox_L1_um']for c in nd['cells']if not' rb_cap['in c['role']),max_capture_to_write_macro_path_estimate_um=max(p['estimated_L1_um']for p in nd['write_paths']))
private=[c for c in nd['cells']if'rb_cap'in c['cell']];public=[c for c in nd['cells']if'rb_cap'not in c['cell']];nd['max_public_pin_to_capture_bbox_estimate_um']=max(c['estimated_bbox_L1_um']for c in public);nd['max_macro_rd_pin_to_rb_cap_bbox_um']=max(c['estimated_bbox_L1_um']for c in private);nd['native_guard']={'status':'PASS_FROM_ACTUAL_FLOORPLAN_ROWS_TAPS','count':686,'private_rbcap':128,'rows':len(rows),'fixed_obstacles':len(obs),'FF_FF_overlap':0,'TAP_macro_overlap':0,'off_row_site':0,'moved':len(moved),'maxL1move_um':max(c['L1_um']for c in moved)}
(P/'native_legal_ff_plan.json').write_text(json.dumps(nd,indent=1)+'\n');(P/'native_legal_moves.json').write_text(json.dumps(moved,indent=1)+'\n')
with(P/'phy_ff_sites_native.tsv').open('w')as f:
 for c in nd['cells']:
  b=c['bbox'];f.write('\t'.join(map(str,[c['cell'],c['master'],b[0],b[1],int('rb_cap'in c['cell'])]))+'\n')
fig,ax=plt.subplots(figsize=(12,10));ax.add_patch(Rectangle((0,0),103.68,95.04,fill=False,lw=2));mb=d['macro_bbox'];hb=d['halo_bbox'];ax.add_patch(Rectangle((hb[0],hb[1]),hb[2]-hb[0],hb[3]-hb[1],fc='#fff4dd',ec='orange',ls='--'));ax.add_patch(Rectangle((mb[0],mb[1]),mb[2]-mb[0],mb[3]-mb[1],fc='#d4d9e0',ec='black'));ax.text(59,47,'512 x128 M1 SRAM\n1cycle read; repairdisabled\nM5 overmacro legal',ha='center')
for b in obs:
 if(b[2]-b[0])/u>10:continue
 ax.add_patch(Rectangle((b[0]/u,b[1]/u),(b[2]-b[0])/u,(b[3]-b[1])/u,fc='black',alpha=.65))
for c in nd['cells']:
 b=c['bbox'];pr='rb_cap'in c['cell'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc='#b71c1c'if pr else'#126fb3'))
 if pr:
  p=c['target'];ax.plot([b[2],p[0]],[.5*(b[1]+b[3]),p[1]],c='#b71c1c',alpha=.2,lw=.3)
for p in nd['write_paths']:
 if p['macro_face']=='E':ax.plot([z[0]for z in p['points']],[z[1]for z in p['points']],c='#259233',alpha=.12,lw=.5)
ax.set_xlim(-2,106);ax.set_ylim(-2,98);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title(f'PHY103 native row/TAP-safe retained686 FF sites;327 homes moved <= {nd["native_guard"]["maxL1move_um"]:.3f}um\nBLUE558public; RED128rb_cap; BLACK actual1263TAPs; GREEN56Ewrite paths')
fig.tight_layout();fig.savefig(P/'native_legal_ff_plan.png',dpi=160);print(nd['native_guard']);print({k:v for k,v in nd.items()if k.startswith('max_')})
