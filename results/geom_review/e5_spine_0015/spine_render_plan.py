import json,sys,matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=json.load(open(sys.argv[1])); u=p['dbu']; legs=p['legs']; cl={c['id']:c for c in p['clusters']}
inleg={tuple(L['child']):L for L in legs}; wl={}
for t in p['taps']:
    L=inleg[('tap',t['name'])]; s=0
    while True:
        s+=L['d']
        if L['parent'] is None: break
        L=legs[cl[L['parent']]['in_leg']]
    wl[t['name']]=s/u
meas={}
if len(sys.argv)>3:
    for l in open(sys.argv[3]):
        f=l.split('\t')
        if f[0]=='tap':
            try: meas[f[1].split('/')[0]]=float(f[3])
            except: pass
fig,ax=plt.subplots(1,2,figsize=(18,10))
nm={n['name']:n for n in p['nodes']}
col={0:'tab:blue',2:'tab:red',3:'tab:green',4:'tab:pink'}
for a in ax:
    for x0,y0,x1,y1 in p['obstacles'] if 'obstacles' in p else []: a.add_patch(Rectangle((x0/u,y0/u),(x1-x0)/u,(y1-y0)/u,color='#ddd'))
    a.set_xlim(0,410);a.set_ylim(0,467);a.set_aspect('equal')
a=ax[0]
for k,q in p['wire_paths'].items():
    s_=k.split('|')[0]; lv=nm[s_]['depth']
    a.plot([z[0]/u for z in q],[z[1]/u for z in q],color=col.get(lv,'k'),lw={0:2.5,2:1.6,3:.8}.get(lv,.4),alpha=.8)
for lv,nmn in [(0,'lead root->M'),(2,'spine legs M->spine pts'),(3,'rib legs spine pt->hub'),(4,'tap legs hub->tap')]:
    n_=[L['d']/u for L in legs if L['level']==lv]
    a.plot([],[],color=col[lv],label='%s: %d legs %.0f-%.0f um'%(nmn,len(n_),min(n_),max(n_)))
a.scatter([n['xy'][0]/u for n in p['nodes']],[n['xy'][1]/u for n in p['nodes']],s=2,c='k',label='BUFx24 %d'%len(p['nodes']))
a.scatter([t['xy'][0]/u for t in p['taps']],[t['xy'][1]/u for t in p['taps']],s=3,c='tab:olive',label='taps %d'%len(p['taps']))
a.legend(loc='upper right',fontsize=7)
a.set_title('E5 SPINE SP2 (claude/e5-spine-0015): reps %s, %d stages every tap'%(p['reps'],p['summary']['trunk_levels']),fontsize=10)
a=ax[1]
if meas:
    ks=[t for t in p['taps'] if t['name'] in meas]; v=[meas[t['name']] for t in ks]
    sc=a.scatter([t['xy'][0]/u for t in ks],[t['xy'][1]/u for t in ks],c=v,s=9,cmap='viridis'); plt.colorbar(sc,ax=a,label='tap input arrival TT ps (GRT RC, clock M4-M5)')
    a.set_title('measured tap input arrival %.0f..%.0f ps (spread %.0f)'%(min(v),max(v),max(v)-min(v)),fontsize=10)
else:
    v=list(wl.values()); sc=a.scatter([t['xy'][0]/u for t in p['taps']],[t['xy'][1]/u for t in p['taps']],c=[wl[t['name']] for t in p['taps']],s=9,cmap='viridis')
    plt.colorbar(sc,ax=a,label='planned root->tap wire um'); a.set_title('planned wire %.0f..%.0f um (spread %.0f)'%(min(v),max(v),max(v)-min(v)),fontsize=10)
fig.tight_layout(); fig.savefig(sys.argv[2],dpi=80)
