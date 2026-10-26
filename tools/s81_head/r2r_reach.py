#!/usr/bin/env python3
"""Complete structural data-cone reach census on an ODB (not timing sign-off).

Each net retains four witnessed extrema x+y,-x-y,x-y,-x+y of its upstream
register/macro output pins. This gives the exact largest Manhattan separation
to each capture pin without enumerating the Cartesian product of sources.
"""
import json
import os
import sys
import odb

sys.setrecursionlimit(100000)
b = odb.read_db(odb.dbDatabase.create(), os.environ['ODB']).getChip().getBlock()
unit = b.getDbUnitsPerMicron()
drivers = {}
for n in b.getNets():
    if n.getSigType() in ('POWER', 'GROUND', 'CLOCK'):
        continue
    drivers[n.getId()] = [t for t in n.getITerms() if t.getIoType() == 'OUTPUT']

def seq(i):
    return i.getMaster().isBlock() or 'DFF' in i.getMaster().getName()

def xy(t):
    good, x, y = t.getAvgXY()
    if not good:
        z = t.getInst().getBBox()
        x, y = (z.xMin()+z.xMax())/2, (z.yMin()+z.yMax())/2
    return x / unit, y / unit

memo, active = {}, set()
cycles = []
def bounds(net):
    if not net or net.getId() not in drivers:
        return None
    key = net.getId()
    if key in memo:
        return memo[key]
    if key in active:
        cycles.append(net.getName())
        return None
    active.add(key)
    candidates = []
    for t in drivers[key]:
        i = t.getInst()
        if seq(i):
            x, y = xy(t)
            who = i.getName() + '/' + t.getMTerm().getName()
            candidates.append([(v, x, y, who) for v in (x+y, -x-y, x-y, -x+y)])
        else:
            for it in i.getITerms():
                if it.getIoType() == 'INPUT' and it.getMTerm().getSigType() not in ('POWER','GROUND','CLOCK'):
                    v = bounds(it.getNet())
                    if v:
                        candidates.append(v)
    active.remove(key)
    memo[key] = [max((a[k] for a in candidates), key=lambda a:a[0]) for k in range(4)] if candidates else None
    return memo[key]

worst = []
captures = sources_absent = 0
for i in b.getInsts():
    if not seq(i):
        continue
    for t in i.getITerms():
        # Asynchronous reset/clock are separate timing and reach contracts.
        # Every actual data input is included, including all macro data/address pins.
        pn = t.getMTerm().getName()
        if t.getIoType() != 'INPUT' or t.getMTerm().getSigType() in ('POWER','GROUND','CLOCK') or pn in ('CLK','CK','clk','RESETN','SETN'):
            continue
        captures += 1
        v = bounds(t.getNet())
        if not v:
            sources_absent += 1
            continue
        x,y = xy(t)
        offsets = (-x-y,x+y,-x+y,x-y)
        k = max(range(4),key=lambda k:v[k][0]+offsets[k])
        dist = v[k][0]+offsets[k]
        worst.append({'distance_um':dist,'launch':v[k][3], 'launch_xy':v[k][1:3],
                      'capture':i.getName()+'/'+pn,'capture_xy':[x,y]})
worst.sort(key=lambda x:x['distance_um'],reverse=True)
bad = [w for w in worst if w['distance_um'] > 405.0+1e-6]
out = {'method':'complete structural data cones, witnessed 4-extrema Manhattan bound',
       'capture_pins':captures,'capture_pins_with_register_sources':len(worst),
       'primary_or_constant_only':sources_absent,'nets_visited':len(memo),
       'combinational_cycles':cycles,'over405':len(bad),'worst':worst[:30],
       'verdict':'PASS' if not bad and not cycles else 'FAIL'}
json.dump(out,open(os.environ['OUT'],'w'),indent=2)
print(json.dumps({k:v for k,v in out.items() if k not in ('worst','combinational_cycles')}))
