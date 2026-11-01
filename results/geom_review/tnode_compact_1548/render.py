import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;d=json.loads((P/'candidate.json').read_text());pins=json.loads((P/'candidate_plan_pins.json').read_text())['pins']
f,ax=plt.subplots(figsize=(12,9));W,H=d['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2))
for m in d['macros']:
 x0,y0,x1,y1=m['halo_rect'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ls='--',ec='#888888'))
 x0,y0,x1,y1=m['rect'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#c5ced7',ec='#364656'));ax.text((x0+x1)/2,(y0+y1)/2,m['instance']+'\n'+str(m['size'][0])+' x '+str(m['size'][1])+' R0',ha='center',va='center')
a=d['clock']['halo_rect'];ax.add_patch(Rectangle((a[0],a[1]),a[2]-a[0],a[3]-a[1],fc='#fae6bf',ec='#d48611',alpha=.6))
a=d['clock']['island_rect'];ax.add_patch(Rectangle((a[0],a[1]),a[2]-a[0],a[3]-a[1],fill=False,ec='#d48611'));ax.scatter([64.776],[64.8],marker='*',s=150,c='red',zorder=5);ax.text(75,65,'M5 root64.776,64.8\nPG64.8,64.8\n8.64 island +4.32 halo',fontsize=8,va='center')
colors={'W':'#236fa1','E':'#236fa1','N':'#b54382','S':'#b54382','internal':'red'}
for side in 'WENS':
 pp=[p for p in pins if p['face']==side];ax.scatter([p['x'] for p in pp],[p['y'] for p in pp],s=4,c=colors[side],zorder=5)
pad=[p for p in pins if p['role']=='LIVE_FREE_PAD_INPUT'];ax.scatter([p['x'] for p in pad],[p['y'] for p in pad],s=25,c='#198c4d',marker='v',zorder=6)
ax.text(0,48,'ua271 / M4\nW: peak35/10um',ha='right',va='center',fontsize=9);ax.text(W,42,'uo271 +da173 / M4\nE: peak58/10um',ha='left',va='center',fontsize=9)
ax.text(W/2,H+2,'N: ub271 +6pad_k +pad_b +rst_n / M5; peak26/10um\nAll7 pad bits LIVE/free; physical pad rectangles UNSUPPLIED',ha='center',va='bottom',fontsize=9)
ax.text(W/2,-3,'S: dn173 +db173 / M5; peak33/10um',ha='center',va='top',fontsize=9)
ax.annotate('',xy=(15.168-4.32,56),xytext=(0,56),arrowprops=dict(arrowstyle='<->',color='#a65b17'));ax.text(5,58,'10.848',fontsize=8)
ax.annotate('',xy=(W,56),xytext=(15.168+94.824+4.32,56),arrowprops=dict(arrowstyle='<->',color='#a65b17'));ax.text(115,58,'10.968',fontsize=8)
ax.text(8,59,'Hcross10.872\nbetween halos',fontsize=8)
ax.set(xlim=(-22,W+29),ylim=(-8,H+15),aspect='equal',xlabel='um',ylabel='um',title='Native Tnode compact proposal125.28 x95.04 (PREP ONLY)\nActual std/free22.39%; source-clean std/free21.11%; no source/stage/tie changes')
f.text(.5,.01,'Parent outline+data-pin event REQUIRED; clock/PG global positions preserved only after all30 instance transforms.\nNo placement, clock-tree, channel-demand or timing PASS; no CAD launched.',ha='center',fontsize=9)
f.savefig(P/'proposal.png',dpi=170,bbox_inches='tight')
