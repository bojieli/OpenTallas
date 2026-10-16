#!/usr/bin/env python3
"""Place all16x36 standard48 RF relay footprints on the centre-route witness.

Exact rectangles and routed-polyline hop lengths are checked; this is not STA.
"""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan')
    ap.add_argument('--netlist-ref',default='af261fbcb')
    a = ap.parse_args()
    d = Path(a.plan)
    p = json.loads((d/'compact.P.json').read_text())
    r = json.loads((d/'rf_centre_routes.json').read_text())
    root=Path(__file__).resolve().parents[2]
    net=json.loads(subprocess.check_output(['git','-C',str(root),'show',a.netlist_ref+':results/arch/hbm_die_v16/contract.json']))
    occupied = []
    cells = []
    failures = []
    side = 21.6

    def free(x,y):
        for b in list(p.values()) + occupied:
            if x-side/2 < b['x']+b['w']-1e-6 and b['x'] < x+side/2-1e-6 and y-side/2 < b['y']+b['h']-1e-6 and b['y'] < y+side/2-1e-6:
                return False
        return True

    def put(route,k,x,y):
        b = dict(x=round(x-side/2,3), y=round(y-side/2,3), w=side,h=side)
        occupied.append(b)
        src,dst=route.split('>');name=f'rfr_{src}_{dst}_{k:02d}'
        native=net['instances'][name]
        assert native['master'].startswith('hbfd_rly_48_')
        cells.append(dict(name=name,route=route,index=k,cell=native['master'],source_ref=a.netlist_ref,
                          source=native['source'],bits_used=41,rect=b))

    for route in sorted(r['routes'], key=lambda z:z['length_um'], reverse=True):
        name=route['source']+'>'+route['destination']
        if route['source']==route['destination']:
            q=route['source'];b=p['sucore_'+q]
            sign=1 if q.endswith('W') else -1
            x0=b['x']+b['w']+21.6 if sign==1 else b['x']-21.6
            y0=b['y']+b['h']-21.6 if q.startswith('S') else b['y']+21.6
            sy=-1 if q.startswith('S') else 1
            for k in range(36):
                col,row=divmod(k,12)
                if col%2:row=11-row
                x,y=x0+sign*col*21.6,y0+sy*row*21.6
                if not free(x,y):failures.append(dict(route=name,index=k,reason='self padding footprint blocked'))
                else:put(name,k,x,y)
            continue
        pts=route['path']
        lengths=[abs(b[0]-a[0])+abs(b[1]-a[1]) for a,b in zip(pts,pts[1:])]
        total=sum(lengths)

        def point(t):
            used=0
            for (a,b),length in zip(zip(pts,pts[1:]),lengths):
                if t<=used+length+1e-6:
                    f=(t-used)/length if length else 0
                    return a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1])
                used+=length
            return tuple(pts[-1])

        previous=0
        chain=[]
        for k in range(36):
            target=(k+1)*total/37
            candidates=sorted(range(max(1,int(target)-180),min(int(total)-1,int(target)+180)+1),key=lambda t:abs(t-target))
            found=False
            for t in candidates:
                if t-previous>480 or t<=previous+21.6 or total-t>(36-k)*480:
                    continue
                x,y=point(t)
                if free(x,y):
                    put(name,k,x,y);chain.append(t-previous);previous=t;found=True;break
            if not found:
                failures.append(dict(route=name,index=k,reason='no legal footprint before480um deadline'))
                break
        route['allocated_hop_um']=chain+[total-previous]
    out=dict(schema='opentallas.hbm.rf_centre_allocation.v1',qualification='GEOMETRIC_FOOTPRINTS_ONLY',
             cells=cells,expected_cells=576,placed_cells=len(cells),failures=failures,
             area_mm2=len(cells)*side*side/1e6,physical_view='hbfd_rly_48 must be source-bound and native-audited before adoption',
             max_allocated_hop_um=max((max(x.get('allocated_hop_um',[0])) for x in r['routes']),default=0),
             all_36_stage_routes_allocated=len(cells)==576 and not failures)
    (d/'rf_centre_allocation.json').write_text(json.dumps(out,indent=1)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='cells'}))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(16,12))
    for n,b in p.items():
        ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#deebf7',edgecolor='#555555',linewidth=.4))
        if n.startswith(('sucore','vmh','idx_','coll_')):ax.text(b['x']+b['w']/2,b['y']+b['h']/2,n,fontsize=5,ha='center')
    for route in r['routes']:
        xy=route['path'];ax.plot([v[0] for v in xy],[v[1] for v in xy],linewidth=.6,alpha=.45,color='#cc0000')
    for c in cells:
        b=c['rect'];ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#009933',edgecolor='none'))
    ax.set(aspect='equal',xlabel='um',ylabel='um',title=f'HBM core-at4 RF36: {len(cells)}/576 relay footprints; {len(failures)} failures; geometry only')
    fig.tight_layout();fig.savefig(d/'rf_centre_allocation.png',dpi=180);plt.close(fig)


if __name__=='__main__':main()
