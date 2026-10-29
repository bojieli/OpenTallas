"""Native reset-wavefront pins and connectivity for static die infrastructure.

This exports the existing reset_tree contract. It neither invents registers nor
qualifies reset timing; physical native masters and actual relay RTL remain the
source of those registers. No raw reset fanout except the one root input.
"""
import re
import reset_tree as RT


def scalar_pins(P, tn):
    if not RT.wavefront(P):
        raise ValueError('reset infrastructure requires reset.release wavefront')
    return [dict(name=n, dir='out', kind='ctl', layer=P.layer_budget['partition_signal_max'],
                 xy_um=[float(x),float(y)]) for n,x,y in RT.out_pins(P,tn)]


def network(P):
    if not RT.wavefront(P):
        raise ValueError('reset infrastructure requires reset.release wavefront')
    W=RT.wf_plan(P)
    if W['unreachable'] or set(W['parts'])!=set(P.parts):
        raise ValueError('reset infrastructure has unreachable partitions')
    if W.get('long_hops'):
        raise ValueError('reset infrastructure has long native wavefront hops')
    root=W['root'];bindings={};wires=set();edges=[]
    for part,p in P.parts.items():
        tn=p['type'];b={}
        for pin in scalar_pins(P,tn):
            wire='rstw_'+re.sub(r'\W','_',part+'.'+pin['name'])
            if wire in wires:raise ValueError('reset net identifier collision '+wire)
            wires.add(wire);b[pin['name']]=wire
        bindings[part]=b
    for part,r in W['parts'].items():
        if r['parent'] is None:
            if part!=root:raise ValueError('multiple reset roots')
            wire='rst_n'
        else:
            parent,pin=r['source'].rsplit('.',1)
            if parent!=r['parent'] or pin not in bindings[parent]:
                raise ValueError('reset source lacks native output '+r['source'])
            wire=bindings[parent][pin]
            edges.append(dict(src=dict(part=parent,pin=pin),dst=dict(part=part,pin='arst_n'),
                              net=wire,hop_um=r['hop_um'],release_cycles=r['release']))
        bindings[part]['arst_n']=wire
    return dict(schema='ot_reset_route/1',root=root,wires=sorted(wires),bindings=bindings,
                edges=edges,raw_loads=[dict(part=root,pin='arst_n')],
                max_release_cycles=W['max_release'],max_hop_um=W['max_die_hop_um'],
                scope='native pin/net composition only; actual relay cells and timing not qualified')
