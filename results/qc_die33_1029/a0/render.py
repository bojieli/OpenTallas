import json,sys,re
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
geom,homes,long,res,out=sys.argv[1:6]
mac=[];D=None
for l in open(geom):
    f=l.rstrip('\n').split('\t')
    if f[0]=='C' and f[2]=='M': mac.append((f[3],*map(float,f[4:8])))
    if f[0]=='D': D=list(map(float,f[1:5]))
    if f[0]=='P' and f[2] in('rst_n','ck'): globals()[f[2]+'_p']=(float(f[6]),float(f[7]))
h=json.load(open(homes));R=json.load(open(res));L=json.load(open(long))
fig,ax=plt.subplots(1,2,figsize=(15,17),sharey=True)
def base(a,t):
    a.add_patch(Rectangle((D[0],D[1]),D[2]-D[0],D[3]-D[1],fill=False,lw=1.5))
    for m,x0,y0,x1,y1 in mac:
        a.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#d0d0d0',ec='#555',hatch='//',lw=.6))
        a.text((x0+x1)/2,(y0+y1)/2,m.replace('ot_qwen_tile_',''),ha='center',va='center',fontsize=7)
    a.plot(*rst_n_p,'r^',ms=12);a.annotate('rst_n',rst_n_p,xytext=(-35,8),textcoords='offset points',color='r')
    a.plot(*ck_p,'*',color='gold',ms=14,mec='k')
    a.set_xlim(-10,470);a.set_ylim(-10,1170);a.set_aspect('equal');a.set_title(t,fontsize=10)
base(ax[0],f"FAILED NK V1L/ICG2 place: {len(L)} captures >405 (max {L[0]['d']})")
for r in L:
    ax[0].plot([r['sxy'][0],r['cxy'][0]],[r['sxy'][1],r['cxy'][1]],'-',color='red',lw=.3,alpha=.35)
cls=[('u_tx/q','TX relay g_r[*] (s2 broadcast -> slice)','tab:blue'),('g_kn.h','ICG B-hop FF h[k]','tab:green'),('/u_icg','ICG gate (homed)','magenta'),
     ('g_icg.dr','ICG dr enable FF','tab:olive'),('rst_native','reset entry','red'),('reset_q','reset relay','red'),('rq','slice reset rq','orange'),('s2_','u_me s2 broadcast root','black'),('','other moved FF','tab:gray')]
base(ax[1],f"PLANNED graph homes (RT 395): r2r>405 {R['r2r_gt405']} max {R['r2r_max']}, relay collapse {R['relay']['relay_collapsed']}, ICG en max {R['icg_enable_leg_max']}")
seen=set()
for n,(x,y) in h['homes'].items():
    ox,oy=h['orig'][n]
    if abs(x-ox)+abs(y-oy)<0.5: continue
    for k,lab,c in cls:
        if k in n:
            ax[1].annotate('',(x,y),(ox,oy),arrowprops=dict(arrowstyle='-',color=c,lw=.25,alpha=.3))
            ax[1].plot(x,y,'o',ms=2.2 if c!='magenta' else 6,color=c,label=None if lab in seen else lab);seen.add(lab);break
ax[1].legend(loc='upper right',fontsize=7,markerscale=2)
fig.suptitle('QC A0 NK (457.92x1157.76) graph-home repair: left = failed placement long captures, right = planned homes (dot) with move line from failed position',fontsize=10)
plt.tight_layout();plt.savefig(out,dpi=90)
