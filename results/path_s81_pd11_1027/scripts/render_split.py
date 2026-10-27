import json, sys
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
B='/srv/opentallas-scratch2/claude/path-s81-pd7-1026/pd9/me1'; O='/srv/opentallas-scratch2/claude/path-s81-pd11-1027/cont'
M=json.load(open(B+'/mesh.json')); XS,YS=15972.92,12376.935
tr={}
for l in open(B+'/tree_TT.txt'):
    f=l.split()
    if f and f[0]=='D': tr[f[1]]=float(f[2])
ss=M['strap_spans']
def draw(ax,box,title):
    x0,x1,y0,y1=box
    for k,(lo,hi) in ss.items():
        a,i,_=k.split(':'); i=int(i)
        if a=='H':
            y=M['ys'][i]
            if y0<=y<=y1: ax.plot([max(lo,x0),min(hi,x1)],[y,y],color='tab:blue',lw=1.2,zorder=1)
        else:
            x=M['xs'][i]
            if x0<=x<=x1: ax.plot([x,x],[max(lo,y0),min(hi,y1)],color='tab:green',lw=1.2,zorder=1)
    for h in M['htree']:
        a,b=h['a'],h['b']
        if h['level']<=4 or (x0-500<=b[0]<=x1+500 and y0-500<=b[1]<=y1+500):
            ax.plot([a[0],b[0],b[0]],[a[1],a[1],b[1]],color='0.55' if h['level']>3 else 'red',lw=0.6 if h['level']>3 else 1.5,zorder=2)
    px,py,c=[],[],[]
    for v in M['drivers'].values():
        x,y=v['site']
        if x0<=x<=x1 and y0<=y<=y1:
            px.append(x);py.append(y);c.append(tr.get(v['cells'][0],float('nan')))
    sc=ax.scatter(px,py,c=c,cmap='viridis',s=22,zorder=3,vmin=6690,vmax=6880,marker='s')
    for d in M.get('dropped_drivers',[]):
        x,y=d['ideal']
        if x0<=x<=x1 and y0<=y<=y1: ax.scatter([x],[y],marker='x',color='k',s=40,zorder=4)
    ax.axvline(XS,color='m',ls='--',lw=1); ax.axhline(YS,color='m',ls='--',lw=1)
    ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.set_title(title,fontsize=9)
    return sc
fig,axs=plt.subplots(1,3,figsize=(21,7.5))
draw(axs[0],(14200,17750,10600,14150),'centre: both split lines (x=15973, y=12377)')
draw(axs[1],(0,3550,10600,14150),'left die edge at y-split (worst U pairs, x=459)')
sc=draw(axs[2],(14200,17750,1000,4550),'x-split near bottom (y 1000-4550)')
fig.colorbar(sc,ax=axs,label='mesh-driver input arrival TT (ps, RCX tree)',shrink=0.8)
fig.suptitle('S81 PD9 me1 clock mesh: M8 straps blue (H), M9 straps green (V), L1-L3 tree red, deeper legs grey, drivers squares; magenta = top split lines',fontsize=10)
fig.savefig(O+'/split_zoom.png',dpi=110)
fig2,ax=plt.subplots(figsize=(13,10)); sc=draw(ax,(0,32000,0,25000),'whole die'); fig2.colorbar(sc,ax=ax); fig2.savefig(O+'/die_full.png',dpi=90)
print('ok')
