#!/usr/bin/env python3
"""Readonly actual geometry inventory for clock/PDN scheduling review."""
import argparse,json
from collections import Counter
from pathlib import Path
from openroad import Tech,Design

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--odb',required=True);p.add_argument('--out',required=True)
a=p.parse_args();t=Tech();d=Design(t);d.readDb(a.odb);b=d.getBlock();u=b.getDbUnitsPerMicron()
def box(q):return [v/u for v in (q.xMin(),q.yMin(),q.xMax(),q.yMax())]
insts=Counter();masters={};pins={};special={};row_length=0
for obj in b.getInsts():
    m=obj.getMaster();insts[m.getName()]+=1;masters[m.getName()]=m
for name,m in masters.items():
    geometries=Counter()
    for term in m.getMTerms():
        if str(term.getSigType()) not in ('POWER','GROUND'):continue
        for pin in term.getMPins():
            for g in pin.getGeometry():geometries[g.getTechLayer().getName()]+=1
    pins[name]=dict(instance_count=insts[name],master_pg_shapes=sum(geometries.values()),
                    instantiated_pg_shapes=insts[name]*sum(geometries.values()),by_layer=dict(geometries))
for name in ('VDD','VSS'):
    net=b.findNet(name);types=Counter()
    for sw in net.getSWires():
        for r in sw.getWires():
            if r.isVia():types['VIA']+=1
            else:types[r.getTechLayer().getName()]+=1
    special[name]=dict(types)
for row in b.getRows():
    q=row.getBBox();row_length+=(q.xMax()-q.xMin())/u
result=dict(schema='opentallas.qwen.clock_pg_inventory.v1',odb=a.odb,
            actual_die_um=box(b.getDieArea()),actual_row_derived_core_um=box(b.getCoreArea()),
            physical_rows=len(b.getRows()),horizontal_row_length_um=row_length,
            actual_supply_special_shapes=special,
            total_supply_special_shapes=sum(sum(v.values()) for v in special.values()),
            total_instantiated_master_pg_shapes=sum(v['instantiated_pg_shapes'] for v in pins.values()),
            largest_master_pg_shape_contributions=sorted(pins.items(),key=lambda x:-x[1]['instantiated_pg_shapes'])[:20],
            clock_cells=sum(v for k,v in insts.items() if k.startswith('BUF')),
            power_qualified=False,timing_qualified=False,production_admitted=False)
Path(a.out).write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1),flush=True)
