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

    def legal(self, xy):
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
        bisect.insort(self.busy[i],(x,x+self.w))
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
    a=ap.parse_args();p=plan(load_geometry(a.geometry));Path(a.out).write_text(json.dumps(p,indent=1)+'\n')
    if a.image:render(p,a.image)
    if a.apply:emit_apply(p,a.apply)
    print(json.dumps(p['summary']))

if __name__=='__main__':main()
