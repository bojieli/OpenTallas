import json,re,sys,matplotlib;matplotlib.use("Agg");import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from collections import Counter
p=json.load(open(sys.argv[1]));pos=p['positions'];T=p['targets'];out=sys.argv[2];title=sys.argv[3]
def d(a,b):return abs(pos[a][0]-pos[b][0])+abs(pos[a][1]-pos[b][1])
cls=[("p_cmd->emb_*/dvf/ea_c (svc cmd bcast)",r"u_svc\.p_cmd","#d62728"),("formatter wd_q/wa_q/we_q->g_safe",r"u_formatter\.w[dae]_q","#ff7f0e"),
("qseat->qb_row (read gather)",r"u_qseat\.","#2ca02c"),("f_dd->rep",r"u_qb\.f_dd","#17becf"),("dvf->slot obs",r"u_svc\.dvf","#9467bd")]
fig,ax=plt.subplots(figsize=(16,11),dpi=110)
for b in p['macros']:ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fc="#dddddd",ec="k",lw=0.6))
regs=p['registers'];ax.scatter([pos[r][0] for r in regs if r in pos],[pos[r][1] for r in regs if r in pos],s=0.2,c="#bbbbbb",label=f"regs ({len(regs)})")
lines={c[0]:[] for c in cls};lines['other']=[]
for s,t in T.items():
  for a in t['src']:
    if d(s,a)>405:
      an=a.replace('\\','')
      for c,rx,_ in cls:
        if re.search(rx,an):lines[c].append((a,s));break
      else:lines['other'].append((a,s))
cols=dict((c,col) for c,_,col in cls);cols['other']='k'
for c,L in lines.items():
  seen=set();n=0
  for a,s in L:
    k=(round(pos[a][0]/5),round(pos[a][1]/5),round(pos[s][0]/5),round(pos[s][1]/5))
    if k in seen:continue
    seen.add(k);ax.plot([pos[a][0],pos[s][0]],[pos[a][1],pos[s][1]],c=cols[c],lw=0.3,alpha=0.5)
  ax.plot([],[],c=cols[c],label=f"{c}: {len(L)} arcs >405")
# reset sources
R=p['reset_cones'];rs=Counter()
for pin,t in R.items():
  for e in t['ends']:
    if d(pin,e)>405 if e in pos and pin in pos else False:rs[e]+=1
for e,n in rs.most_common(10):ax.scatter([pos[e][0]],[pos[e][1]],marker='*',s=120,c='magenta')
ax.scatter([],[],marker='*',c='magenta',label=f"reset drivers w/ >405 sinks: {len(rs)} drivers, {sum(rs.values())} pins")
ax.set_xlim(0,777.6);ax.set_ylim(0,518.4);ax.set_aspect("equal");ax.legend(loc="upper left",fontsize=7,markerscale=3)
ax.set_title(title);fig.savefig(out,bbox_inches="tight")
print('reset drivers',[(e.replace('\\','')[:80],n,[round(v) for v in pos[e]]) for e,n in rs.most_common(8)])
