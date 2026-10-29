#!/usr/bin/env python3
import argparse,json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--windows',required=True);p.add_argument('--tools',required=True);p.add_argument('--out',required=True);a=p.parse_args();sys.path.insert(0,a.tools);import die_trial
plan=json.load(open(a.plan));windows=json.load(open(a.windows))['windows'];types=['kv3_hg_v3','kv3_sys_c','kv3_io_ft','kv3_phy'];fig,axs=plt.subplots(2,2,figsize=(15,14))
for ax,tn in zip(axs.flat,types):
 t=plan['partition_types'][tn];w,h=t['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fc='#eeeeee',ec='black'))
 for x,y,X,Y,*rest in die_trial.core_obs(t):ax.add_patch(Rectangle((x,y),X-x,Y-y,fc='#777777',ec='black',lw=.3))
 for x,y,X,Y in windows[tn]:ax.add_patch(Rectangle((x,y),X-x,Y-y,fc='#3366cc',ec='none'))
 pins=t.get('clock',{}).get('landing_contract',{}).get('pins',[])
 ax.scatter([q['xy_um'][0] for q in pins if q['name'].startswith('cland_tstart')],[q['xy_um'][1] for q in pins if q['name'].startswith('cland_tstart')],s=15,c='red')
 ax.set_xlim(-5,w+5);ax.set_ylim(-5,h+5);ax.set_aspect('equal');ax.set_title(f'{tn}: {len(windows[tn])} union windows, outline {w} x {h}um');ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('KV event27f: full clock + provider physical reservations\nBlue = common type-union islands; grey = hard cores; red = native START pins');plt.tight_layout();plt.savefig(a.out,dpi=100)
