"""Plan a bounded-depth clock trunk on free physical sites, before local CTS.

The existing density tap buffers are leaves. All leaves have the same number
of trunk stages; only the local tap nets go through TritonCTS afterwards.
Geometry uses native OpenDB DBU throughout. No RTL or cycle count changes.
"""
import argparse
import bisect
import json
import math
from pathlib import Path


def load_geometry(path):
    g = dict(rows=[], cells=[], taps=[])
    orientations={}
    for line in Path(path).read_text().splitlines():
        f = line.split()
        if not f or f[0].startswith('#'):
            continue
        k = f.pop(0)
        if k == 'DBU': g['dbu'] = int(f[0])
        elif k == 'CORE': g['core'] = list(map(int, f[:4]))
        elif k == 'ROOT': g['root'] = list(map(int, f[:2]))
        elif k == 'ROOT_NAME': g['root_name'] = f[0]
        elif k == 'MASTER': g['master'], g['width'], g['height'] = f[0], int(f[1]), int(f[2])
        elif k == 'ROW': g['rows'].append(list(map(int, f[:5])) + [f[5] if len(f)>5 else 'R0'])
        elif k == 'ROW_ORIENT': orientations[(int(f[1]),int(f[2]))]=f[3]
        elif k == 'CELL': g['cells'].append([f[0]]+list(map(int, f[1:6])))
        elif k == 'TAP': g['taps'].append(dict(name=f[0], xy=list(map(int,f[1:3])), nets=f[3:5]))
    for row in g['rows']:row[5]=orientations.get((row[0],row[1]),row[5])
    for k in ('dbu','core','root','master','width','height'):
        if k not in g: raise ValueError(f'missing physical geometry {k}')
    if not g['taps'] or not g['rows']: raise ValueError('missing taps or legal rows')
    return g


class FreeSites:
    def __init__(self, g):
        self.w, self.h = g['width'], g['height']
        self.rows = g['rows']
        self.busy = [[] for _ in self.rows]
        ordered = sorted((r[1],i) for i,r in enumerate(self.rows))
        ys = [y for y,i in ordered]
        maxrh=max(r[3] for r in self.rows)
        for name,x0,y0,x1,y1,block in g['cells']:
            # Every occupied footprint counts, including movable logic/F6 FFs.
            lo = bisect.bisect_right(ys,y0-maxrh)
            hi = bisect.bisect_left(ys,y1)
            for y,i in ordered[lo:hi]:
                if y+self.rows[i][3]>y0: self.busy[i].append((x0,x1))
        for i in range(len(self.rows)): self.busy[i].sort()

    def legal(self, xy, reserve=True):
        tx,ty=xy[0]-self.w/2,xy[1]-self.h/2
        best=None
        for i in sorted(range(len(self.rows)),key=lambda i:(abs(self.rows[i][1]-ty),i)):
            rx,y,sw,rh,ns,orient=self.rows[i]
            if rh != self.h: continue
            if best is not None and abs(y-ty)>best[0]: break
            end=rx+sw*ns
            intervals=[]
            for a,b in self.busy[i]:
                if b<=rx or a>=end: continue
                if intervals and a<=intervals[-1][1]: intervals[-1]=(intervals[-1][0],max(b,intervals[-1][1]))
                else: intervals.append((max(rx,a),min(end,b)))
            start=rx
            for a,b in intervals+[(end,end)]:
                left=math.ceil((start-rx)/sw)
                right=math.floor((a-self.w-rx)/sw)
                if left<=right:
                    ix=min(max(round((tx-rx)/sw),left),right)
                    x=rx+ix*sw
                    v=(abs(x-tx)+abs(y-ty),i,x,y,orient)
                    if best is None or v<best: best=v
                start=max(start,b)
        if best is None: raise ValueError('no free row-legal clock buffer footprint')
        _,i,x,y,orient=best
        if reserve: bisect.insort(self.busy[i],(x,x+self.w))
        return dict(ll=[x,y],xy=[x+self.w/2,y+self.h/2],orient=orient)


