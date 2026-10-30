#!/usr/bin/env python3
"""Prepare zero-cycle placement repair from actual failing sfustore ODB dump.

Output is an opt-in Tcl probe, never an adopted plan or a route result. The
authoritative parent fault-S pin event must accompany this probe.
"""
import argparse
import inspect
import json
from collections import defaultdict
import sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('geom_tsv')
p.add_argument('geom_tools')
p.add_argument('out')
a = p.parse_args()
sys.path.insert(0, a.geom_tools)
import geom_rules as g

src = inspect.getsource(g.r2r_metrics).replace(
    'n_gt += 1', 'n_gt += 1\n            FAILS.append((mx,src,cap))')
g.FAILS = []
exec(src, g.__dict__)
d = g.Design(a.geom_tsv)
g.r2r_metrics(d)
macros = [c[2:6] for c in d.cells.values() if c[0] == 'M']
occupied = [(i, c[2:6]) for i,c in d.cells.items() if c[0] != 'M']
bins = defaultdict(list)
def add_occupied(i, r):
    for bx in range(int(r[0]//5),int(r[2]//5)+1):
        for by in range(int(r[1]//5),int(r[3]//5)+1):
            bins[bx,by].append((i,r))
for i,r in occupied:
    add_occupied(i,r)
anchors = []
for dist,s,c in g.FAILS:
    if 'u_bout_fault' in d.cells[c][6]:
        continue  # parent fr18 pin move, not an internal staging fix
    launch, capture = g.ctr(d.cells[s]), g.ctr(d.cells[c])
    target = tuple((x+y)/2 for x,y in zip(launch,capture))
    cell = d.cells[c]
    w,h = cell[4]-cell[2],cell[5]-cell[3]
    choices = []
    for dx in range(-120,121):
        for dy in range(-120,121):
            x = round((target[0]+dx*.54-w/2)/.054)*.054
            y = round((target[1]+dy*.54-h/2)/.27)*.27
            if x<4.32 or y<4.32 or x+w>358.56 or y+h>384.48:
                continue
            if abs(x+w/2-launch[0])+abs(y+h/2-launch[1])>395:
                continue
            def overlaps(r,halo=0):
                return x<r[2]+halo and x+w>r[0]-halo and y<r[3]+halo and y+h>r[1]-halo
            if any(overlaps(r,1.08) for r in macros):
                continue
            nearby=[entry for bx in range(int(x//5),int((x+w)//5)+1)
                    for by in range(int(y//5),int((y+h)//5)+1)
                    for entry in bins[bx,by]]
            if any(i!=c and overlaps(r) for i,r in nearby):
                continue
            choices.append((abs(x+w/2-target[0])+abs(y+h/2-target[1]),x,y))
    if not choices:
        raise SystemExit('NO_SITE '+cell[6])
    _,x,y = min(choices)
    anchors.append(dict(name=cell[6],xy_um=[round(x,3),round(y,3)],
                        source=d.cells[s][6],old_reach_um=round(dist,3)))
    occupied.append((c,(x,y,x+w,y+h)))
    add_occupied(c,(x,y,x+w,y+h))
out=Path(a.out)
out.mkdir(parents=True,exist_ok=True)
(out/'anchors.json').write_text(json.dumps(anchors,indent=1)+'\n')
lines=['# Apply only to an own copied 3_place ODB. No netlist/cycle changes.',
       'set ab [ord::get_db_block]', 'set au [$ab getDbUnitsPerMicron]']
for r in anchors:
    name=r['name'].replace('\\[','[').replace('\\]',']')
    x,y=r['xy_um']
    lines += ['set ai [$ab findInst {'+name+'}]',
              'if {$ai eq "NULL" || $ai eq ""} {error "missing anchor"}',
              f'$ai setLocation [expr {{round({x}*$au)}}] [expr {{round({y}*$au)}}]',
              '$ai setPlacementStatus FIRM']
lines += ['detailed_placement', 'check_placement -verbose']
(out/'anchor.tcl').write_text('\n'.join(lines)+'\n')
print(len(anchors),'anchors prepared; physical placement/reach/geometry NOT RUN')
