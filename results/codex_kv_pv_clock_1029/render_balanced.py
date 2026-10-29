#!/usr/bin/env python3
"""Static clock-ownership review using actual placed-cell coordinates."""
import collections,json,re,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from group_pipeline_sinks import norm,family
base,successor,geom,report,out=map(Path,sys.argv[1:])
before=json.loads(base.read_text());after=json.loads(successor.read_text());rep=json.loads(report.read_text()); bal=json.loads((report.parent / ('balanced_fMX.json' if 'fMX' in out.name else 'balanced_R0.json')).read_text())
xy={};mac=[]
for l in geom.read_text().splitlines():
 a=l.split('\t')
 if a[0]=='C' and len(a)>=9:
  x0,y0,x1,y1=map(float,a[4:8]);xy[norm(a[8])]=((x0+x1)/2,(y0+y1)/2)
  if a[2]=='M':mac.append((x0,y0,x1,y1,a[8]))
colors=['#1879ba','#e48c20','#2a9d64','#8a4db9']
fig=plt.figure(figsize=(20.5,7.4),layout='constrained');gs=fig.add_gridspec(1,3,width_ratios=[1,1,.62])
axes=[fig.add_subplot(gs[0,0]),fig.add_subplot(gs[0,1])];table=fig.add_subplot(gs[0,2]);table.axis('off')
newgroups={}
for side,(d,ax,title)in enumerate(zip([before,after],axes,['Original: 28 FP families split between CTS roots','Successor: each complete FP family owns one root'])):
 ct=d['core_tree'];nodes={n['name']:n for n in ct['nodes']};groups=collections.defaultdict(list);fampos=collections.defaultdict(list);owners={}
 for leaf in ct['leaves']:
  if not leaf.get('cts_open'):continue
  root=leaf['node'];idx=int(root[-1]);owners[root]=0
  for s in leaf['sinks']:
   name=norm(s).rsplit('/',1)[0]
   if name not in xy:continue
   x,y=xy[name];groups[root].append((x,y));f=family(s)
   if f:fampos[f].append((x,y,root));newgroups[f]=root if side else newgroups.get(f)
  owners[root]=len(leaf['sinks'])
 for x0,y0,x1,y1,n in mac:
  ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#bfc6cc',edgecolor='#555f68',lw=.7,zorder=1,alpha=.65))
 for root,pts in groups.items():
  idx=int(root[-1]);px,py=zip(*pts);ax.scatter(px,py,s=.45,c=colors[idx],alpha=.45,rasterized=True,zorder=2)
  rx,ry=nodes[root]['xy_um'];ax.scatter([rx],[ry],s=190,marker='*',c=colors[idx],edgecolor='black',linewidth=.8,zorder=7)
  ax.annotate(root.replace('mp_pv_ck_','')+f'\n{owners[root]:,} FF',(rx,ry),xytext=(4,7),textcoords='offset points',fontsize=8,weight='bold',zorder=8)
 if side:
  for f,pts in fampos.items():
   x=sum(p[0]for p in pts)/len(pts);y=sum(p[1]for p in pts)/len(pts);root=pts[0][2];rx,ry=nodes[root]['xy_um']
   ax.plot([rx,x],[ry,y],color=colors[int(root[-1])],alpha=.45,lw=.7,zorder=4)
   m=re.match(r'u_s([01]).*\[(\d+)\]',f);label=m[1]+':'+m[2].zfill(2)
   ax.text(x,y,label,fontsize=6,color='#222',zorder=9)
 # Highlight all lane3 registers and the actual failed s1_bad/s2_bad pair.
 target='u_s0.u_slice.g_lane[3]';pts=fampos[target];px=[p[0]for p in pts];py=[p[1]for p in pts]
 ax.scatter(px,py,s=3,facecolors='none',edgecolors='#db195a',linewidth=.35,zorder=5)
 for suffix,marker in [('s1_bad','^'),('s2_bad','v')]:
  name=next(n for n in xy if n.startswith(target+'.u_prod.'+suffix+'$'))
  ax.scatter(*xy[name],s=55,marker=marker,c='#ff0055',edgecolor='black',lw=.5,zorder=10)
 ax.set_xlim(0,380.16);ax.set_ylim(0,190.08);ax.set_aspect('equal');ax.set_title(title,fontsize=11,pad=12)
 ax.set_xlabel('x (um)');ax.set_ylabel('y (um)');ax.grid(alpha=.15)
table.set_title('Complete family -> new root',fontsize=11,pad=12)
for slice_id in (0,1):
 x=.0+.52*slice_id;table.text(x,.95,f'Slice {slice_id}',weight='bold',fontsize=10,transform=table.transAxes)
 for lane in range(16):
  f=f'u_s{slice_id}.u_slice.g_lane[{lane}]';root=next(r['new']for r in rep['families_detail']if r['family']==f);idx=int(root[-1]);y=.9-lane*.045
  table.text(x,y,f'{slice_id}:{lane:02d}  ->  isl{idx}',color=colors[idx],fontsize=9,transform=table.transAxes,
             bbox=dict(facecolor='#ffe1eb',edgecolor='#db195a',lw=.5,pad=2)if(slice_id,lane)==(0,3)else None)
table.text(0,.12,'Magenta: complete s0 lane3\nTriangles: failed s1_bad / s2_bad\nGray: unchanged SRAM outlines\nStars: unchanged CTS island roots\nLines show family ownership',fontsize=8.5,transform=table.transAxes)
view='fMX'if'fMX' in out.name else'R0'
fig.suptitle(f'PV pair {view}: structural pipeline ownership, unchanged four-root clock geometry',fontsize=15,weight='bold')
fig.text(.01,.025,f"29,770 register sinks + 8 unchanged SRAM clock pins; 32 complete FP families + short non-FP chains intact; original equal root counts; max L1 root reach {bal['max_stub_L1_um']:.2f} um (<405); cycles added 0",fontsize=9)
fig.text(.01,.005,'R0 measured CTS witness: s1_bad CK175.12 / s2_bad CK278.40 ps, skew103.28 -> FFhold -97.44 ps. Successor timing not run. Macro clock branches/stages, pins, IO budget and RTL unchanged.',fontsize=8.5)
fig.savefig(out,dpi=140);print(out)
