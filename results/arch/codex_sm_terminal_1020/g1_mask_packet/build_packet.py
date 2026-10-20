#!/usr/bin/env python3
import csv,json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'tools')
import check_macro_track_alignment as C
P=Path(__file__).resolve().parent
s=json.loads((P/'native_master_phase.json').read_text())
r=json.loads((P.parent/'mask_relay_plan.json').read_text())
with (P/'all_master_pins.tsv').open('w') as f:
 w=csv.writer(f,delimiter='\t');w.writerow(['inst','master_sha','orient','base_x','base_y','phase_y_um','pin','use','layer','x0','y0','x1','y1'])
 for ch in s['children']:
  lef=next(Path(ch['view']).glob('*.lef'));m=C.parse_lef(lef.read_text())[0]
  x,y=ch['track_legal_origin'];bx,by=ch['logical_lattice_origin']
  actual=C.check_placement(m,ch['orient'],round(x*1000),round(y*1000))
  assert sum(z['offtrack'] for z in actual['layers'].values())==0,ch
  if ch['physical_phase_nm']:
   assert ch['orient']=='MX' and sum(z['offtrack'] for z in ch['at_logical_origin']['layers'].values())>0
  for p in m['pins']:
   for layer,rect in p['rects']:
    a=C.transform_rect(rect,ch['orient'],m['W'],m['H'])
    w.writerow([ch['inst'],ch['lef_sha256'],ch['orient'],bx,by,y-by,p['name'],p['use'],layer,x+a[0]/1000,y+a[1]/1000,x+a[2]/1000,y+a[3]/1000])
fig,ax=plt.subplots(figsize=(8,12))
for name,master,x0,y0,x1,y1 in s['layout']['blocks']:
 ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#d4d6dc',edgecolor='#50545c'))
 ax.text((x0+x1)/2,(y0+y1)/2,name.replace('u_lf0.u_lh.',''),ha='center',va='center',fontsize=7,rotation=90 if y1-y0>x1-x0 else 0)
for k,st in enumerate(r['stations']):
 x0,y0,x1,y1=st['box'];h=max(2,y1-y0)
 ax.add_patch(Rectangle((x0,y0),x1-x0,h,facecolor='#e650a4',edgecolor='#9e0060'))
 ax.text((x0+x1)/2,y1+8,st['name'],ha='center',fontsize=8,color='#9e0060')
 if k:
  a=r['stations'][k-1]['box'];start=((a[0]+a[2])/2,(a[1]+a[3])/2);end=((x0+x1)/2,(y0+y1)/2)
  if k in (2,3,4):
   routex={2:356,3:315,4:424}[k]
  if k==2:
   ax.plot([start[0],356,356,end[0]],[start[1],start[1],end[1],end[1]],color='#9e0060',lw=1.6)
   ax.add_patch(Rectangle((347,334),19.2,180,facecolor='#e650a4',alpha=.2))
  elif k in (3,4):
   ax.plot([start[0],routex,routex,end[0]],[start[1],start[1],end[1],end[1]],color='#9e0060',lw=1.6)
  else:
   ax.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','color':'#9e0060','lw':1.6})
  ax.text((start[0]+end[0])/2+8,(start[1]+end[1])/2,str(round(r['hops'][k-1].get('obstacle_aware_manhattan_um',r['hops'][k-1]['max_manhattan_um']),2))+'um max',fontsize=8,color='#9e0060')
b=r['additional_g1_bank']['box'];ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],facecolor='#5ca5e8'));ax.text(300,123,'G1 compute254FF',ha='center',fontsize=8,color='#1569a5')
ax.set(xlim=(0,457.92),ylim=(0,850),xlabel='um',ylabel='um')
ax.set_aspect('equal');ax.set_title('SM9 +2 compute / four spatial GN registers\nPLANNED exact closed-master rectangles; NOT PLACED\nOLD XS STAND-IN: NOT RELEASE BINDING',fontsize=11)
fig.tight_layout();fig.savefig(P/'north_spatial_relays.png',dpi=160)
print(P/'north_spatial_relays.png')
