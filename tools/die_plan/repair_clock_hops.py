#!/usr/bin/env python3
"""Prototype: replace illegal long clock branches with legal edge relay chains.

Uses orthogonal obstacle visibility paths only to select relay sites. Real clock
wire RC and skew must be remeasured after global/detailed routing. No data cycles.
"""
import argparse,json,math
from pathlib import Path
import die_clock_mesh as M
import clock_corridor as C


def run(a):
    src,out=Path(a.dir),Path(a.out)
    if out.exists():raise ValueError('output must be fresh')
    P=M.S.Plan(M.S.load(a.plan))
    mesh=json.loads((src/'mesh.json').read_text());cells=json.loads((src/'place.json').read_text());data=json.loads((src/'nets.json').read_text())
    hard=M.DC.keepouts(P);K=M.DC.KeepIndex(hard,die=(P.W,P.H))
    for n,c in cells.items():M.reserve_cell(K,n,c)
    wanted={(r[0],r[1]) for r in mesh['unplaced'] if len(r)>=4 and r[2]=='STRUCTURAL clock span exceeds 750 um'}
    byport={t['port']:t['xy'] for t in mesh['taps']};extra=[];done=set();routes=[]
    def centre(c):return (c['x']+M.cell_width(c)/2,c['y']+M.ROW_Y/2)
    for n in data['nets']:
        if n['drv'].startswith('port:'): continue
        pa=centre(cells[n['drv']])
        for ld in n['loads']:
            pb=tuple(byport[ld[5:]]) if ld.startswith('port:') else centre(cells[ld])
            if abs(pa[0]-pb[0])+abs(pa[1]-pb[1])+M.BUF_W+M.ROW_Y>750:
                wanted.add((n['drv'],ld))
    for net in list(data['nets']):
        updated=[]
        for load in net['loads']:
            if (net['drv'],load) not in wanted:updated.append(load);continue
            pa=centre(cells[net['drv']]);pb=tuple(byport[load[5:]]) if load.startswith('port:') else centre(cells[load])
            x0,x1=min(pa[0],pb[0])-a.margin,max(pa[0],pb[0])+a.margin
            y0,y1=min(pa[1],pb[1])-a.margin,max(pa[1],pb[1])+a.margin
            boxes=[(max(0,r[0]-2.16),max(0,r[1]-1.08),min(P.W,r[2]+2.16),min(P.H,r[3]+1.08))
                   for r in hard if r[3]>y0 and r[1]<y1]
            points=C.route(pa,pb,boxes,(P.W,P.H))
            planned=[]
            for start,end in zip(points,points[1:]):
                length=abs(start[0]-end[0])+abs(start[1]-end[1]);n=max(1,math.ceil(length/a.pitch))
                planned.extend((start[0]+(end[0]-start[0])*k/n,start[1]+(end[1]-start[1])*k/n) for k in range(1,n+1))
            planned=planned[:-1]
            names=[];actual=[pa]
            for j,p in enumerate(planned):
                q,_=M.free_near(K,p,limit=64,step=M.STEP_UM)
                if q is None:raise ValueError(f'no legal relay for {net["drv"]}->{load} at {p}')
                name=f'ckm_r_edge_{len(routes)}_{j}'
                cell={'x':M.snap(q[0]-M.BUF_W/2,M.SITE_X),'y':M.snap(q[1]-M.ROW_Y/2,M.ROW_Y),'kind':'rep','level':net.get('level'),'edge_repair':True}
                cells[name]=cell;M.reserve_cell(K,name,cell);names.append(name);actual.append(centre(cell))
            actual.append(pb)
            hops=[abs(u[0]-v[0])+abs(u[1]-v[1])+M.BUF_W+M.ROW_Y for u,v in zip(actual,actual[1:])]
            if not names or max(hops)>750:raise ValueError(f'relay reach failed {net["drv"]}->{load}: {max(hops):.3f} um')
            updated.append(names[0])
            for u,v in zip(names,names[1:]+[load]):extra.append({'name':'ckm_w_'+u,'drv':u,'loads':[v],'level':net.get('level')})
            done.add((net['drv'],load));routes.append({'from':net['drv'],'to':load,'points_um':actual,'cells':names,'max_hop_um':max(hops),'extra_wire_um':sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(actual,actual[1:]))-abs(pa[0]-pb[0])-abs(pa[1]-pb[1])})
        net['loads']=updated
    data['nets']+=extra
    mesh['unplaced']=[r for r in mesh['unplaced'] if (r[0],r[1]) not in done]
    bad=M.hard_keepout_violations(P,cells);over=M.placement_overlaps(cells)
    if bad or over:raise ValueError(f'placement illegal: {len(bad)} hard, {len(over)} clock overlaps')
    all_hops=[]
    for n in data['nets']:
        if n['drv'].startswith('port:'): continue
        pa=centre(cells[n['drv']])
        for ld in n['loads']:
            pb=tuple(byport[ld[5:]]) if ld.startswith('port:') else centre(cells[ld])
            all_hops.append(abs(pa[0]-pb[0])+abs(pa[1]-pb[1])+M.BUF_W+M.ROW_Y)
    if max(all_hops,default=0)>750:raise ValueError('complete clock-hop census exceeds 750 um')
    extra_mm=sum(r['extra_wire_um'] for r in routes)/1000
    mesh['meta']['htree_wire_mm']+=extra_mm
    mesh['meta']['reps']=sum(c.get('kind')=='rep' for c in cells.values())
    mesh['edge_repair']=routes
    mesh['meta'].update(cells=len(cells),unplaced=len(mesh['unplaced']),clock_cell_overlap_pairs=0,clock_hard_keepout_violations=0)
    mesh['meta']['edge_repair']={'source':str(src),'branches':len(done),'added_cells':len(extra),'max_hop_um':max(all_hops,default=0),'extra_wire_mm':extra_mm,'qualification':'NOT RUN: actual routed RC and skew required'}
    out.mkdir(parents=True);ren=M.write_verilog(cells,data['nets'],data['ports'],out/'ctree.v')
    for n in data['nets']:n['name']=ren.get(n['name'],n['name'])
    for name,obj in [('mesh.json',mesh),('place.json',cells),('nets.json',data)]: (out/name).write_text(json.dumps(obj)+'\n')
    print(json.dumps(mesh['meta']['edge_repair'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dir');p.add_argument('--out',required=True);p.add_argument('--plan',required=True);p.add_argument('--pitch',type=float,default=500);p.add_argument('--margin',type=float,default=300);run(p.parse_args())
