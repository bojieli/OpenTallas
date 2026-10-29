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


def check_provider_root(P, source, provider):
    """Check an explicit local native reset output feeding one virtual START root.

    This checks declared real registered pins and conservative physical reach;
    it never treats those checks as built phase or reset timing qualification.
    """
    import math
    import gen_phys
    import start_provider_plan as SP
    errors=[]
    try:
        if not isinstance(source,dict) or source.get('port')!='rst_raw_n':
            raise ValueError('virtual START root requires its one explicit local rst_raw_n input')
        if not provider or not isinstance(provider,dict):
            raise ValueError('local root reset requires a physical START provider')
        roots=[n for n in provider.get('nodes',[]) if n.get('root')]
        if len(roots)!=1:raise ValueError('local root reset requires exactly one virtual START root')
        part=source['part'];pin=source['pin']
        if part not in P.parts:raise ValueError('root reset source is not a native partition')
        tn=P.parts[part]['type']
        native=next((q for q in scalar_pins(P,tn) if q['name']==pin),None)
        if native is None:raise ValueError('root reset source is not an actual registered wavefront output')
        xy=list(P.to_die(part,native['xy_um']))
        declared=source.get('xy_um',[])
        if len(declared)!=2 or any(not math.isfinite(float(v)) for v in declared) or any(abs(float(a)-b)>1e-6 for a,b in zip(declared,xy)):
            raise ValueError('root reset native pin position mismatch')
        net=network(P)
        if source.get('net')!=net['bindings'][part][pin]:raise ValueError('root reset source net mismatch')
        release=RT.wf_plan(P)['parts'][part]['release']
        if source.get('source_part_release_cycles')!=release:raise ValueError('root reset source release price mismatch')
        tw=gen_phys.LAYER_W[P.layer_budget['partition_signal_max']]/2
        hh=gen_phys.tap_pin_height(P,tn,pin)/2
        x,y=native['xy_um'];a=P.to_die(part,[x-tw,y-hh]);b=P.to_die(part,[x+tw,y+hh])
        rect=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]
        distance=SP.hop(rect,roots[0]['rect_um'])
        if distance>405+1e-6:raise ValueError(f'local root reset native pin to all root FF bodies {distance:.3f}um exceeds405')
        return dict(errors=[],part=part,pin=pin,net=source['net'],source_part_release_cycles=release,
                    max_hop_um=distance,physical_qualified=False,phase_qualified=False)
    except (KeyError,ValueError,TypeError,StopIteration) as ex:
        errors.append(str(ex))
    return dict(errors=errors,physical_qualified=False,phase_qualified=False)