def split(points, count):
    ax=max((0,1),key=lambda j:(max(p['xy'][j] for p in points)-min(p['xy'][j] for p in points),-j))
    pts=sorted(points,key=lambda p:(p['xy'][ax],p['xy'][1-ax],p['name']))
    count=min(count,len(pts))
    return [pts[len(pts)*i//count:len(pts)*(i+1)//count] for i in range(count)]


def plan(g, fanout=4, leaf_fanout=8, max_hop_um=400):
    if fanout<2 or leaf_fanout<1: raise ValueError('invalid clock fanout')
    a,b,c,d=g['core']
    if any(not (a<=t['xy'][0]<=c and b<=t['xy'][1]<=d) for t in g['taps']):
        raise ValueError('tap buffer lies outside the physical core')
    level=0
    while leaf_fanout*fanout**level<len(g['taps']): level+=1
    sites=FreeSites(g)
    nodes=[]; edges=[]
    def build(pts,parent,remaining,depth,desired=None):
        nm=f'ot_dtsh_{len(nodes)}'
        xy=desired or [sum(p['xy'][j] for p in pts)/len(pts) for j in (0,1)]
        node=dict(name=nm,parent=parent,depth=depth,**sites.legal(xy))
        nodes.append(node)
        if parent: edges.append([parent,nm])
        if remaining:
            for group in split(pts,fanout): build(group,nm,remaining-1,depth+1)
        else:
            for t in pts: edges.append([nm,t['name']])
    # One common lead from the physical pin to the spatial tree. It is common
    # to every tap, instead of making four long high-load branches at the pin.
    lead=dict(name='ot_dtsh_0',parent=None,depth=1,**sites.legal(g['root']))
    nodes.append(lead)
    build(g['taps'],lead['name'],level,2)
    xy={n['name']:n['xy'] for n in nodes}|{t['name']:t['xy'] for t in g['taps']}
    max_hop=max(abs(xy[a][0]-xy[b][0])+abs(xy[a][1]-xy[b][1]) for a,b in edges)/g['dbu']
    stub=sum(abs(a-b) for a,b in zip(nodes[0]['xy'],g['root']))/g['dbu']
    max_hop=max(max_hop,stub)
    if max_hop>max_hop_um: raise ValueError(f'planned clock edge {max_hop:.3f} um exceeds {max_hop_um}')
    p=dict(nodes=nodes,edges=edges,taps=g['taps'],root=g['root'],root_name=g.get('root_name',''),
           dbu=g['dbu'],core=g['core'],master=g['master'],width=g['width'],height=g['height'],
           obstacles=[c[1:5] for c in g['cells'] if c[5]],
           summary=dict(new_buffers=len(nodes),tap_buffers=len(g['taps']),trunk_levels=level+3,
                        max_hop_um=max_hop,port_stub_um=stub,fanout=fanout,leaf_fanout=leaf_fanout,
                        added_cycles=0,added_area_um2=len(nodes)*g['width']*g['height']/g['dbu']**2))
    validate(p)
    return p


# ---------------------------------------------------------------------------
# CLOSED-LOOP structured spine (CLOCK-TRUNK 10-25, MSCTS practice).
# Every tree edge is a private buffered LEG: a leg-start buffer next to the
# parent cluster point, n repeaters along a (possibly detoured) path, and a
# 2-pin wire into the child (the child cluster's leg-start buffers, or the
# density-tap input).  All legs of one level have the same repeater count, so
# every tap has the same stage count; every segment is <= rmax_um.  The open-
# loop geometry is only the start point: OpenROAD measures the tap arrivals
# (TT + FF, its own parasitic estimate) and cl_step() re-targets each leg's
# length bottom-up until the tap spread meets the target.
# ---------------------------------------------------------------------------
def _man(a,b): return abs(a[0]-b[0])+abs(a[1]-b[1])


def plan_legs(g, fanout=4, leaf_fanout=2, rmax_um=100.0, slack=1.4, min_rep=1):
    if fanout<2 or leaf_fanout<1: raise ValueError('invalid clock fanout')
    a,b,c,d=g['core']; u=g['dbu']
    if any(not (a<=t['xy'][0]<=c and b<=t['xy'][1]<=d) for t in g['taps']):
        raise ValueError('tap buffer lies outside the physical core')
    depth=0
    while leaf_fanout*fanout**depth<len(g['taps']): depth+=1
    clusters=[]; legs=[]
    def cent(pts): return [sum(p['xy'][j] for p in pts)/len(pts) for j in (0,1)]
    def build(pts,level):
        cid=len(clusters); cl=dict(id=cid,level=level,point=cent(pts),taps=[t['name'] for t in pts],legs=[])
        clusters.append(cl)
        if level<depth:
            for grp in split(pts,fanout):
                ch=build(grp,level+1)
                legs.append(dict(id=len(legs),level=level+1,parent=cid,child=['cluster',ch]))
                cl['legs'].append(legs[-1]['id']); clusters[ch]['in_leg']=legs[-1]['id']
        else:
            for t in pts:
                legs.append(dict(id=len(legs),level=level+1,parent=cid,child=['tap',t['name']]))
                cl['legs'].append(legs[-1]['id'])
        return cid
    build(g['taps'],1)
    # cluster points on legal free logic sites (a centroid may fall on a macro)
    probe=FreeSites(g)
    for cl in clusters: cl['point']=probe.legal(cl['point'],reserve=False)['xy']
    lead=dict(id=len(legs),level=0,parent=None,child=['cluster',0]); legs.append(lead); clusters[0]['in_leg']=lead['id']
    tapxy={t['name']:t['xy'] for t in g['taps']}
    for L in legs:
        L['A']=list(g['root']) if L['parent'] is None else clusters[L['parent']]['point']
        L['C']=clusters[L['child'][1]]['point'] if L['child'][0]=='cluster' else tapxy[L['child'][1]]
        L['d']=_man(L['A'],L['C'])
    reps={}
    for lv in sorted({L['level'] for L in legs}):
        dm=max(L['d'] for L in legs if L['level']==lv)/u
        reps[lv]=max(0 if lv==0 else min_rep, math.ceil((dm if lv==0 else dm*slack)/rmax_um)-1)
    k=0
    order=sorted(legs,key=lambda L:(L['level'],L['id']))
    for L in order:
        L['n']=reps[L['level']]
        L['xmax']=max(0.0,(L['n']+1)*rmax_um*u-L['d']) if L['level'] else 0.0
        # equal-length start: every leg of a level as long as its longest
        dm=max(M['d'] for M in legs if M['level']==L['level'])
        L['x']=min(L['xmax'],float(dm-L['d'])) if L['level'] else 0.0
        L['bufs']=[f'ot_dtsh_{k+i}' for i in range(L['n']+1)]; k+=L['n']+1
        L['hist']=[]
    p=dict(mode='closed_loop',clusters=clusters,legs=legs,taps=g['taps'],root=g['root'],root_name=g.get('root_name',''),
           dbu=u,core=g['core'],master=g['master'],width=g['width'],height=g['height'],
           obstacles=[cc[1:5] for cc in g['cells'] if cc[5]],rmax_um=rmax_um,reps=reps,iters=[],
           fanout=fanout,leaf_fanout=leaf_fanout)
    realize(p,g)
    return p


def leg_path(A,C,T,core,side=1,axis=None):
    """Manhattan polyline A->C of length T (>= |A-C|): L-shape, or a U-detour
    beyond the bounding box (on the minor axis by default) when T exceeds the
    distance."""
    dx,dy=abs(A[0]-C[0]),abs(A[1]-C[1])
    ax=(1 if dx>=dy else 0) if axis is None else axis   # ax = detour axis
    e=max(0.0,(T-dx-dy)/2)
    lo,hi=min(A[ax],C[ax]),max(A[ax],C[ax])
    cands=[hi+e,lo-e] if side>0 else [lo-e,hi+e]
    w=A[ax]
    if e>0:
        w=None
        for v in cands:
            if core[ax]<=v<=core[ax+2]: w=v;break
        if w is None: w=min(max(cands[0],core[ax]),core[ax+2])
    def pt(v_ax,v_other):
        q=[0,0];q[ax]=v_ax;q[1-ax]=v_other;return q
    return [list(A),pt(w,A[1-ax]),pt(w,C[1-ax]),list(C)]


def along(poly,s):
    for a,b in zip(poly,poly[1:]):
        l=_man(a,b)
        if s<=l and l>0:
            f=s/l;return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f]
        s-=l
    return list(poly[-1])


def realize(p,g):
    """Legal free-site positions for every leg buffer; top-down order."""
    sites=FreeSites(g); nodes=[]; edges=[]
    last={}
    for L in sorted(p['legs'],key=lambda L:(L['level'],L['id'])):
        T=L['d']+L['x']
        # detour shape: the one whose repeaters land on free logic sites (not
        # pushed off a macro, which would make the leg length unresponsive);
        # sticky unless another shape is clearly better
        def shape(sel):
            poly=leg_path(L['A'],L['C'],T,p['core'],sel[1],sel[0])
            pts=[along(poly,T*i/(L['n']+1)) for i in range(1,L['n']+1)]
            return poly,pts,sum(_man(q,sites.legal(q,reserve=False)['xy']) for q in pts)
        cur=tuple(L.get('dsel') or ((1 if abs(L['A'][0]-L['C'][0])>=abs(L['A'][1]-L['C'][1]) else 0),1 if L['id']%2 else -1))
        poly,_,best=shape(cur)
        if L['x']>0 and best>2*p['dbu']:
            for sel in [(a,sd) for a in (0,1) for sd in (1,-1)]:
                if sel==cur: continue
                q,_,sc=shape(sel)
                if sc+5*p['dbu']<best: cur,poly,best=sel,q,sc
        L['dsel']=list(cur)
        L['T']=T; L['seg_um']=T/(L['n']+1)/p['dbu']
        parent=None if L['parent'] is None else last[('cl',L['parent'])]
        for i,nm in enumerate(L['bufs']):
            xy=L['A'] if i==0 else along(poly,T*i/(L['n']+1))
            node=dict(name=nm,parent=parent,depth=L['level'],leg=L['id'],**sites.legal(xy))
            nodes.append(node)
            if parent: edges.append([parent,nm])
            parent=nm
        if L['child'][0]=='cluster': last[('cl',L['child'][1])]=parent
        else: edges.append([parent,L['child'][1]])
    p['nodes']=nodes; p['edges']=edges
    xy={n['name']:n['xy'] for n in nodes}|{t['name']:t['xy'] for t in p['taps']}
    hop=max(_man(xy[a],xy[b]) for a,b in edges)/p['dbu']
    p['summary']=dict(mode='closed_loop',new_buffers=len(nodes),tap_buffers=len(p['taps']),
                      trunk_levels=sum(n+1 for n in p['reps'].values()),reps={str(k):v for k,v in p['reps'].items()},
                      max_hop_um=hop,rmax_um=p['rmax_um'],added_cycles=0,
                      added_area_um2=len(nodes)*p['width']*p['height']/p['dbu']**2)
    validate(p)
    return p


def read_meas(path):
    tap={};buf={}
    for line in Path(path).read_text().splitlines():
        f=line.split()
        if len(f)<4: continue
        if f[0]=='T': tap[f[1]]=(float(f[2]),float(f[3]))
        elif f[0]=='B': buf[f[1]]=(float(f[2]),float(f[3]))
    return tap,buf


def spread(tap):
    tt=[v[0] for v in tap.values()];ff=[v[1] for v in tap.values()]
    return max(tt)-min(tt),max(ff)-min(ff)


def cl_step(p,tap,buf,damp=0.8,k0=0.2,kmin=0.04,kmax=1.5):
    """One closed-loop update from MEASURED arrivals (ps) at tap inputs (TT,FF)
    and leg-buffer inputs.  Bottom-up: inside each cluster every child leg is
    re-targeted so the child subtrees' mean arrival is equal and the shortest
    leg is direct (x=0); predicted subtree means feed the level above."""
    u=p['dbu']
    tt=[v[0] for v in tap.values()];ff=[v[1] for v in tap.values()]
    r=(sum(tt)/len(tt))/(sum(ff)/len(ff))
    m={t:(v[0]+r*v[1])/2 for t,v in tap.items()}
    mb={b:(v[0]+r*v[1])/2 for b,v in buf.items()}
    legs={L['id']:L for L in p['legs']}; cl=p['clusters']
    def child_in(L):
        if L['child'][0]=='tap': return m[L['child'][1]]
        ins=[mb[legs[j]['bufs'][0]] for j in cl[L['child'][1]]['legs'] if legs[j]['bufs'][0] in mb]
        return sum(ins)/len(ins) if ins else None
    # per-leg sensitivity (ps per um of leg length), secant over history
    for L in p['legs']:
        D=None
        if L['bufs'][0] in mb:
            ci=child_in(L)
            if ci is not None: D=ci-mb[L['bufs'][0]]
        L['hist'].append([L['T']/u,D])
        h=[q for q in L['hist'] if q[1] is not None]
        k=L.get('k',k0)
        if len(h)>=2 and abs(h[-1][0]-h[-2][0])>2:
            k=(h[-1][1]-h[-2][1])/(h[-1][0]-h[-2][0])
        L['k']=min(kmax,max(kmin,k))
    pred={}
    def visit(cid):
        vals=[]
        for j in cl[cid]['legs']:
            L=legs[j]
            v=m[L['child'][1]] if L['child'][0]=='tap' else visit(L['child'][1])
            vals.append((L,v))
        # common target: the latest child at its shortest legal length
        tau=max(v-L['k']*L['x']/u for L,v in vals)
        out=[]
        for L,v in vals:
            xn=L['x']+damp*(tau-v)/L['k']*u
            xn=min(L['xmax'],max(0.0,xn))
            out.append(v+L['k']*(xn-L['x'])/u); L['x']=xn
        pred[cid]=sum(out)/len(out)
        return pred[cid]
    visit(0)
    s=spread(tap)
    p['iters'].append(dict(tt_spread=s[0],ff_spread=s[1],tt=[min(tt),max(tt)],ff=[min(ff),max(ff)],
                           capped=sum(1 for L in p['legs'] if L['level'] and L['x']>=L['xmax']-1)))
    return s


def emit_moves(p,out):
    import re
    lines=['# closed-loop trunk re-placement (same names/topology); native DBU','ot_dtsh::relocate_begin']
    for n in p['nodes']:
        if not re.fullmatch(r'ot_dtsh_\d+',n['name']):raise ValueError('unsafe trunk name')
        x,y=n['ll'];lines.append(f"ot_dtsh::relocate {n['name']} {x} {y} {n['orient']}")
    lines.append('ot_dtsh::relocate_end')
    Path(out).write_text('\n'.join(lines)+'\n')


def _strip(p):
    return {k:v for k,v in p.items() if k not in ('obstacles',)}


def validate(p):
    names={n['name'] for n in p['nodes']}
    taps={t['name'] for t in p['taps']}
    parents={}
    for a,b in p['edges']:
        if a not in names or b not in names|taps or b in parents: raise ValueError('broken trunk ownership')
        parents[b]=a
    roots=names-set(parents)
    if len(roots)!=1 or not taps<=set(parents): raise ValueError('missing root or tap clock driver')
    depths=[]
    for t in taps:
        seen=set();n=t
        while n in parents:
            if n in seen: raise ValueError('clock trunk cycle')
            seen.add(n);n=parents[n]
        depths.append(len(seen)+1)
    if len(set(depths))!=1: raise ValueError('unequal clock trunk levels')


def render(p,out):
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(7,7))
    from matplotlib.patches import Rectangle
    u=p['dbu']; xy={n['name']:n['xy'] for n in p['nodes']}|{t['name']:t['xy'] for t in p['taps']}
    for x0,y0,x1,y1 in p.get('obstacles',[]):ax.add_patch(Rectangle((x0/u,y0/u),(x1-x0)/u,(y1-y0)/u,color='#ddd'))
    for a,b in p['edges']:
        x,y=xy[a];xx,yy=xy[b]
        ax.plot([x/u,xx/u,xx/u],[y/u,y/u,yy/u],color='#4878a8',lw=.6)
    ax.scatter([t['xy'][0]/u for t in p['taps']],[t['xy'][1]/u for t in p['taps']],s=12,label='existing tap buffer')
    ax.scatter([n['xy'][0]/u for n in p['nodes']],[n['xy'][1]/u for n in p['nodes']],marker='s',s=25,label='planned trunk buffer')
    ax.scatter([p['root'][0]/u],[p['root'][1]/u],marker='*',s=100,color='black',label='actual clock pin')
    a,b,c,d=p['core'];rx,ry=p['root'];ax.set_xlim(min(a,rx)/u-3,max(c,rx)/u+3);ax.set_ylim(min(b,ry)/u-3,max(d,ry)/u+3);ax.set_aspect('equal')
    ax.set_title(f"{p['summary']['tap_buffers']} tap clock: {p['summary']['trunk_levels']} trunk levels, max edge {p['summary']['max_hop_um']:.1f} um")
    ax.legend(fontsize=7);fig.savefig(out,dpi=130,bbox_inches='tight')


