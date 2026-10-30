#!/usr/bin/env python3
"""Narrow, opt-in BD entry correction on an OWN copied plan; no cycles added."""
import argparse
import json
from pathlib import Path

a = argparse.ArgumentParser()
a.add_argument('plan')
root = Path(a.parse_args().plan)
module = 'ot_hgi_sm_xload_cl2_bdring'
xy = [60.48, 108.0]
rect = [56.16, 103.68, 64.8, 112.32]

def read(n):
    return json.loads((root/n).read_text())

def write(n,d):
    f=root/n
    if f.is_symlink():
        f.unlink()
    f.write_text(json.dumps(d,indent=1)+'\n')

def point(p,w,h,o):
    x,y=p
    if o=='R0': return [x,y]
    if o=='MX': return [x,h-y]
    if o=='MY': return [w-x,y]
    if o=='R180': return [w-x,h-y]
    raise ValueError('unhandled orientation '+o)

plan=read('die_plan.json')
ce=read('clock_entries.json')
entries=read('entries.json')
entries[module]=dict(source='BD current-outline centre entry, 120.96x216, zero cycle delta',xy=xy)
count=0
for typ,cores in ce.items():
    if not isinstance(cores,dict): continue
    for inst,c in cores.items():
        if not isinstance(c,dict) or c.get('module')!=module: continue
        c.update(xy_um=xy,island_um=rect,source='BD current-outline centre entry, replaces stale 86.4x302.4 centre')
        count+=1
assert count==4,count
plan['clock']['mesh']['core_islands'][module]=dict(
    rule='12.2a1 single centre clock/reset island; maximum corner reach168.48um<200um',
    frame='core',instances=4,rects_um=[rect])
changed={}
for typ,t in plan['partition_types'].items():
    for c in t.get('hard_cores',[]):
        if c.get('module')!=module: continue
        local=point(xy,*c['outline_um'],c.get('orient','R0'))
        local=[round(z+o,3) for z,o in zip(local,c['origin_um'])]
        taps=[q for q in t['clock']['taps'] if q['name'] in (c['inst'],c['inst']+'.clk')]
        assert len(taps)==1,(typ,c['inst'],len(taps))
        taps[0]['xy']=local
        taps[0]['note']='BD current-outline centre; corrected stale aspect-repair entry; zero cycles'
        changed[typ,taps[0]['name']]=local
assert len(changed)==4
parts={p['name']:p for p in plan['partitions']}
export=read('clock_taps_die.json')
updated=0
for tap in export:
    key=tap['type'],tap['tap']
    if key not in changed: continue
    p=parts[tap['part']]
    w,h=plan['partition_types'][p['type']]['outline_um']
    local=point(changed[key],w,h,p.get('orient','R0'))
    tap['xy_die_um']=[round(z+o,3) for z,o in zip(local,p['origin_um'])]
    updated+=1
assert updated==4,updated
for name,d in [('die_plan.json',plan),('clock_entries.json',ce),('entries.json',entries),('clock_taps_die.json',export)]:
    write(name,d)
print(json.dumps(dict(module=module,entry_um=xy,island_um=rect,core_entries=count,die_exports=updated,cycle_delta=0)))
