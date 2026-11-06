"""Validate selected native seams against reciprocal hard-child connectivity in the selected parent plan."""
import gzip
import hashlib
import json
import re
from pathlib import Path

SCHEMA='opentallas.native_hard_child_seam.v1'


def read_json(path):
    path=Path(path)
    if not path.is_file():path=Path(str(path)+'.gz')
    raw=path.read_bytes()
    if path.suffix=='.gz':raw=gzip.decompress(raw)
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def widths(pins):
    out={}
    for row in pins:
        if 'name' in row:
            m=re.fullmatch(r'(.+)\[(\d+)\]',row['name'])
            bus,bit=(m.group(1),int(m.group(2))) if m else (row['name'],0)
        else:bus,bit=row['bus'],int(row.get('bit') or 0)
        if bit in out.setdefault(bus,set()):raise ValueError('duplicate native pin '+bus)
        out[bus].add(bit)
    for bus,bits in out.items():
        if bits!=set(range(len(bits))):raise ValueError('non-contiguous native bus '+bus)
    return {bus:len(bits) for bus,bits in out.items()}


def validate(plan,pdir,view,scope,request,plan_sha256):
    """All replicas of this module/pin view must have exclusively reciprocal peers in the same partition type.

    The request supplies peer MODULE + PORT, never an exemption by external port name. Peer instances and their
    parent contexts come from the plan itself. An absent/external/mixed connection or width mismatch rejects it.
    """
    pdir=Path(pdir);scope=sorted(set(scope))
    if not scope or request.get('schema')!=SCHEMA or request.get('module')!=view['module']:
        raise ValueError('native seam request needs its exact module and nonempty scope')
    if set(request.get('peers',{}))!=set(scope):raise ValueError('native seam request/selected buses differ')
    conns,conns_sha=read_json(pdir/'core_conns.json')
    cache={}
    def pin_info(core):
        key=core['pins_file']
        if key not in cache:
            pins,digest=read_json(pdir/key);cache[key]=(widths(pins),digest)
        return cache[key]
    contexts=[];bus_widths=None
    for parent,typ in plan['partition_types'].items():
        children={c['inst']:c for c in typ.get('hard_cores',[])}
        for child,core in children.items():
            if core.get('module')!=view['module']:continue
            own_widths,digest=pin_info(core)
            if digest!=view['pins_sha256']:continue
            if list(core['outline_um'])!=list(view['outline_um']):raise ValueError('native view outline differs from parent child')
            own=conns.get(parent,{}).get(child,{})
            links={}
            for bus in scope:
                peer_req=request['peers'][bus]
                targets=own.get(bus,[])
                if len(targets)!=1 or not targets[0].startswith('core:'):
                    raise ValueError(f'{parent}.{child}.{bus}: not an exclusive internal hard-child seam')
                peer=targets[0][5:]
                if peer==child or peer not in children:raise ValueError('native seam peer is not another hard child in '+parent)
                peer_core=children[peer];peer_port=peer_req['port']
                if peer_core['module']!=peer_req['module']:raise ValueError('native peer module differs from declared cut')
                peer_widths,_=pin_info(peer_core)
                if own_widths.get(bus)!=peer_widths.get(peer_port) or bus not in own_widths:
                    raise ValueError('native seam widths differ: '+bus+' / '+peer_port)
                back=conns.get(parent,{}).get(peer,{}).get(peer_port,[])
                if back!=['core:'+child]:raise ValueError('native seam peer is not exclusively reciprocal')
                links[bus]=dict(peer_inst=peer,peer_module=peer_core['module'],peer_port=peer_port,
                                peer_parent_partition_type=parent,
                                width=own_widths[bus],child_targets=targets,peer_targets=back)
            selected={bus:own_widths[bus] for bus in scope}
            if bus_widths is not None and bus_widths!=selected:raise ValueError('native seam replica widths differ')
            bus_widths=selected
            contexts.append(dict(parent_partition_type=parent,child_inst=child,child_module=core['module'],peers=links))
    if not contexts:raise ValueError('native seam view has no matching parent hard-child instance')
    return dict(schema=SCHEMA,module=view['module'],scope_buses=scope,bus_widths=bus_widths,
                plan_sha256=plan_sha256,pins_sha256=view['pins_sha256'],core_conns_sha256=conns_sha,
                parent_contexts=contexts)