def emit_apply(p,out):
    import re
    validate(p)
    lines=['# Generated bounded-depth clock trunk; native DBU coordinates.']
    for n in p['nodes']:
        if not re.fullmatch(r'ot_dtsh_\d+',n['name']):raise ValueError('unsafe trunk name')
        x,y=n['ll'];parent=n['parent'] or '@root'
        lines.append(f"ot_dtsh::node {n['name']} {x} {y} {n['orient']} {parent}")
    taps={t['name'] for t in p['taps']}
    for a,b in p['edges']:
        if b in taps:
            if not re.fullmatch(r'ot_dtap_\d+',b):raise ValueError('unsafe tap name')
            lines.append(f'ot_dtsh::leaf {b} {a}')
    Path(out).write_text('\n'.join(lines)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('geometry');ap.add_argument('--out',required=True);ap.add_argument('--image');ap.add_argument('--apply')
    ap.add_argument('--closed-loop',action='store_true',help='structured spine of private buffered legs (re-targeted by --cl-step)')
    ap.add_argument('--cl-step',metavar='MEAS',help='measured arrivals TSV; updates --out plan in place and writes --apply moves')
    ap.add_argument('--target-ps',type=float,default=20.0)
    a=ap.parse_args();g=load_geometry(a.geometry)
    env=__import__('os').environ
    if a.cl_step:
        p=json.loads(Path(a.out).read_text())
        p['reps']={int(k):v for k,v in p['reps'].items()}
        tap,buf=read_meas(a.cl_step)
        s=cl_step(p,tap,buf,damp=float(env.get('OT_DTSH_CL_DAMP','0.8')))
        done=max(s)<=a.target_ps
        if not done:
            realize(p,g)
            if a.apply: emit_moves(p,a.apply)
        Path(a.out).write_text(json.dumps(p,indent=1)+'\n')
        if a.image: render(p,a.image)
        print(json.dumps(dict(iter=len(p['iters']),tt_spread=round(s[0],2),ff_spread=round(s[1],2),done=done,
                              capped=p['iters'][-1]['capped'],buffers=len(p['nodes']))))
        return
    if a.closed_loop:
        p=plan_legs(g,fanout=int(env.get('OT_DTSH_FANOUT','4')),leaf_fanout=int(env.get('OT_DTSH_LEAF_FANOUT','2')),
                    rmax_um=float(env.get('OT_DTSH_RMAX_UM','100')))
    else:
        p=plan(g)
    Path(a.out).write_text(json.dumps(p,indent=1)+'\n')
    if a.image:render(p,a.image)
    if a.apply:emit_apply(p,a.apply)
    print(json.dumps(p['summary']))

if __name__=='__main__':main()
