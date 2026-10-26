#!/usr/bin/env python3
"""Legalize a measured mesh without changing its cells, nets, mesh, or tap count.

Driver groups retain their strap and center where possible, use actual LEF body
widths, and move together only when a hard keepout requires it. Stub buffers move
only along their existing strap. Other conflicting bodies use nearby legal rows.
The result needs visual review and a fresh routed-clock TT/FF gate.
"""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import die_clock_mesh as M


def run(a):
    src,out=Path(a.dir),Path(a.out)
    if out.exists():raise ValueError('fresh output directory required')
    mesh=json.loads((src/'mesh.json').read_text());cells=json.loads((src/'place.json').read_text())
    before={n:dict(c) for n,c in cells.items()}
    data=json.loads((src/'nets.json').read_text())
    plan=M.S.Plan(M.S.load(a.plan));hard=M.DC.KeepIndex(M.DC.keepouts(plan),die=(float(plan.W),float(plan.H)))
    bins=defaultdict(list)
    def rect(c):return (c['x'],c['y'],c['x']+M.cell_width(c),c['y']+M.ROW_Y)
    def collide(r,s):return min(r[2],s[2])-max(r[0],s[0])>1e-5 and min(r[3],s[3])-max(r[1],s[1])>1e-5
    def keys(r):return [(x,y) for x in range(int(r[0]//4),int(r[2]//4)+1) for y in range(int(r[1]),int(r[3])+1)]
    def legal(c):
        r=rect(c)
        if r[0]<0 or r[1]<0 or r[2]>float(plan.W) or r[3]>float(plan.H):return False
        if any(hard.hit(x,y,m=.6) for x in (r[0],r[2]) for y in (r[1],r[3])):return False
        return not any(collide(r,s) for k in keys(r) for _,s in bins[k])
    def reserve(n,c):
        r=rect(c)
        for k in keys(r):bins[k].append((n,r))
    def offsets(axis=None):
        yield 0.,0.
        if axis is not None:
            for i in range(1,1201):
                d=i*(M.SITE_X if axis==0 else M.ROW_Y)
                for sign in (-1,1):yield (sign*d,0.) if axis==0 else (0.,sign*d)
        else:
            for r in range(1,81):
                for ix in range(-r,r+1):
                    for iy in (-r,r):yield ix*M.SITE_X,iy*M.ROW_Y
                for iy in range(-r+1,r):
                    for ix in (-r,r):yield ix*M.SITE_X,iy*M.ROW_Y
    # Actual-width parallel banks are an intentional abutting group. Check each
    # body against previously placed groups, then reserve the whole bank.
    done=set()
    for d in mesh['drivers'].values():
        names=d['cells'];sx,sy=d['site'];axis=0 if d['strap']=='M8' else 1
        for dx,dy in offsets(axis):
            trial=[]
            for i,n in enumerate(names):
                c=dict(cells[n]);c['x']=M.snap(sx+dx+(i-len(names)/2)*M.BUF_W,M.SITE_X);c['y']=M.snap(sy+dy-M.ROW_Y/2,M.ROW_Y);trial.append((n,c))
            if all(legal(c) for n,c in trial):break
        else:raise ValueError(f'no legal parallel driver bank {names}')
        for n,c in trial:cells[n]=c;reserve(n,c);done.add(n)
        d['site']=[round(sx+dx,4),round(sy+dy,4)]
        d['move_um']=round(abs(d['site'][0]-d['ideal'][0])+abs(d['site'][1]-d['ideal'][1]),4)
    tapby={t['stub']:t for t in mesh['taps']}
    for n,c in sorted(cells.items(),key=lambda x:(x[1]['kind']=='stub',x[0])):
        if n in done:continue
        old=dict(c);tap=tapby.get(n);axis=None if tap is None else (0 if tap['strap'][0]=='M8' else 1)
        for dx,dy in offsets(axis):
            c=dict(old);c['x']=M.snap(old['x']+dx,M.SITE_X);c['y']=M.snap(old['y']+dy,M.ROW_Y)
            if legal(c):break
        else:raise ValueError(f'no legal site for {n}')
        cells[n]=c;reserve(n,c)
        if tap:
            tap['foot']=[round(tap['foot'][0]+dx,4),round(tap['foot'][1]+dy,4)]
            tap['stub_um']=round(abs(tap['foot'][0]-tap['xy'][0])+abs(tap['foot'][1]-tap['xy'][1]),4)
    overlaps=M.placement_overlaps(cells)
    if overlaps:raise ValueError(f'legalizer left {len(overlaps)} body overlaps')
    changed=[dict(name=n,before_um=[before[n]['x'],before[n]['y']],after_um=[c['x'],c['y']]) for n,c in cells.items() if c['x']!=before[n]['x'] or c['y']!=before[n]['y']]
    mesh['meta']['physical_legalization']={'source':str(src),'actual_BUF24_width_um':M.BUF_W,'changed_cells':len(changed),'max_move_um':max((abs(z['after_um'][0]-z['before_um'][0])+abs(z['after_um'][1]-z['before_um'][1]) for z in changed),default=0),'body_overlaps':0,'same_cells':len(cells)==len(before),'same_nets_sha256':hashlib.sha256((src/'nets.json').read_bytes()).hexdigest(),'qualification':'NOT RUN: requires image review and actual routed TT/FF'}
    mesh['meta']['reserve_cell_sites']=True;mesh['meta']['cell_body_overlaps']=0
    mesh['meta']['plan']=str(a.plan);mesh['meta']['plan_sha256']=hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    mesh['meta']['stub_max_um']=max(t['stub_um'] for t in mesh['taps'])
    mesh['meta']['driver_move_max_um']=max(d['move_um'] for d in mesh['drivers'].values())
    out.mkdir(parents=True)
    M.write_verilog(cells,data['nets'],data['ports'],out/'ctree.v')
    for name,obj in [('mesh.json',mesh),('place.json',cells),('nets.json',data),('legalization.json',{'changes':changed,'summary':mesh['meta']['physical_legalization']})]:(out/name).write_text(json.dumps(obj)+'\n')
    print(json.dumps(mesh['meta']['physical_legalization'],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('dir');p.add_argument('--out',required=True);p.add_argument('--plan',required=True);run(p.parse_args())
