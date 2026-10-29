import json,sys,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
a=json.load(open(sys.argv[1]));b=json.load(open(sys.argv[2]))
fig,axs=plt.subplots(2,2,figsize=(14,12))
for row,tn in enumerate(['q_hub_nw','q_hub_ne']):
  for col,(lab,p) in enumerate([('before (d13)',a),('after (d14)',b)]):
    ax=axs[row][col];t=p['partition_types'][tn]
    for h in t['hard_cores']:
      x,y=h['origin_um'];w,hh=h['outline_um'];k=h['inst']
      c='red' if 'hcollgl_Q__q1' in k else 'blue' if 'ring_ag__q1' in k else 'orange' if 'hcollgi_Q__q1' in k or 'reduce__q1' in k or 'body' in k and 'q1' in k else 'grey'
      ax.add_patch(Rectangle((x,y),w,hh,fc=c,alpha=.35,ec='k',lw=.5))
      if c!='grey': ax.text(x+w/2,y+hh/2,k.replace('u_','').replace('_Q',''),fontsize=6,ha='center')
    for s in t['internal_stations']:
      if 'hcollgl' in s['conn'] or 'ring_ag' in s['conn']:
        pts=[s['from_um']]+s.get('regs_um',[])+[s['to_um']]
        if not (3600<pts[0][0]<5200 or 3600<pts[-1][0]<5200): continue
        ax.plot([q[0] for q in pts],[q[1] for q in pts],'-',lw=.6,color='green' if 'ag_' in s['conn'] else 'purple')
        ax.plot([q[0] for q in s.get('regs_um',[])],[q[1] for q in s.get('regs_um',[])],'.',ms=2,color='k')
    ax.set_xlim(3500,5300);ax.set_ylim(1700,3900);ax.set_aspect('equal');ax.set_title(f'{tn} {lab}: red=hcollgl q1, blue=ring_ag q1; green=ag->gl legs, purple=other gl/ring legs, dots=station FFs',fontsize=8)
fig.tight_layout();fig.savefig(sys.argv[3],dpi=110)
