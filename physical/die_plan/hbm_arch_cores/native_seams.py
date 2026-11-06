"""Validate selected native seams against reciprocal hard-child connectivity in the selected parent plan."""
import gzip
import hashlib
import json
import re
from pathlib import Path

SCHEMA='opentallas.native_hard_child_seam.v1'
RANGED_SCHEMA='opentallas.native_hard_child_seam.v2'


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
    if request.get("schema")==RANGED_SCHEMA:
        return validate_ranged(plan,pdir,view,scope,request,plan_sha256)
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


def validate_ranged(plan,pdir,view,scope,request,plan_sha256):
    """Validate a reciprocal family cut against exact bit-level parent connectivity.

    v2 is explicit and opt-in. Every endpoint is a named hard child of the same
    parent, with full bus coverage. The selected elaborated parent must retain
    those children as exact-master blackboxes. Its actual nets, directions,
    clocks, resets and exclusive two-endpoint use are checked, not inferred
    from coarse core_conns or declared ranges. Timing and protocol closure are
    still the parent's responsibility.
    """
    pdir=Path(pdir);scope=sorted(set(scope))
    if not scope or request.get('module')!=view['module']:
        raise ValueError('ranged seam needs exact module and nonempty scope')
    expected=set()
    for parent,typ in plan['partition_types'].items():
        for core in typ.get('hard_cores',[]):
            if core.get('module')==view['module']:
                _,digest=read_json(pdir/core['pins_file'])
                if digest==view['pins_sha256']:
                    if list(core['outline_um'])!=list(view['outline_um']):
                        raise ValueError('ranged view outline differs from parent child')
                    expected.add((parent,core['inst']))
    if not expected:raise ValueError('ranged seam view has no matching parent child')
    seen=set();contexts=[];bus_widths=None;captures=[]
    for ctx in request.get('contexts',[]):
        parent=ctx['parent_partition_type']
        if parent not in plan['partition_types']:raise ValueError('unknown ranged seam parent')
        children={c['inst']:c for c in plan['partition_types'][parent].get('hard_cores',[])}
        if len(children)!=len(plan['partition_types'][parent].get('hard_cores',[])):
            raise ValueError('duplicate hard child instance')
        record=ctx['netlist'];rel=Path(record['path'])
        if rel.is_absolute() or '..' in rel.parts:raise ValueError('netlist path must be inside plan directory')
        netlist,digest=read_json(pdir/rel)
        if digest!=record['sha256']:raise ValueError('parent netlist hash mismatch')
        top=netlist['modules'][record['top']];cells=top.get('cells',{})
        # Include all cells and top ports: a third sink or exposed external net
        # invalidates the internal cut even if all declared peers agree.
        uses={}
        for inst,cell in cells.items():
            for port,bits in cell.get('connections',{}).items():
                for bitidx,bit in enumerate(bits):
                    if type(bit)==int:uses.setdefault(bit,[]).append((inst,port,bitidx))
        for port,desc in top.get('ports',{}).items():
            for bitidx,bit in enumerate(desc['bits']):
                if type(bit)==int:uses.setdefault(bit,[]).append(('$parent',port,bitidx))
        endpoints={};all_pins={}
        for ep in ctx['endpoints']:
            inst=ep['inst']
            if inst in endpoints or inst not in children:raise ValueError('duplicate or absent endpoint')
            core=children[inst]
            pins,pinsha=read_json(pdir/core['pins_file']);wds=widths(pins)
            if ep['module']!=core['module'] or ep['pins_sha256']!=pinsha:
                raise ValueError('endpoint master or pin identity mismatch')
            cell=cells.get(inst)
            if not cell or cell['type']!=core['module']:
                raise ValueError('actual endpoint cell/master mismatch')
            abstract=netlist['modules'].get(cell['type'],{})
            blackbox=abstract.get('attributes',{}).get('blackbox',0)
            if not (blackbox is True or blackbox==1 or (isinstance(blackbox,str) and re.fullmatch(r'0*1',blackbox))):
                raise ValueError('endpoint must be retained as a hard-child blackbox')
            for port,bits in cell.get('connections',{}).items():
                declared=abstract.get('ports',{}).get(port,{})
                if len(declared.get('bits',[]))!=len(bits) or declared.get('direction')!=cell.get('port_directions',{}).get(port):
                    raise ValueError('actual cell port disagrees with hard-child abstract')
            for role in ('clock_port','reset_port'):
                port=ep[role]
                if wds.get(port)!=1 or cell.get('port_directions',{}).get(port)!='input':
                    raise ValueError('endpoint clock/reset must be scalar input')
                bits=cell['connections'].get(port,[])
                if len(bits)!=1 or type(bits[0])!=int:raise ValueError('endpoint clock/reset missing or constant')
            if ep['clock_port']==ep['reset_port']:raise ValueError('clock and reset cannot alias a port')
            if not ep.get('buses'):raise ValueError('endpoint has no scoped seam bus')
            endpoints[inst]=ep;all_pins[inst]=wds
        for inst,ep in endpoints.items():
            cell=cells[inst];wds=all_pins[inst]
            for bus,links in ep['buses'].items():
                if bus in (ep['clock_port'],ep['reset_port']) or bus not in wds:
                    raise ValueError('invalid scoped seam bus')
                own=cell['connections'].get(bus,[])
                direction=cell.get('port_directions',{}).get(bus)
                if len(own)!=wds[bus] or direction not in ('input','output'):
                    raise ValueError('actual scoped port width/direction mismatch')
                covered=set()
                for link in links:
                    peer=link['peer_inst'];port=link['peer_port']
                    if peer==inst or peer not in endpoints:raise ValueError('peer not another declared hard endpoint')
                    pep=endpoints[peer];pcell=cells[peer]
                    if link['peer_module']!=pep['module'] or port not in pep['buses']:
                        raise ValueError('peer master or reciprocal scoped port mismatch')
                    lo,plo,n=link['own_lsb'],link['peer_lsb'],link['width']
                    if any(type(v)!=int for v in (lo,plo,n)) or lo<0 or plo<0 or n<1:
                        raise ValueError('range needs nonnegative integer offsets and positive width')
                    if lo+n>wds[bus] or plo+n>all_pins[peer].get(port,0):raise ValueError('range outside port')
                    bits=set(range(lo,lo+n))
                    if covered & bits:raise ValueError('overlapping own ranges')
                    covered.update(bits)
                    reciprocal=dict(own_lsb=plo,width=n,peer_inst=inst,peer_module=ep['module'],peer_port=bus,peer_lsb=lo)
                    if pep['buses'][port].count(reciprocal)!=1:raise ValueError('missing exact reciprocal range')
                    other=pcell['connections'].get(port,[])
                    if len(other)!=all_pins[peer][port] or pcell.get('port_directions',{}).get(port)!={'input':'output','output':'input'}[direction]:
                        raise ValueError('peer actual width/direction differs')
                    for role in ('clock_port','reset_port'):
                        if cell['connections'][ep[role]]!=pcell['connections'][pep[role]]:
                            raise ValueError('native seam clock/reset nets differ')
                    for offset in range(n):
                        bit=own[lo+offset]
                        endpoints_for_bit={(inst,bus,lo+offset),(peer,port,plo+offset)}
                        if type(bit)!=int or bit!=other[plo+offset] or set(uses.get(bit,[]))!=endpoints_for_bit or len(uses.get(bit,[]))!=2:
                            raise ValueError('actual range is reordered, constant, external or has extra load')
                if covered!=set(range(wds[bus])):raise ValueError('scoped bus ranges do not cover all bits')
            key=(parent,inst)
            if key in expected:
                if key in seen:raise ValueError('duplicate selected parent context')
                if set(ep['buses'])!=set(scope):raise ValueError('selected scope differs from ranged declaration')
                selected={b:wds[b] for b in scope}
                if bus_widths is not None and selected!=bus_widths:raise ValueError('replica widths differ')
                bus_widths=selected;seen.add(key)
                contexts.append(dict(parent_partition_type=parent,child_inst=inst,child_module=ep['module'],
                                     peers=ep['buses'],family_endpoints=ctx['endpoints'],
                                     clock_port=ep['clock_port'],reset_port=ep['reset_port'],
                                     netlist_sha256=digest,netlist_top=record['top']))
        captures.append(dict(parent_partition_type=parent,**record))
    if seen!=expected:raise ValueError('ranged seam omits a matching view replica')
    return dict(schema=RANGED_SCHEMA,module=view['module'],scope_buses=scope,bus_widths=bus_widths,
                plan_sha256=plan_sha256,pins_sha256=view['pins_sha256'],parent_netlists=captures,parent_contexts=contexts)
