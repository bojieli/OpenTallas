import sys,re,json,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
dump,log,coll,out=sys.argv[1:5]
t=open(log).read();tap={m[0]:float(m[1]) for m in re.findall(r'OT_MSCTS_TAP grt TT (\S+) n \d+ mean ([-.\d]+)',t)}
c=json.load(open(coll))['corners']
cells={};drv={};ffs=[];std=[];mac=[]
for l in open(dump):
  f=l.split()
  if f[0]=='DIE':W,H=float(f[1]),float(f[2])
  elif f[0]=='MACRO':mac.append(list(map(float,f[2:6])))
  elif f[0]=='STD':std.append((float(f[1]),float(f[2])))
  elif f[0]=='FF':ffs.append((float(f[1]),float(f[2]),f[3] if len(f)>3 else ''))
  elif f[0]=='CLK':
    nm,x,y,m=f[1],float(f[2]),float(f[3]),f[4];i=f[5] if len(f)>5 else '';o=f[6] if len(f)>6 else ''
    cells[nm]=(x,y,m,i,o);drv[o]=(x,y)
leafnet={v[4]:re.sub(r'^ot_ms_(.*)_tap$',r'\1',k) for k,v in cells.items() if k.endswith('_tap')}
fig,ax=plt.subplots(figsize=(13,9.5))
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1))
for r in mac:ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='#c8cce0'))
ax.scatter([p[0] for p in std],[p[1] for p in std],s=0.15,c='#bbbbbb',lw=0)
vals=[tap.get(leafnet.get(n,''),float('nan')) for _,_,n in ffs]
sc=ax.scatter([p[0] for p in ffs],[p[1] for p in ffs],s=1.2,c=vals,cmap='viridis',vmin=250,vmax=275,lw=0)
for k,(x,y,m,i,o) in cells.items():
  if i in drv:ax.plot([drv[i][0],x],[drv[i][1],y],'-',lw=0.5,color='k',alpha=.6)
for k,(x,y,m,i,o) in cells.items():
  if k.endswith('_tap'):ax.plot(x,y,'s',ms=2.5,color='tab:red')
  elif 'BUFx24' in m:ax.plot(x,y,'o',ms=5,color='tab:blue')
  else:ax.plot(x,y,'o',ms=2,color='tab:green')
ax.plot(*cells['ot_ms_root'][:2],'X',ms=12,color='k')
plt.colorbar(sc,ax=ax,shrink=.7,label='GRT-RC TT tap mean (ps)')
T,F=c['TT'],c['FF']
ax.set_title('btab R6 calibration build, 5_1_grt placement + clock tree (413 cells; blue BUFx24 branch, green rep, red tap)\nGRT RC (UNCHECKED): TT mean %.1f, tap-mean window %.1f | FF mean %.1f, window %.1f | n=%d sinks'%(T['mean_ps'],T['tap_mean_window_ps'],F['mean_ps'],F['tap_mean_window_ps'],T['n']),fontsize=9)
ax.set_aspect('equal');ax.set_xlim(-2,W+2);ax.set_ylim(-2,H+2);fig.savefig(out,dpi=120,bbox_inches='tight')
