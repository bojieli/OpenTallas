import sys,re,numpy as np,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
guide,dump,out=sys.argv[1:4]
W,H=354.24,259.2;B=2.16;nx,ny=int(np.ceil(W/B)),int(np.ceil(H/B))
L=['M2','M3','M4','M5'];G={l:np.zeros((ny,nx)) for l in L};CK={l:np.zeros((ny,nx)) for l in L}
mac=[];clk=set()
for l in open(dump):
  f=l.split()
  if f[0]=='MACRO':mac.append(list(map(float,f[2:6])))
  if f[0]=='CLK' and len(f)>6: clk.add(f[6])
net=None
for ln in open(guide):
  s=ln.strip()
  if not s: continue
  if s=='(' or s==')': continue
  p=s.split()
  if len(p)==1: net=p[0]; isck=(net in clk) or net.startswith('ot_ms') or net=='ck'; continue
  x1,y1,x2,y2=[int(v)/1000 for v in p[:4]];ly=p[4]
  if ly not in G: continue
  i0,i1=int(x1/B),max(int(x1/B),int((x2-1e-6)/B));j0,j1=int(y1/B),max(int(y1/B),int((y2-1e-6)/B))
  G[ly][j0:j1+1,i0:i1+1]+=1
  if isck: CK[ly][j0:j1+1,i0:i1+1]+=1
fig,axs=plt.subplots(2,2,figsize=(15,11))
for ax,l in zip(axs.flat,L):
  g=G[l];im=ax.imshow(g,origin='lower',extent=(0,nx*B,0,ny*B),cmap='magma',vmax=np.percentile(g[g>0],99.5) if (g>0).any() else 1)
  ys,xs=np.nonzero(CK[l]);ax.scatter((xs+.5)*B,(ys+.5)*B,s=1,c='cyan',lw=0)
  for r in mac:ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,ec='w',lw=.8))
  ax.plot(177.132,135,'X',c='lime',ms=9)
  ax.set_title(f'{l}: guide nets per 2.16 um gcell (max {int(g.max())}, p99.5 {np.percentile(g[g>0],99.5):.0f}); cyan = clock-net guides')
  plt.colorbar(im,ax=ax,shrink=.8)
fig.suptitle("btab_m0_r5 post-GRT (5_1_grt route.guide; corner keep-offs + E read-mux region): GRT overflow 0, usage M2 6.9 / M3 7.9 / M4 2.6 / M5 2.8 % (UNCHECKED)")
plt.tight_layout();plt.savefig(out,dpi=110)
