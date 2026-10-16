import json,gzip
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path('/home/ubuntu/artifacts/s81-netfill-0253/qbank/frame_candidate');plan=json.load(gzip.open('/home/ubuntu/artifacts/s81-connected-0305/first_pass_plan_17b.json.gz','rt'));old={i['name']:i for i in plan['insts']};changes=json.load(open(p/'proof/transforms.json'));new=dict(old)
for r in changes:new[r['instance']]=r['candidate']
colors={'q':'#72b7b2','qbank':'#e45756','cfg':'#f2cf5b','seq':'#b279a2','bf':'#4c78a8','bfcol':'#4c78a8','sstn':'#ff9da6','cfifo':'#9d755d'}
fig,axs=plt.subplots(1,2,figsize=(15,8),layout='constrained')
for ax,src,title in zip(axs,[old,new],['17b initial generated slots (not final adoption)','Opt-in source replay: S25.92 / N8.64, q slots +21.60um']):
 for n,i in src.items():
  if i.get('region')!='frame_0' or i['kind'] not in colors:continue
  if i['y']>4350 or i['y']+i['h']<3020:continue
  ax.add_patch(Rectangle((i['x'],i['y']),i['w'],i['h'],facecolor=colors[i['kind']],edgecolor='black',lw=.5,alpha=.65))
  if src is old and i['kind']=='qbank':
   ah=25.92 if i['master'].endswith('_S') else 8.64
   ax.add_patch(Rectangle((i['x'],i['y']),60.48,ah,fill=False,edgecolor='red',linestyle='--',lw=1))
  if i['kind'] in ['qbank','q','bf','seq','sstn','cfifo']:ax.text(i['x']+i['w']/2,i['y']+i['h']/2,n,ha='center',va='center',fontsize=7,clip_on=True)
 ax.set_xlim(2615,3768);ax.set_ylim(3020,4350);ax.set_aspect('equal');ax.set_title(title,fontsize=11);ax.set_xlabel('die X (um)');ax.set_ylabel('die Y (um)');ax.grid(alpha=.2)
fig.suptitle('Qbank frame 0: actual source field geometry; relay/clock/reset replan and full final GEN still required',fontsize=12)
fig.savefig(p/'frame0_before_candidate.png',dpi=150)
