"""Explicit native net-root clock census for planning, never a period/CDC waiver.

The complete parent census proves which root clocks each FF and macro pin.
Child FFs stay inside the child and never inflate the parent's core-clock grid.
Unplaced census coordinates are not interpreted as spatial sink inventory.
"""
import json
import math
import re
from collections import Counter
from pathlib import Path


def _load(P,name):
    p=Path(name)
    if not p.is_absolute():p=(Path(P.path).parent if P.path else Path.cwd())/p
    return json.loads(p.read_text())


def _census(P,path,sha,module):
    c=_load(P,path)
    if not re.fullmatch(r'[0-9a-f]{64}',sha or '') or c.get('source_odb_sha256')!=sha:
        raise ValueError('native clock census source ODB identity mismatch')
    if c.get('top_module')!=module:raise ValueError('native clock census top module mismatch')
    ports={};nets={}
    for p in c.get('clock_root_ports',[]):
        port,net=p.get('port'),p.get('net')
        if p.get('dir')!='INPUT' or not isinstance(port,str) or not isinstance(net,str) or port in ports or net in nets:
            raise ValueError('native clock census requires unique actual INPUT roots and nets')
        root=port
        if port.endswith('[0]'):
            base=port[:-3]
            if {r['port'] for r in c['clock_root_ports'] if r['port'].startswith(base+'[')}=={port}:root=base
        ports[port]=dict(root=root,net=net);nets[net]=root
    counts=Counter();seen=set()
    for p in c.get('ff_clock_pins',[]):
        key=(p.get('inst'),p.get('pin'))
        if not all(isinstance(x,str) and x for x in key) or key in seen or p.get('net') not in nets:
            raise ValueError('native clock census duplicate/unrooted FF clock pin')
        seen.add(key);counts[p['net']]+=1
    if len(seen)!=c.get('ff_count') or dict(counts)!=c.get('ff_clock_net_counts'):
        raise ValueError('native clock census FF rows/counts disagree')
    return c,ports,nets,counts


def contract(P,tn):
    t=P.types[tn];spec=t.get('clock',{}).get('native_domains')
    if spec is None:return None
    if spec.get('schema')!='opentallas.native_clock_domains.v1':raise ValueError('native clock domain contract schema')
    c,ports,nets,counts=_census(P,spec['census_file'],spec['source_odb_sha256'],t['module'])
    roots={p['root']:dict(net=p['net'],parent_ff=counts[p['net']]) for p in ports.values()}
    core=spec.get('core_root')
    if core!='clk' or core not in roots:raise ValueError('native clock core root must be the generated partition clk input')
    inventory={h['inst']:h['module'] for h in t.get('hard_cores',[])}
    inventory.update({h.get('physical_inst',h['inst']):h.get('physical_master',h['module']) for h in t.get('contents',[]) if h.get('lef')})
    actual={}
    for p in c.get('macro_clock_pins',[]):
        key=(p['inst'],p['master'],p['pin'])
        if key in actual or inventory.get(p['inst'])!=p['master'] or p['net'] not in nets:
            raise ValueError('native macro clock witness differs from actual planned module/pin/root inventory')
        actual[key]=nets[p['net']]
    declared={}
    for p in spec.get('macro_pins',[]):
        key=(p['inst'],p['module'],p['pin'])
        if key in declared or actual.get(key)!=p['root']:raise ValueError('native macro clock binding differs from its actual net root')
        declared[key]=p['root']
    if declared!=actual:raise ValueError('native macro clock binding inventory is incomplete')
    if any(ff['inst'].startswith(inst+'.') or ff['inst'].startswith(inst+'/')
           for ff in c.get('ff_clock_pins',[]) for inst,_,_ in actual):
        raise ValueError('parent FF census includes internal FFs below a hard macro')
    children=[];child_instances=set()
    for child in spec.get('children',[]):
        key=(child['inst'],child['module'],child['pin'])
        if child['inst'] in child_instances:raise ValueError('duplicate child clock census')
        child_instances.add(child['inst'])
        if actual.get(key)!=child['root']:raise ValueError('child clock is not connected to its declared parent net root')
        cc,cp,cn,co=_census(P,child['census_file'],child['source_odb_sha256'],child['module'])
        if child['pin'] not in cp or len(cp)!=1:raise ValueError('child clock census does not have its declared sole native input')
        children.append(dict(inst=child['inst'],module=child['module'],native_pin=child['pin'],root=child['root'],internal_ff=cc['ff_count']))
    return dict(core_root=core,roots=roots,macro_pins=declared,children=children,
                core_grid_parent_ff=roots[core]['parent_ff'],child_internal_ff_excluded=sum(x['internal_ff'] for x in children),
                source_odb_sha256=spec['source_odb_sha256'],spatial_status='NOT QUALIFIED: unplaced FF census supplies counts, not positions',
                electrical_status='PREP only: clock period/source/phase qualification is separate')


def macro_root(P,tn,inst,module,pin):
    c=contract(P,tn)
    return None if c is None else c['macro_pins'].get((inst,module,pin))


def summary(P,tn):
    c=contract(P,tn)
    if c is None:return None
    return {k:v for k,v in c.items() if k!='macro_pins'}


def core_planning_sites(P,tn):
    """Optional explicit planning positions for parent FFs on the actual core root.

    No inference from cell count, NONE ODB coordinates, child internal FFs, or
    another root. Without explicit sites the caller retains its ordinary mode.
    """
    c=contract(P,tn)
    if c is None:return None
    rows=P.types[tn]['clock']['native_domains'].get('planned_sink_sites')
    if rows is None:return None
    per={}
    for root,sites in rows.items():
        if root not in c['roots']:raise ValueError('planning sinks use an unknown native root')
        clean=[]
        for x,y,n in sites:
            if not all(math.isfinite(v) for v in (x,y,n)) or n<=0:raise ValueError('invalid native-domain planning sink')
            clean.append((float(x),float(y),float(n)))
        if abs(sum(p[2] for p in clean)-c['roots'][root]['parent_ff'])>1e-6:
            raise ValueError('native-domain planning sink demand differs from parent FF inventory')
        per[root]=clean
    if c['core_root'] not in per:raise ValueError('native core root has no explicit planning positions')
    return per[c['core_root']]
