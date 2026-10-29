#!/usr/bin/env python3
"""HEAD-START-2 render of the placed START vehicle (bodies + every measured hop).
usage: render_reach.py repo mapped physical_lc stages ctree_dir lef plan reach.json outdir"""
import json,sys,collections
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection,PatchCollection
repo,mapped,phys,stages,ctd,lef,planf,reachf,out=sys.argv[1:10];out=Path(out);out.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[repo+'/tools/die_plan',repo+'/tools/s81_head']
import schema as S,start_stage_emit as E
from head_start_pack import lef_sizes
sz=lef_sizes(open(lef).read());P=S.Plan(json.load(open(planf)),Path(planf))
ph=json.load(open(phys));st=json.load(open(stages));rc=json.load(open(reachf))
tc,txy=E.ctree_cells(open(ctd+'/ctree.v').read(),open(ctd+'/ctree.tcl').read())
trect={n:(x,y,x+sz[m][0],y+sz[m][1]) for n,(m,_,_) in tc.items() for x,y in [txy[n]]}
srect={n:tuple(c['rect_um']) for n,c in ph['cells'].items()}
lrect={v['inst']:tuple(v['rect_um']) for v in ph['stage_clock_drivers'].values()}
ctr=lambda r:((r[0]+r[2])/2,(r[1]+r[3])/2)
allr={**trect,**srect,**lrect}
mod=json.load(open(mapped))['modules']['ot_die_start_stages']
drv={};snk=collections.defaultdict(list)
for n,v in mod['ports'].items():
    for b in v['bits']:
        if isinstance(b,int):(drv.__setitem__(b,('p',n)) if v['direction']=='input' else snk[b].append(('p',n)))
for n,c in mod['cells'].items():
    for pin,bits in c['connections'].items():
        for b in bits:
            if isinstance(b,int):(drv.__setitem__(b,('c',n)) if c['port_directions'][pin]=='output' else snk[b].append(('c',n)))
pxy={n:v['xy_um'] for n,v in ph['ports'].items()};cp={s['clock_port']:s for s in st['stages']}
def L(e):return pxy[e[1]] if e[0]=='p' else ctr(srect[e[1]])
data=[];rst=[];lclk=[];tre=[]
for b,ss in snk.items():
    d=drv.get(b)
    if not d:continue
    if d[0]=='p' and d[1] in cp:
        bc=ctr(lrect[ph['stage_clock_drivers'][d[1]]['inst']]);lclk+=[(bc,L(e)) for e in ss];continue
    (rst if d[0]=='p' else data).extend((L(d),L(e)) for e in ss)
ydrv={y:n for n,(m,a,y) in tc.items()};tin=collections.defaultdict(list)
for n,(m,a,y) in tc.items():tin[a].append(n)
for n,(m,a,y) in tc.items():tre+=[(ctr(trect[n]),ctr(trect[k])) for k in tin.get(y,())]
for c,s in cp.items():
    t=ydrv.get(c) or ydrv.get(s['clock_net']);lclk.append((ctr(trect[t]),ctr(lrect[ph['stage_clock_drivers'][c]['inst']])))
cores=[]
for q in P.parts:
    for c in P.ptype(q).get('hard_cores',[]):
        x,y=c['origin_um'];w,h=c['outline_um'];cs=[P.to_die(q,[xx,yy]) for xx in (x,x+w) for yy in (y,y+h)];xs,ys=zip(*cs);cores.append((min(xs),min(ys),max(xs),max(ys)))
