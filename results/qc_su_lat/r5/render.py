import json,sys,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
r=json.load(open(sys.argv[1]));geo=[l.split() for l in open(sys.argv[2])]
fig,ax=plt.subplots(figsize=(11,8))
for f in geo:
  if f[0]=='MACRO':x0,y0,x1,y1=map(float,f[3:7]);ax.add_patch(plt.Rectangle((x0,y0),x1-x0,y1-y0,color='#ccd'))
xs=[float(f[1]) for f in geo if f[0]=='SINK'];ys=[float(f[2]) for f in geo if f[0]=='SINK'];ax.scatter(xs,ys,s=0.3,c='#999')
pos={'root':tuple(r['entry'])};col={1:'r',2:'b',3:'g'}
for n,p,xy,c in r['nodes']:pos[n]=tuple(xy)
for n,p,xy,c in r['nodes']:
  ax.plot([pos[p][0],xy[0]],[pos[p][1],xy[1]],'-',lw=1.2 if c.startswith('BUFx24') else 0.8,color='k' if 'B' not in n else ('b' if 'L' not in n else 'g'))
  ax.plot(*xy,'s' if c.startswith('BUFx24') else 'o',ms=5 if c.startswith('BUFx24') else 3,color='r' if c.startswith('BUFx24') else 'm')
for n,p,xy,k in r['leaves']:ax.plot([pos[p][0],xy[0]],[pos[p][1],xy[1]],'-',lw=0.6,color='g');ax.plot(*xy,'^',ms=3,color='g')
for x,y in r['islands']:ax.plot(x,y,'*',ms=14,color='orange')
ax.plot(*r['entry'],'X',ms=12,color='k')
p=r['pred'];ax.set_title('btab R5 equal-structure channel H-tree (plan model, UNCHECKED): TT %.1f w%.1f / FF %.1f w%.1f'%(p['TT']['mean'],p['TT']['window'],p['FF']['mean'],p['FF']['window']))
ax.set_aspect('equal');ax.set_xlim(0,354);ax.set_ylim(0,259);fig.savefig(sys.argv[3],dpi=110,bbox_inches='tight')
