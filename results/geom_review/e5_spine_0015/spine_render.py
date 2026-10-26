import json,sys,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=json.load(open(sys.argv[1])); S=p['summary']; XS=S['spine_x']; M=S['spine_mid']
fig,ax=plt.subplots(1,2,figsize=(18,10))
for a in ax:
    for m in p['macros']: a.add_patch(Rectangle((m[0],m[1]),m[2]-m[0],m[3]-m[1],color='#ddd'))
    c=p['core']; a.add_patch(Rectangle((c[0],c[1]),c[2]-c[0],c[3]-c[1],fill=False,ec='k',lw=.5))
    a.set_xlim(0,410);a.set_ylim(0,467);a.set_aspect('equal')
a=ax[0]
a.plot([p['root'][0],p['root'][0],XS],[p['root'][1],M[1],M[1]],color='tab:blue',lw=3,label='lead root->M %.0f um'%S['lead_um'])
ys=sorted({h['ys'] for h in p['hubs']})
a.plot([XS,XS],[min(ys),max(ys)],color='tab:red',lw=3,label='spine (private M5 legs from M)')
for h in p['hubs']:
    a.plot([XS,h['xy'][0],h['xy'][0]],[h['ys'],h['ys'],h['xy'][1]],color='tab:green',lw=.6,alpha=.7)
a.plot([],[],color='tab:green',label='ribs: M4 along channel row, M5 vertical to hub')
for y in ys: a.plot(XS,y,'s',color='tab:red',ms=7)
a.scatter([h['xy'][0] for h in p['hubs']],[h['xy'][1] for h in p['hubs']],s=[4*h['n'] for h in p['hubs']],c='k',zorder=5,label='hubs (<=%d taps), %d'%(S['hub_cap'],S['hubs']))
a.scatter([t[1] for t in p['taps']],[t[2] for t in p['taps']],s=2,c='tab:olive',label='taps %d'%S['taps'])
a.plot(*M,'*',color='tab:blue',ms=16); a.plot(*p['root'],'v',color='tab:blue',ms=12)
a.legend(loc='upper right',fontsize=8)
a.set_title('E5 spine/rib plan R%.0f: reps lead/spine/rib/tap %s, %s stages, %d BUFx24'%(S['rmax_um'],'/'.join(str(v) for v in S['reps'].values()),S['stages'],S['buffers']),fontsize=10)
a=ax[1]
sc=a.scatter([t[1] for t in p['taps']],[t[2] for t in p['taps']],c=[t[4] for t in p['taps']],s=8,cmap='viridis')
plt.colorbar(sc,ax=a,label='planned root->tap wire um')
a.set_title('root->tap wire %.0f..%.0f um (spread %.0f); Elmore est %.0f..%.0f ps (spread %.0f)'%(S['wl_min'],S['wl_max'],S['wl_spread'],S['elmore_ps_min'],S['elmore_ps_max'],S['elmore_spread_ps']),fontsize=10)
fig.tight_layout(); fig.savefig(sys.argv[2],dpi=80)
