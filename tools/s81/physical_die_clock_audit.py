#!/usr/bin/env python3
"""Read back an actual physical clock ODB and independently audit connectivity/sites.

Also inventory unwalked clock-like nets and their real drivers. Name discovery
is explicitly conservative; native clock coverage still requires consumed
Liberty/RTL relationships, particularly forwarded clocks and frequency ratios.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hbm_die_v15'))
from die_clock_tree import Grid,GRID
from clock_sites import XPITCH,YPITCH,SIZES


def main():
    import odb
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('odb','candidate','inventory','out'):ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads(a.candidate.read_text())
    inventory=json.loads(a.inventory.read_text())
    db=odb.dbDatabase.create();odb.read_db(db,str(a.odb));block=db.getChip().getBlock()
    unit=block.getDbUnitsPerMicron();die=block.getDieArea()
    obstacles=[]
    for inst in block.getInsts():
        if inst.getMaster().isBlock():
            b=inst.getBBox();obstacles.append(tuple(v/unit for v in (b.xMin(),b.yMin(),b.xMax(),b.yMax())))
    grid=Grid(die.xMax()/unit,die.yMax()/unit,obstacles)
    sites=set()
    for row in manifest['buffers']:
        inst=block.findInst(row['name'])
        if not inst or inst.getMaster().getName()!=row['cell']:
            raise ValueError(f'actual clock instance missing/wrong master: {row}')
        b=inst.getBBox();x,y=b.xMin()/unit,b.yMin()/unit
        if abs(x-row['x'])+abs(y-row['y'])>.002:
            raise ValueError(f'actual buffer box moved: {row["name"]}: {x,y} vs {row["x"],row["y"]}')
        site=(round(x/XPITCH),round(y/YPITCH))
        if site in sites:raise ValueError(f'overlapping actual clock site {site}')
        sites.add(site)
        # Entire actual cell rectangle, rather than just its anchor point.
        for ci in range(int(x/GRID),int((b.xMax()/unit-1e-9)/GRID)+1):
            for cj in range(int(y/GRID),int((b.yMax()/unit-1e-9)/GRID)+1):
                if not (0<=ci<grid.nx and 0<=cj<grid.ny and grid.free((ci,cj))):
                    raise ValueError(f'actual clock cell overlaps hard outline: {row["name"]}')
    expected=defaultdict(set)
    for e in manifest['entries']:expected[e['root']].add(e['pin'])
    coverage={}
    for root,want in expected.items():
        first=block.findITerm(root)
        seen,got,buffers=set(),set(),set()
        stack=[first.getNet()]
        while stack:
            net=stack.pop()
            if net.getName() in seen:raise ValueError(f'clock cycle/reconvergence: {net.getName()}')
            seen.add(net.getName())
            drivers=[it for it in net.getITerms() if it.getIoType()=='OUTPUT']
            if len(drivers)!=1:raise ValueError(f'clock net {net.getName()} has {len(drivers)} drivers')
            for pin in net.getITerms():
                if pin.getIoType()!='INPUT':continue
                inst=pin.getInst();name=inst.getName()
                if name.startswith('s81clk_'):
                    if inst.getMaster().getName() not in SIZES:raise ValueError('unapproved/inverting clock cell')
                    if pin.getMTerm().getName()!='A':raise ValueError('unexpected clock load terminal')
                    buffers.add(name);out=inst.findITerm('Y').getNet()
                    if not out:raise ValueError(f'orphan actual clock cell {name}')
                    stack.append(out)
                else:got.add(name+'/'+pin.getMTerm().getName())
        if got!=want:raise ValueError(f'actual clock coverage FAIL: missing {want-got}, extra {got-want}')
        coverage[root]=dict(entries=len(got),buffers=len(buffers),nets=len(seen),cycles=0,multiple_drivers=0)
    nets=defaultdict(list)
    for row in inventory:nets[row['net']].append(row['pin'])
    discovered=[]
    for name,pins in sorted(nets.items(),key=lambda nv:(-len(nv[1]),str(nv[0]))):
        net=block.findNet(name) if name else None
        drivers=[];external=[]
        if net:
            drivers=[dict(pin=p.getInst().getName()+'/'+p.getMTerm().getName(),master=p.getInst().getMaster().getName())
                     for p in net.getITerms() if p.getIoType()=='OUTPUT']
            external=[p.getName() for p in net.getBTerms() if p.getIoType()=='INPUT']
        discovered.append(dict(net=name,clocklike_entries=len(pins),drivers=drivers,external_sources=external,pins=pins))
    (a.out/'unwalked_clock_net_drivers.json').write_text(json.dumps(discovered,indent=1)+'\n')
    rec=dict(schema='opentallas.s81.physical_clock_odb_audit.v1',
        verdict='PASS_PHYSICAL_CONNECTIVITY_AND_SITES_ONLY',native_clock_qualified=False,
        actual_clock_cells=len(sites),hard_obstacles=len(obstacles),roots=coverage,
        unwalked_clocklike_entries=len(inventory),unwalked_clocklike_nets=len(discovered),
        top_unwalked=[{k:v for k,v in x.items() if k!='pins'} for x in discovered[:20]],
        open_obligations=manifest['open_obligations'])
    (a.out/'audit.json').write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({k:v for k,v in rec.items() if k not in ['top_unwalked','open_obligations']}))


if __name__=='__main__':main()
