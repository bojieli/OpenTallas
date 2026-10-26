import json,sys,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
geo,js,out=sys.argv[1:4];d=json.load(open(js))
fig,ax=plt.subplots(figsize=(12,9))
for l in open(geo):
  f=l.split()
  if f and f[0]=='MACRO':r=list(map(float,f[3:7]));ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='#ccd'))
  if f and f[0]=='SINK' and hash(f[4])%4==0:ax.plot(float(f[1]),float(f[2]),',',color='#999')
pos={n[0]:n[2] for n in d['nodes']}
col={'entry':'k','branch':'tab:blue','rep':'tab:green','leaf':'tab:red'}
for n,p,xy,m,k in d['nodes']:
  if p:ax.plot([pos[p][0],xy[0]],[pos[p][1],xy[1]],'-',lw=0.6,color='k',alpha=.5)
  ax.plot(*xy,'o' if k!='leaf' else 's',ms=3 if k!='entry' else 9,color=col[k])
for n,v in d['pred_leaf']['TT']['leaf'].items():
  ax.annotate('%.0f'%v[0],pos[n],fontsize=6,color='tab:red')
for k,v in d['sites'].items():
  if len(k)<=3 and k!='R':ax.plot(*v,'*',ms=14,color='orange');ax.annotate(k,v,fontsize=8)
p=d['pred'];ax.set_title('%s  model TT %.1f w%.1f / FF %.1f w%.1f (PLAN MODEL, UNCHECKED); lines = parent->child (actual wire = maze path)'%(js.split('/')[-1],p['TT']['mean'],p['TT']['window'],p['FF']['mean'],p['FF']['window']),fontsize=9)
ax.set_aspect('equal');plt.savefig(out,dpi=110,bbox_inches='tight')
