#!/usr/bin/env python3
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,str(Path(__file__).parent))
from propose_sram_slots import ROOT,blob,S,station_cloud
D=Path(__file__).parent/'sram_proposal';j=json.loads((D/'proposal.json').read_text());P=S.Plan(json.loads(blob('physical/die_plan/qwen_compute/die_plan.json')))
colors={'ot_sram_1r1w_32x64_m1':'#2d8a84','ot_sram_1r1w_128x256_m1_r2c2':'#cd9634','ot_sram_1r1w_64x512_m1_r2c2':'#4a87bc','ot_sram_1r1w2c_64x546_m1':'#ad659e'}
def draw(ax,tn):
 t=P.types[tn];W,H=t['outline_um'];pts=station_cloud(P,tn)
 if len(pts):ax.scatter(pts[:,0],pts[:,1],s=.15,c='#7e8b99',alpha=.3,rasterized=True)
 for e in j['contents_append'][tn]:
  x,y=e['origin_um'];w,h=j['existing_views'][e['module']]['outline_um'];c=colors[e['module']]
  ax.add_patch(Rectangle((x-5.4,y-5.4),w+10.8,h+10.8,facecolor=c,edgecolor='none',alpha=.12))
  ax.add_patch(Rectangle((x,y),w,h,facecolor=c,edgecolor='black',linewidth=.3))
  label=e['inst'].split('.')[-3] if 'g_btb' in e['inst'] else e['inst'].split('.')[-4] if '.u_u_r' in e['inst'] else e['inst'].split('.')[-2]
  if '32x64' not in e['module']:ax.text(x+w/2,y+h/2,label,fontsize=5,ha='center',va='center')
 from propose_sram_slots import gen_phys
 for _,x,y in gen_phys.clock_pins(P,tn)+gen_phys.core_tap_pins(P,tn):ax.scatter(x,y,marker='*',c='#d02a45',s=35,zorder=4)
 ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',title=tn,xlabel='um',ylabel='um');ax.grid(alpha=.1)
fig,axs=plt.subplots(3,3,figsize=(13,18));
for ax,tn in zip(axs.flat,j['contents_append']):draw(ax,tn)
fig.suptitle('PROPOSED existing SRAM slots: grey=FT station points, red=existing clock taps\nNo interface/latency edits; 5.4um halos, all182 actual instances positioned; not adopted',fontsize=13);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(D/'all_types.png',dpi=160)
for tn in ('sle_st_a_v1','sle_st_b_v1','coll_n'):
 fig,ax=plt.subplots(figsize=(7,11));draw(ax,tn);fig.tight_layout();fig.savefig(D/(tn+'.png'),dpi=160);plt.close(fig)
