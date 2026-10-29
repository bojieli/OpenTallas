import json,sys,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt;from matplotlib.patches import Rectangle
s=json.load(open(sys.argv[1]));pg=json.load(open(sys.argv[2]))
fig,ax=plt.subplots(1,4,figsize=(16,5))
for a,r in zip(ax,s['stubs']):
  x,y=r['entry_xy_um'];px0,py0,px1,py1=r['rect_um'];cy=(py0+py1)/2
  a.set_xlim(x-1.2,x+1.2);a.set_ylim(cy-1.2,cy+1.2);a.set_aspect('equal')
  for q in pg:
    if q[1]=='M8':a.add_patch(Rectangle((q[2],q[3]),q[4]-q[2],q[5]-q[3],color='tab:green' if q[0]=='VSS' else 'tab:red',alpha=.35,label=q[0]+' M8'))
    if q[1]=='M9':a.add_patch(Rectangle((q[2],q[3]),q[4]-q[2],q[5]-q[3],color='gray',alpha=.2))
  sx0,sy0,sx1,sy1=r['m7_stub_um']
  a.add_patch(Rectangle((sx0,sy0),sx1-sx0,sy1-sy0,color='tab:blue',alpha=.8,label='M7 pin+stub'))
  a.add_patch(Rectangle((px0,py0),px1-px0,py1-py0,fill=False,ec='k',lw=1.5,label='native M7 pin'))
  a.add_patch(Rectangle((x-.096,y-.04),.192,.08,color='tab:orange',alpha=.9,label='VIA78 M8 patch'))
  a.add_patch(Rectangle((x-.096-.32,y-.04-.32),.192+.64,.08+.64,fill=False,ec='tab:orange',ls='--',label='0.32 NDR keep'))
  a.set_title(f"{r['inst']} stub +{r['stub_len_beyond_pin_um']} um, row {y}",fontsize=9)
ax[0].legend(fontsize=7,loc='lower left')
plt.tight_layout();plt.savefig(sys.argv[3],dpi=110)
