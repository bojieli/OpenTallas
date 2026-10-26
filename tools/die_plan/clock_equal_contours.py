#!/usr/bin/env python3
"""Physical clock prototype: equal per-stage Manhattan contours at real sites.

Input must already have equal root-to-tap clock-cell depth. Existing cells are
legalized first; each non-root edge gains one kept real buffer at equal L1
distance from its physical endpoints. One common radius is used per stage.
No off-contour slide, electrical padding, or datapath latency change is allowed.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import json
import math
from pathlib import Path
import die_clock as DC
import schema as S
from clock_grt_probe import legalize_cells


def points(a,b,r):
    distance=abs(a[0]-b[0])+abs(a[1]-b[1])
    if distance>2*r+1e-6:return []
    result=[]
    for axis in [0,1]:
        cross=1-axis;direction=1 if b[axis]>=a[axis] else -1
        for sign in [1,-1]:
            u=(a[axis]+b[axis]+direction*sign*(a[cross]-b[cross]))/2
            v=max(a[cross],b[cross])+(2*r-distance)/2 if sign>0 else min(a[cross],b[cross])-(2*r-distance)/2
            p=[0.,0.];p[axis]=u;p[cross]=v;p=tuple(p)
            if all(abs(abs(p[0]-q[0])+abs(p[1]-q[1])-r)<1e-6 for q in [a,b]) and p not in result:result.append(p)
    return result


def equalize(plan,source,out,max_legs=3):
    P=S.Plan(S.load(plan));T=DC.load_tree(source);tree=json.loads((source/'tree.json').read_text())
    T.cells,legal=legalize_cells(T.cells,plan)
    K=DC.KeepIndex(DC.keepouts(P),die=(P.W,P.H));sx,sy=.054,.27;ns=30;width=1.62
    ports={'port:'+t['port']:tuple(t['xy']) for t in tree['taps']};ports['port:root']=tuple(tree['meta']['root_um'])
    def xy(node):return ports[node] if node.startswith('port:') else (T.cells[node]['x'],T.cells[node]['y'])
    incoming={load:n['drv'] for n in T.nets for _,_,load,_ in n['branches']}
    @lru_cache(None)
    def depth(node):
        if node=='port:root':return 0
        return depth(incoming[node])+(not node.startswith('port:'))
    active=[depth('port:'+t['port']) for t in tree['taps']]
    if min(active)!=max(active):raise ValueError('equal-depth input required')
    occupied=set()
    for c in T.cells.values():
        ix,iy=round(c['x']/sx),round(c['y']/sy);occupied.update((iy,j) for j in range(ix,ix+ns))
    groups=defaultdict(list)
    for ni,n in enumerate(T.nets):
        if n['drv']=='port:root':continue
        for bi,(_,layer,load,_) in enumerate(n['branches']):groups[depth(n['drv'])].append((ni,bi,n['drv'],load,layer))
    # NDR must follow the normalized physical stages, rather than differing
    # legacy node depths on paths that were structurally equalized.
    wide_through=max(depth(n) for n,c in T.cells.items() if c.get('kind')=='node' and (c.get('level') or 0)<=6)
    drivers={n['drv'] for n in T.nets if not n['drv'].startswith('port:')}
    for name in drivers:
        c=T.cells[name];c['physical_prior_kind']=c['kind'];c['physical_prior_level']=c.get('level')
        c['kind']='rep';c['level']=0 if depth(name)<=wide_through else 99
    native_offsets=sorted([(dx,dy) for dx in range(-5,6) for dy in [-1,0,1]],key=lambda d:abs(d[0])*sx+abs(d[1])*sy)
    def site(raw,controls):
        deep=K.hit(*raw,m=-.6)
        if deep and deep[4]!='outside die':return None
        bx,by=round(raw[0]/sx),round(raw[1]/sy)
        # Native row quantization is the only permitted contour error. A
        # nearby occupied exact intersection may use its adjacent row only
        # while BOTH individual legs remain within0.3um of the common radius.
        for dx,dy in native_offsets:
            ix,iy=bx+dx,by+dy;x,y=ix*sx,iy*sy
            if x<1 or y<1 or x+width>P.W-1 or y+.27>P.H-1:continue
            err=max(abs(abs(x-q[0])+abs(y-q[1])-r) for q,r in controls)
            if err>.300001:continue
            if any((iy,j) in occupied for j in range(ix,ix+ns)):continue
            if any(K.hit(u,v) for u,v in [(x,y),(x+width,y),(x,y+.27),(x+width,y+.27),(x+width/2,y+.135)]):continue
            return (round(x,6),round(y,6),iy,err),{(iy,j) for j in range(ix,ix+ns)}
        return None
    circle_cache={}
    def circle(a,r,b):
        cached=circle_cache.get((a,r))
        if cached is not None:
            extra=set()
            for u in [abs(a[0]-b[0]),r-abs(a[1]-b[1])]:
                if 0<=u<=r:
                    for sx_ in [-1,1]:
                        for sy_ in [-1,1]:extra.add((a[0]+sx_*u,a[1]+sy_*(r-u)))
            return sorted(set(cached)|extra,key=lambda p:abs(p[0]-b[0])+abs(p[1]-b[1]))
        us={i*8.64 for i in range(math.floor(r/8.64)+1)}|{r,abs(a[0]-b[0]),r-abs(a[1]-b[1])}
        for d in [.27,.54,.81,1.08,1.62,2.16,3.24]:us.update([d,r-d])
        # Clock corridors may be only a few microns wide. A macro-grid-only
        # sample can miss them forever; include exact rectangle-clearance events.
        nearby=set()
        for ix in range(int((a[0]-r-2)//K.b),int((a[0]+r+2)//K.b)+1):
            for iy in range(int((a[1]-r-2)//K.b),int((a[1]+r+2)//K.b)+1):nearby.update(K.g.get((ix,iy),()))
        for box in nearby:
            for x in [box[0]-width-.6,box[2]+.6]:us.add(abs(x-a[0]))
            for y in [box[1]-.27-.6,box[3]+.6]:us.add(r-abs(y-a[1]))
        candidates=set()
        for u in us:
            if not 0<=u<=r:continue
            v=r-u
            for sx_ in [-1,1]:
                for sy_ in [-1,1]:candidates.add((a[0]+sx_*u,a[1]+sy_*v))
        circle_cache[(a,r)]=tuple(candidates)
        return sorted(candidates,key=lambda p:abs(p[0]-b[0])+abs(p[1]-b[1]))
    def route(a,b,r,legs):
        if legs==2:
            for raw in points(a,b,r):
                q=site(raw,[(a,r),(b,r)])
                if q is not None:
                    p,sites=q;occupied.update(sites);return [p],sites
        elif legs==3:
            for raw in circle(a,r,b):
                one=site(raw,[(a,r)])
                if one is None:continue
                p,sites=one;occupied.update(sites)
                for raw2 in points(p[:2],b,r):
                    two=site(raw2,[(p[:2],r),(b,r)])
                    if two is not None:
                        q,sites2=two;occupied.update(sites2);return [p,q],sites|sites2
                occupied.difference_update(sites)
        else:
            for raw in circle(a,r,b):
                one=site(raw,[(a,r)])
                if one is None:continue
                p,sites=one;occupied.update(sites)
                for raw3 in circle(b,r,p[:2]):
                    three=site(raw3,[(b,r)])
                    if three is None:continue
                    q,sites3=three;occupied.update(sites3)
                    for raw2 in points(p[:2],q[:2],r):
                        two=site(raw2,[(p[:2],r),(q[:2],r)])
                        if two is not None:
                            middle,sites2=two;occupied.update(sites2);return [p,middle,q],sites|sites2|sites3
                    occupied.difference_update(sites3)
                occupied.difference_update(sites)
        return None
    selected={};radii={};leg_counts={};maxerror=0.;failures=[]
    for stage,edges in sorted(groups.items()):
        largest=max(abs(xy(a)[0]-xy(b)[0])+abs(xy(a)[1]-xy(b)[1]) for _,_,a,b,_ in edges)
        success=False;blocked=None
        for legs in range(2,max_legs+1):
            first=max(8.64,math.ceil(largest/legs/8.64)*8.64)
            radii_to_try={round(first+i*8.64,6) for i in range(math.floor((449.28-first)/8.64)+1)}
            # Equal native-length channel runs have narrow feasible radius
            # intervals; add their exact site-grid events instead of relaxing
            # the equal-leg condition or sliding a waypoint off its contour.
            for ni,bi,src,dst,layer in edges:
                a,b=xy(src),xy(dst);distance=abs(a[0]-b[0])+abs(a[1]-b[1])
                for divisor in [1,2,3,4]:
                    event=round(distance/divisor/.27)*.27
                    for offset in [-1.08,-.54,-.27,0,.27,.54,1.08]:
                        r=round(event+offset,6)
                        if largest/legs<=r<=449.28:radii_to_try.add(r)
            for r in sorted(radii_to_try):
                circle_cache.clear()
                placed=set();chosen=[];blocked=None
                for ni,bi,src,dst,layer in edges:
                    found=route(xy(src),xy(dst),r,legs)
                    if found is None:blocked=(ni,bi,src,dst);break
                    ps,sites=found;placed.update(sites);chosen.append((ni,bi,ps))
                if blocked is None:success=True;break
                occupied.difference_update(placed)
            if success:break
        if not success:
            failures.append(dict(stage=stage,edges=len(edges),minimum_radius_um=first,failed_edge=blocked,max_legs=max_legs))
            break
        for ni,bi,ps in chosen:
            selected[(ni,bi)]=ps
            maxerror=max(maxerror,max(p[3] for p in ps))
        radii[stage]=round(r,3);leg_counts[stage]=legs
        print(json.dumps(dict(stage=stage,edges=len(edges),legs=legs,radius_um=round(r,3))),flush=True)
    out.mkdir(parents=True,exist_ok=True)
    if failures:
        report=dict(verdict='FAIL',cause='no free equal-leg native site within450um radius',failures=failures,completed_stages=radii)
        (out/'failure.json').write_text(json.dumps(report,indent=2));raise ValueError(str(report))
    result=[];count=0;maxhop=0.
    def branch(a,b,load,layer):
        nonlocal maxhop
        g=abs(a[0]-b[0])+abs(a[1]-b[1]);maxhop=max(maxhop,g)
        bend=(b[0],a[1]) if layer=='M8' else (a[0],b[1]);return (g,layer,load,g),[a,bend,b]
    for ni,old in enumerate(T.nets):
        net={**old,'branches':[],'routes':[]};new=[];a=xy(old['drv'])
        for bi,(_,layer,load,_) in enumerate(old['branches']):
            if (ni,bi) not in selected:
                br,route=branch(a,xy(load),load,layer);net['branches'].append(br);net['routes'].append(route);continue
            mids=selected[(ni,bi)];names=[]
            level=DC.net_leg_level(T,old)
            for x,y,iy,error in mids:
                name=f'ngeom{count}';count+=1;T.cell(name,x,y,'rep',level)
                T.cells[name]['orient']='MX' if iy%2 else 'R0';names.append(name)
            br,route=branch(a,xy(names[0]),names[0],layer)
            net['branches'].append(br);net['routes'].append(route)
            for j,name in enumerate(names):
                target=names[j+1] if j+1<len(names) else load
                br,route=branch(xy(name),xy(target),target,layer)
                public=load[5:] if target==load and load.startswith('port:') else 'w_'+name
                new.append(dict(name=public,drv=name,branches=[br],routes=[route]))
            if load.startswith('port:'):
                if len(old['branches'])!=1:raise ValueError('public port fanout unsupported')
                net['name']='w_pre_'+old['name']
        result.append(net);result.extend(new)
    T.nets=result;parent={load:n['drv'] for n in T.nets for _,_,load,_ in n['branches']}
    @lru_cache(None)
    def path(node):
        if node=='port:root':return []
        return path(parent[node])+([] if node.startswith('port:') else [node])
    for t in tree['taps']:t['path']=path('port:'+t['port']);t['pad_nets']=[]
    for name,node in tree['nodes'].items():node['path']=path(name)
    ds=[len(t['path']) for t in tree['taps']]
    if min(ds)!=max(ds):raise ValueError('physical contour transform changed relative clock depth')
    meta=dict(added_clock_cells=count,clock_stages_per_tap=ds[0],radius_by_stage_um=radii,legs_by_stage=leg_counts,wide_through_original_stage=wide_through,
        max_native_grid_leg_error_um=round(maxerror,6),max_physical_hop_um=round(maxhop,6),
        added_cell_area_um2=round(count*1.62*.27,4),data_cycles_added=0,hidden_wire_pad_um=0,base_legalization=legal)
    tree['meta'].update(ndr=f'4W;8W through normalized clock stage{wide_through}',cells=len(T.cells),wire_um=round(sum(L for n in T.nets for L,*_ in n['branches']),3),padding_um=0.,pad_um=0.,pads=0,physical_equal_contours=meta)
    DC.NDR_MODE='4w';DC.WIDE_LEVELS=6;DC.write_verilog(T,out/'ctree.v');DC.write_spef(T,out/'ctree.spef')
    for file,obj in [('tree.json',tree),('place.json',T.cells),('nets.json',dict(ports=T.ports,nets=T.nets))]:(out/file).write_text(json.dumps(obj))
    print(json.dumps(meta,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--max-legs',type=int,choices=[2,3,4],default=4)
    a=p.parse_args();equalize(a.plan,a.source,a.out,a.max_legs)
