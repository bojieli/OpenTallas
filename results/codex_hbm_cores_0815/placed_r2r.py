"""Full placed register-pair geometry census through combinational connectivity.

Run inside the pinned OpenROAD image with ODB and OUT environment variables.
All sequential data/control inputs except clocks are traversed. Memory macros
stop a register path. Distances are placed instance-centre Manhattan lower
bounds, not routed wire lengths or a timing claim. No per-endpoint path pruning.
"""
import collections
import functools
import heapq
import json
import os
import sys
import odb

sys.setrecursionlimit(100000)
db=odb.dbDatabase.create();odb.read_db(db,os.environ['ODB'])
block=db.getChip().getBlock();scale=db.getTech().getDbUnitsPerMicron()
insts={i.getId():i for i in block.getInsts()}
flops={n:i for n,i in insts.items() if 'DFF' in i.getMaster().getName()}
coords={n:((i.getBBox().xMin()+i.getBBox().xMax())/(2*scale),
           (i.getBBox().yMin()+i.getBBox().yMax())/(2*scale)) for n,i in flops.items()}
drivers=collections.defaultdict(list);fanin={};nets={};cycles=set();active=set()
clock_names={'CLK','CK','C','GCLK'}
for n,i in insts.items():
    inputs=[]
    for term in i.getITerms():
        net=term.getNet()
        if net is None or term.getMTerm().getSigType() in ('POWER','GROUND'):continue
        ni=net.getId();nets[ni]=net
        if term.getIoType()=='OUTPUT':drivers[ni].append(n)
        elif term.getIoType()=='INPUT' and term.getMTerm().getName() not in clock_names:inputs.append(ni)
    fanin[n]=inputs

@functools.lru_cache(None)
def sources(net_id):
    if net_id in active:
        cycles.add(net_id);return frozenset()
    active.add(net_id);ret=set()
    for n in drivers.get(net_id,[]):
        if n in flops:ret.add(n)
        elif not insts[n].getMaster().isBlock():
            for other in fanin[n]:ret.update(sources(other))
    active.remove(net_id)
    return frozenset(ret)

count=0;over=0;maximum=0.;worst=[];endpoint_count=0;reset_pairs=0
for target,i in flops.items():
    endpoints=set();reset_sources=set()
    for term in i.getITerms():
        if term.getIoType()!='INPUT' or term.getMTerm().getName() in clock_names:continue
        net=term.getNet()
        if net is None:continue
        ss=sources(net.getId());endpoints.update(ss)
        if 'RESET' in term.getMTerm().getName() or 'SET' in term.getMTerm().getName():reset_sources.update(ss)
    if endpoints:endpoint_count+=1
    reset_pairs+=len(reset_sources)
    x,y=coords[target]
    for src in endpoints:
        sx,sy=coords[src];dist=abs(sx-x)+abs(sy-y);count+=1;maximum=max(maximum,dist)
        over+=dist>405+1e-6
        item=(dist,src,target)
        if len(worst)<24:heapq.heappush(worst,item)
        elif item>worst[0]:heapq.heapreplace(worst,item)
report=dict(scope=__doc__.strip(),verdict='INCOMPLETE' if cycles else ('REACH_FAIL' if over else 'PLACED_REACH_PASS'),
            register_count=len(flops),endpoints_with_register_fanin=endpoint_count,related_register_pairs=count,
            related_reset_pairs=reset_pairs,over_405um=over,max_manhattan_um=round(maximum,6),
            combinational_cycles=[nets[n].getName() for n in sorted(cycles)[:24]],
            pair_enumeration='ALL unique launch/capture register pairs; data and timed reset/control fanins',
            worst=[dict(distance_um=round(d,6),launch=insts[s].getName(),capture=insts[t].getName())
                   for d,s,t in sorted(worst,reverse=True)])
with open(os.environ['OUT'],'w') as f:json.dump(report,f,indent=1)
print(json.dumps({k:v for k,v in report.items() if k not in ('scope','worst','combinational_cycles')}))
