import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
# Replay after align_selector_topk.py SRC OUT: python3 render.py OUT
import sys
r=Path(__file__).resolve().parent;pd=Path(sys.argv[1]);plan=json.load(open(pd/'die_plan.json'));root=plan['partition_types']['root'];cores={c['inst']:c for c in root['hard_cores']}
tc,sc=cores['u_hb_idx__link'],cores['u_hb_idx__selector'];assert tc['origin_um']==[34.56,0.0] and sc['origin_um']==[699.84,0.0], 'renderer is this C25b/C25c physical vehicle'
tp=json.load(open(pd/tc['pins_file']));sp=json.load(open(pd/sc['pins_file']));st=next(s for s in root['internal_stations'] if s.get('conn')=='u_hb_idx__link.selected_line|u_hb_idx__selector');bank=st['bit_sites_um'][0]
fig,axs=plt.subplots(1,3,figsize=(15,7),gridspec_kw={'width_ratios':[3,2,2]})
ax=axs[0]
for label,x,w,h,pins,flip in [('TOPK MY',34.56,650.16,500.04,tp,True),('SELECTOR R0',699.84,600.048,450.36,sp,False)]:
 ax.add_patch(Rectangle((x,0),w,h,fc='#ecf2f7',ec='black',lw=1.5));ax.text(x+w/2,h/2,label,ha='center',fontsize=11)
 for p in pins:
  px=x+(w-p['x'] if flip else p['x']);py=p['y'];m=p['name'].startswith('selected_line[');ax.plot(px,py,'.',color='#087f5b' if m else '#748494',ms=1.5 if m else .6)
ax.plot([692.28,692.28],[8.64,437.67],color='#e88713',lw=2,label='Existing relay; exact 2369 FFs');ax.set_xlim(0,1340);ax.set_ylim(-10,520);ax.set_aspect('equal');ax.legend(fontsize=8,loc='lower center');ax.set_title('True source SELECTOR → TOPK\nOpposite abutting faces; other pins untouched')
for ax,lo,hi,title in [(axs[1],0,450,'Physical gap and full FF bank'),(axs[2],220,225,'Zoom: row/site legal alternating FFs')]:
 ax.add_patch(Rectangle((675,-10),9.72,530,color='#dbe8f2'));ax.add_patch(Rectangle((699.84,-10),10,530,color='#dbe8f2'))
 for p in tp:
  if p['name'].startswith('selected_line[') and lo<=p['y']<=hi:ax.plot(684.624,p['y'],'.',color='#087f5b',ms=2)
 for p in sp:
  if p['name'].startswith('selected_line[') and lo<=p['y']<=hi:ax.plot(699.936,p['y'],'.',color='#087f5b',ms=2)
 for x,y in bank:
  if lo-.27<=y<=hi:ax.add_patch(Rectangle((x,y),1.404,.27,fc='#ffb656',ec='#ab6500',lw=.2))
 ax.set_xlim(682,702.5);ax.set_ylim(lo,hi);ax.set_title(title);ax.set_xlabel('root-local x (um)')
 if hi-lo<10:ax.set_aspect('equal')
axs[0].set_xlabel('root-local x (um)');axs[0].set_ylabel('um');fig.suptitle('TOPK/selector plan candidate: 2368 aligned bits; one unchanged relay, zero added cycles\nMax actual endpoint hop 8.493 um; W-face peaks 5.60/5.65 pins per um; FF gap fill 13.84%',fontsize=12);fig.tight_layout();fig.savefig(r/'selector_topk_abut.png',dpi=170)