parts=[(o[0],o[1],o[0]+P.types[p['type']]['outline_um'][0],o[1]+P.types[p['type']]['outline_um'][1]) for p in P.parts.values() for o in [p['origin_um']]]
def draw(tag,box,title,bodies=False):
    fig,ax=plt.subplots(figsize=(11,10),dpi=120)
    ax.add_collection(PatchCollection([Rectangle((a,b),c-a,d-b) for a,b,c,d in parts],facecolor='none',edgecolor='#888',linewidth=.3))
    ax.add_collection(PatchCollection([Rectangle((a,b),c-a,d-b) for a,b,c,d in cores],facecolor='#e0e0e0',edgecolor='#aaa',linewidth=.3))
    lw=.25 if box is None else .8
    ax.add_collection(LineCollection(tre,colors='#31a354',linewidths=lw,alpha=.6,label='clock tree hop'))
    ax.add_collection(LineCollection(rst,colors='#ff9900',linewidths=lw,alpha=.5,label='raw reset relay -> stage'))
    ax.add_collection(LineCollection(data,colors='#3182bd',linewidths=lw,alpha=.8,label='START data (BUF8 chains)'))
    ax.add_collection(LineCollection(lclk,colors='#ae017e',linewidths=lw,alpha=.9,label='tree -> local BUF8 -> FF CLK'))
    if bodies:
        for rr,col in ((trect,'#31a354'),(srect,'#d7301f'),(lrect,'#ae017e')):
            ax.add_collection(PatchCollection([Rectangle((a,b),c-a,d-b) for a,b,c,d in rr.values() if box[0]-5<a<box[2]+5 and box[1]-5<b<box[3]+5],facecolor=col,edgecolor='k',linewidth=.3,alpha=.7))
        ys=[box[1]+k*.27 for k in range(int((box[3]-box[1])/.27)+2)];ys=[round(y/.27)*.27 for y in ys]
        ax.add_collection(LineCollection([((box[0],y),(box[2],y)) for y in ys],colors='#ccc',linewidths=.2))
    else:
        ax.scatter([ctr(r)[0] for r in srect.values()],[ctr(r)[1] for r in srect.values()],s=.3,c='#d7301f')
        ax.scatter([ctr(r)[0] for r in lrect.values()],[ctr(r)[1] for r in lrect.values()],s=1.2,c='#ae017e')
    if box:ax.set_xlim(box[0],box[2]);ax.set_ylim(box[1],box[3])
    else:ax.set_xlim(0,P.die['outline_um'][0]);ax.set_ylim(0,P.die['outline_um'][1])
    ax.set_aspect('equal');ax.legend(loc='upper right',fontsize=7);ax.set_title(title.replace('$',r'\$'),fontsize=9);ax.set_xlabel('um');ax.set_ylabel('um')
    fig.tight_layout();fig.savefig(out/(tag+'.png'));plt.close(fig)
h=rc['summary']['hops']
draw('overview',None,'HEAD START vehicle placed (plan_spine_raw_rx_tx): START cells red, local clock BUF8 magenta, hard cores grey\n'+', '.join(f"{k} max {v['max']}" for k,v in h.items())+' um; 0 >405; 0 overlaps')
def around(name,r=420):
    x,y=ctr(allr[name]);return (x-r,y-r,x+r,y+r)
for k in ('tree->local_clk','reset_port->cell','tree->tree','cell->cell'):
    w=h[k]['worst'];a=w[1] if w[1] in allr else w[2]
    draw('worst_'+k.replace('->','_to_').replace('>',''),around(a),f'worst {k} {w[0]} um: {w[1]} -> {w[2]}')
root=next(s for s in st['stages'] if s['root'])
draw('root',around(root['node_cell'],350),'root stage '+root['id'])
x,y=ctr(lrect['start_clock_'+root['id']]);draw('rows_root',(x-12,y-8,x+12,y+8),'native rows near root local BUF8: clock green, START red, local BUF8 magenta',bodies=True)
w=h['tree->local_clk']['worst'];x,y=ctr(lrect[w[2]]);draw('rows_worst_lclk',(x-12,y-8,x+12,y+8),'rows at worst local BUF8 '+w[2],bodies=True)
print('rendered',sorted(p.name for p in out.glob('*.png')))
