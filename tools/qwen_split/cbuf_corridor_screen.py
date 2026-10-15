#!/usr/bin/env python3
"""Read frozen C21s diagnostic graph; never assume its skipped relays are free."""
import collections
import hashlib
import json
from pathlib import Path
import re

OUT=Path('results/arch/qwen_split_compute_1014/native_cbuf_corridor_1103')
SRC=OUT/'inputs/out'
LOCK=Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
REGION=[19744.968,14713.92,19856.88,17832.96]


def write(name,data):
    assert json.loads(LOCK.read_text())['owner']=='codex'
    (OUT/name).write_text(json.dumps(data,indent=2)+'\n')


def overlaps(a,b):
    return a[0]<=b[2] and a[2]>=b[0] and a[1]<=b[3] and a[3]>=b[1]


def bounds(q):
    return [min(p[0]for p in q),min(p[1]for p in q),max(p[0]for p in q),max(p[1]for p in q)]


def main():
    graph=json.loads((SRC/'rom_tp8b.json').read_text())
    run=json.loads((SRC/'relay_run.json').read_text())
    inst={q['n']:q for q in graph['insts']}
    text=(SRC/'case/die.v').read_text()
    placement=(SRC/'case/place.tcl').read_text()
    orientation={n:o for n,o in re.findall(r'findInst (\S+)\] [\d.]+ [\d.]+ (R0|MX|MY|R180)',placement)}
    packs={p.stem:json.loads(p.read_text())for p in (SRC/'pins').glob('*.json')if p.stem!='INDEX'}
    connections=collections.defaultdict(list)
    unknown=[]
    for m in re.finditer(r'^\s+(\w+)\s+(\w+)\s*\((.*?)\);',text,re.M|re.S):
        master,name,body=m.groups()
        if name not in inst:continue
        if master not in packs:
            unknown.append(dict(instance=name,master=master,why='No assigned pin pack'));continue
        for port,expr in re.findall(r'\.(\w+)\(([^()]*)\)',body):
            nets=set(re.findall(r'\bn_(\w+)\b',expr))
            if not nets:continue
            spec=packs[master]['ports'].get(port)
            if spec is None:
                unknown.append(dict(instance=name,master=master,port=port,why='No assigned port'));continue
            q=inst[name];w,h=q['w'],q['h']
            if 'positions_xy_um'in spec:
                points=spec['positions_xy_um']
            else:
                lo,hi=spec['range_um'];face=spec['face']
                points=([(lo,0),(hi,0)]if face=='S'else[(lo,h),(hi,h)]if face=='N'else[(0,lo),(0,hi)]if face=='W'else[(w,lo),(w,hi)])
            xy=[];ori=orientation.get(name,'UNKNOWN')
            for x,y in points:
                if ori in ('MY','R180'):x=w-x
                if ori in ('MX','R180'):y=h-y
                xy.append((q['x']+x,q['y']+y))
            endpoint=dict(instance=name,master=master,port=port,bits=spec['bits'],direction=spec['direction'],
                          face=spec['face'],layer=spec['layer'],orient=ori,bbox=bounds(xy),expression=expr,
                          coordinate_scope='Assigned port range/explicit interior points; not routed wire shapes')
            for net in nets:connections[net].append(endpoint)
    occupants=[];edge_occupants=[]
    for q in inst.values():
        box=[q['x'],q['y'],q['x']+q['w'],q['y']+q['h']]
        if overlaps(box,REGION):
            (occupants if box[0]<REGION[2] and box[2]>REGION[0] else edge_occupants).append(q)
    incident=[];endpoint_inside=[]
    for name,family,width,names in graph['buses']:
        endpoints=connections.get(name,[])
        if not endpoints:
            unknown.append(dict(bus=name,bits=width,why='No mapped endpoint'));continue
        boxes=[p['bbox']for p in endpoints]
        box=[min(p[0]for p in boxes),min(p[1]for p in boxes),max(p[2]for p in boxes),max(p[3]for p in boxes)]
        if not overlaps(box,REGION):continue
        inside=[p for p in endpoints if overlaps(p['bbox'],REGION)]
        record=dict(bus=name,family=family,bits=width,bbox=box,endpoints=endpoints,
                    endpoints_incident_to_window=inside,
                    spans_both_x_boundaries=box[0]<REGION[0]and box[2]>REGION[2],
                    spans_both_y_boundaries=box[1]<REGION[1]and box[3]>REGION[3],
                    scope='Potential endpoint-span incidence only; routing may detour and allocated C21 relay occupancy is absent')
        incident.append(record)
        if inside:endpoint_inside.append(name)
    family=collections.defaultdict(lambda:dict(buses=0,bits_per_bus_sum=0,endpoint_pin_bits=0))
    for q in incident:
        f=family[q['family']];f['buses']+=1;f['bits_per_bus_sum']+=q['bits'];f['endpoint_pin_bits']+=sum(p['bits']for p in q['endpoints'])
    # Sweep two vertical cuts, reporting every possible y-range intersection.
    # These are interval upper bounds, not physical cut usage measurements.
    cuts=[]
    for x in [REGION[0],sum(REGION[::2])/2,REGION[2]]:
        events=[]
        for q in incident:
            a,b,c,d=q['bbox']
            if a<=x<=c:
                events.extend([(max(b,REGION[1]),q['bits'],q['bus']),(min(d,REGION[3]),-q['bits'],q['bus'])])
        live=peak=0;at=None
        for y,delta,name in sorted(events,key=lambda q:(q[0],q[1])):
            live+=delta
            if live>peak:peak,at=live,y
        cuts.append(dict(x=x,peak_possible_bits=peak,y=at,scope='Endpoint bbox overlap bound; not actual routed usage'))
    old_fine=[q for q in run['cuts'].get('fine_top',[])if (q['ax']=='x'and REGION[0]<=q['pos']<=REGION[2]and q['win'][0]<=REGION[3]and q['win'][1]>=REGION[1])or(q['ax']=='y'and REGION[1]<=q['pos']<=REGION[3]and q['win'][0]<=REGION[2]and q['win'][1]>=REGION[0])]
    manifest=[]
    for p in sorted((OUT/'inputs').rglob('*')):
        if p.is_file():manifest.append(dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    result=dict(schema='qwen.cbuf.corridor.screen.v1',region=REGION,width_um=round(REGION[2]-REGION[0],6),
                source='C21s SOURCE59fb67ed5, OT_RELAY_SKIP; immutable copied graph and assigned pins',
                full_C21='OPEN: EPYC1TB c21/out empty when collected; full allocator still has no emitted graph/relay occupancy',
                verdict='NO_WIDENING_PROPOSAL_SUPPORTED',hard_occupants=occupants,boundary_occupants=edge_occupants,
                endpoint_span_incident_buses=len(incident),family=dict(family),buses_with_endpoint_inside=endpoint_inside,
                cuts=cuts,existing_fine_top_in_window=old_fine,unknowns=unknown,
                open=['Full C21 allocated relay population/homes, cut usage and clock/reset branches absent',
                      'All incident actual routed wire/PG/via shapes absent; empty macro boxes do not imply free corridor',
                      'C21s older CROM/CBUF graph differs from proposed native R3/D3 cohort',
                      'Endpoint-span burden cannot be subtracted as measured usage or credited as guaranteed free tracks'],
                inputs=manifest)
    write('receipt.json',result);write('incident_buses.json',incident)
    print(json.dumps({k:result[k]for k in ['verdict','hard_occupants','endpoint_span_incident_buses','family','buses_with_endpoint_inside','cuts','existing_fine_top_in_window']},indent=2))


if __name__=='__main__':main()
