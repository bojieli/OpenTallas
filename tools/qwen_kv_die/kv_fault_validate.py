#!/usr/bin/env python3
"""Independent candidate geometry/graph check; never clock/reset/CDC admission."""
import argparse
import json
from pathlib import Path
from kv_fault_topology import Sites,CELL,REACH,distance


def validate(inv,plan):
    if plan['sources']!=inv['sources']:raise ValueError('source inventory changed')
    points={s['id']:s['pin_xy'] or s.get('successor_native_pin_xy') for s in inv['sources']}
    clocks={s['id']:s['clock'] for s in inv['sources']}
    latencies={s['id']:{s['id']:0} for s in inv['sources']}
    sites=Sites(inv['physical_obstacles']);ops={};used=set();lane_map={l['id']:l for l in inv['spare_transport_candidates']}
    for n in plan['nodes']:
        if n['id'] in points or n['id'] in ops:raise ValueError('duplicate node identity')
        x,y=n['placement']['x'],n['placement']['y']
        if n['placement']['orient']!='R0' or not sites.free(x,y):raise ValueError('overlapping/outside cell '+n['id'])
        sites.add([x,y,x+CELL,y+CELL]);points[n['id']]=[x+21.558,y+10.812];clocks[n['id']]=n['clock'];ops[n['id']]=n
    for t in plan['transports']:
        lane=lane_map[t['lane_id']];bit=t['payload_bit'];key=(lane['id'],bit)
        if key in used or bit not in lane['free_bits'] or t['stations']!=lane['stations']:raise ValueError('unqualified transport bit')
        if t['id'] in points or t['id'] in ops:raise ValueError('duplicate transport identity')
        if t['latency_cycles']!=lane['conservative_model_cycles']:raise ValueError('changed transport delay')
        if clocks[t['source']]!=lane['source_clock']:raise ValueError('wrong launch clock')
        if distance(points[t['source']],lane['input_pin_xy'][str(bit)])>REACH+1e-6:raise ValueError('long ingress edge')
        used.add(key);points[t['id']]=lane['output_pin_xy'][str(bit)];clocks[t['id']]=lane['destination_clock'];ops[t['id']]=t
    max_edge=0
    for n in plan['nodes']:
        if n['master']!='qkd_astk_fault_join' or n['latency']!=1:raise ValueError('unpriced primitive or latency')
        if n['kind']=='sticky':
            if n['b']!=n['id']:raise ValueError('sticky feedback missing')
        elif n['kind']=='pipe':
            if n['a']!=n['b']:raise ValueError('pipe contains tie/nonduplicate input')
        elif n['kind']!='join':raise ValueError('unknown node kind')
        x,y=n['placement']['x'],n['placement']['y']
        for k,p in enumerate(('a','b')):
            source=n[p]
            if source==n['id'] and n['kind']=='sticky':continue
            if source not in points or points[source] is None:raise ValueError('unknown source coordinate')
            if clocks[source]!=n['clock']:raise ValueError('untimed clock crossing')
            edge=distance(points[source],[x+.042,y+10.812+k*.144]);max_edge=max(max_edge,edge)
            if edge>REACH+1e-6:raise ValueError('long data edge '+n['id'])
    pending=dict(ops)
    while pending:
        ready=[]
        for id,n in pending.items():
            refs=[n['source']] if 'source' in n else [n['a'],n['b']]
            refs=[r for r in refs if not(n.get('kind')=='sticky' and r==id)]
            if all(r in latencies for r in refs):
                delay=n.get('latency_cycles',1);out={}
                for r in refs:
                    for src,age in latencies[r].items():out[src]=max(out.get(src,0),age+delay)
                latencies[id]=out;ready.append(id)
        if not ready:raise ValueError('cycle/unresolved graph')
        for id in ready:pending.pop(id)
    sink=plan['sink'];node=ops[sink]
    if node.get('kind')!='sticky':raise ValueError('sink not sticky')
    missing=set(s['id'] for s in inv['sources'])-set(latencies[sink])
    if missing:raise ValueError('missing real source coverage '+str(sorted(missing)))
    consumer=inv['consumer'];final_distance=distance(points[sink],consumer['pin_xy'])
    if final_distance>REACH or clocks[sink]!=consumer['clock']:raise ValueError('invalid final consumer edge')
    bound=max(latencies[sink].values())
    if plan['retirement_quiet_cycles']<bound or plan['max_leaf_latency_bound']!=bound:raise ValueError('latency/quiet underpriced')
    return dict(status='CANDIDATE_GRAPH_AND_DATA_GEOMETRY_PASS_NOT_PHYSICAL_ADMISSION',sources=len(inv['sources']),
                added_cells=len(plan['nodes']),used_existing_bits=len(used),max_data_edge_um=max_edge,
                final_consumer_edge_um=final_distance,max_leaf_latency=bound,leaf_latencies=latencies[sink],
                qualification='No clock/reset geometry, reset calendar, actual lane age, STA, routing or retirement schedule admission')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('inventory',type=Path);ap.add_argument('candidate',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();doc=validate(json.loads(a.inventory.read_text()),json.loads(a.candidate.read_text()));a.out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:v for k,v in doc.items() if k!='leaf_latencies'}))
if __name__=='__main__':main()
