import csv,re,pickle,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ins=[r for r in csv.DictReader(open('insts.tsv'),delimiter='\t') if r['name']!='name']
sinks=pickle.load(open('sinks.pkl','rb'))
fig,axs=plt.subplots(1,2,figsize=(16,20))
W,H=457.92,1166.4
def cls(inst,src):
    if src in('ck_rs','ck_rn'): return src+(' W' if False else '')
    m=re.search(r'g_sl\[(\d)\]\.g_hd\.g_tx\.g_r\[(\d)\]',inst)
    if m: return f'tx{m.group(1)}r{m.group(2)}'
    if 'mq_wrom' in inst: return 'mq_wrom'
    if 's2_w' in inst: return 's2_w'
    if 'u_xm' in inst: return 'xm'
    return 'ck_other' if src=='ck' else src
import matplotlib.cm as cm
groups=sorted(set(cls(i,s) for _,s,i,_,_,_ in sinks))
cmap=cm.get_cmap('tab20',len(groups))
for ax in axs:
    ax.add_patch(Rectangle((0,0),W,H,fill=False))
    for r in ins:
        if r['block']=='1':
            x,y,w,h=map(float,(r['x'],r['y'],r['w'],r['h']))
            ax.add_patch(Rectangle((x,y),w,h,fc='#dddddd',ec='k',lw=.6))
            ax.text(x+w/2,y+h/2,r['master'].replace('ot_qwen_tile_','')+'\n'+re.sub(r'.*(g_sl\\\[\d\\\]|g_rb\\\[\d\\\]|g_col\\\[\d\\\]|u_node).*',r'\1',r['name']).replace('\\',''),ha='center',va='center',fontsize=6)
    ax.set_xlim(-5,W+5);ax.set_ylim(-5,H+5);ax.set_aspect('equal')
# left: sinks by group
for gi,g in enumerate(groups):
    pts=[(x,y) for _,s,i,x,y,_ in sinks if cls(i,s)==g]
    if True:
        axs[0].scatter([p[0] for p in pts],[p[1] for p in pts],s=1.2,color=cmap(gi),label=f'{g} ({len(pts)})')
axs[0].legend(fontsize=6,markerscale=6,loc='upper right',ncol=2);axs[0].set_title('gate3 CTS ODB: register sinks by group')
# right: ck/ck_rs/ck_rn arrival heat
sel=[(x,y,a) for _,s,i,x,y,a in sinks if s in('ck','ck_rs','ck_rn')]
sc=axs[1].scatter([p[0] for p in sel],[p[1] for p in sel],c=[p[2] for p in sel],s=1.5,cmap='inferno_r',vmin=300,vmax=1230)
plt.colorbar(sc,ax=axs[1],shrink=.5,label='TT clock arrival ps (ck; rs/rn incl. entry phase)')
axs[1].set_title('ck / ck_rs / ck_rn sink arrival (TT, placement RC)')
fig.tight_layout();fig.savefig(sys.argv[1] if len(sys.argv)>1 else 'gate3_sinks.png',dpi=90)
