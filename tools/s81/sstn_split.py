"""Exact two-leaf slot-station graph expansion. Requires real bound child views."""
import copy
import hashlib
import json
import re
from pathlib import Path

BASE_PORTS = dict(ck=('input',1), rs=('input',1), cci=('input',15), xai=('input',283),
                  xbi=('input',266), c0=('input',2), c1=('input',2), e0=('input',2),
                  e1=('input',2), si=('input',2), nf=('input',1), cc=('output',15),
                  xa=('output',283), xb=('output',266), so=('output',2))
PAYLOAD_PORTS = dict(ck=('input',1), rs=('input',1), i=('input',536), o=('output',536))


def expand(model, usage, mapping, views):
    """Preserve every net/bit order; duplicate only clock/reset endpoints and explicit inactive-role straps."""
    if model.get('sstn_split'):
        return False
    if model.get('bound_views'):
        raise ValueError('expand SSTN source before view binding, never rewrite a completed physical model')
    if mapping.get('schema') != 's81-sstn-two-leaf-map-v1':
        raise ValueError('unknown SSTN split map schema')
    leaves = mapping['leaves']; roles = {r['logical_parent']: r for r in mapping['roles']}
    if len(roles) != len(mapping['roles']):
        raise ValueError('duplicate SSTN role')
    for key, size in [('base',(84.24,30.24)),('payload',(86.4,25.92))]:
        leaf=leaves[key];view=views.get(leaf['master'])
        if not view:
            raise ValueError('SSTN split requires a real bound view: '+leaf['master'])
        if tuple(leaf['outline']) != size or abs(view['w']-size[0])>1e-6 or abs(view['h']-size[1])>1e-6:
            raise ValueError('SSTN split actual child outline differs from granted map')
    if leaves['base']['origin'] != [0,0] or leaves['payload']['origin'] != [86.4,0] or mapping['parent_outline'] != [172.8,30.24]:
        raise ValueError('SSTN split changes granted parent envelope')
    replacements={}; extra=[]; straps={}; records=[]
    names={i.name for i in model['insts']}
    for inst in model['insts']:
        ports=usage.get(inst.name,{})
        if inst.kind!='sstn' or 'x2i' not in ports:
            continue
        role='dsfd_sstn_'+''.join(k for k in ('e0','e1','c0','c1','si','nf','qt') if k in ports)+'_x2'
        spec=roles.get(role)
        if spec is None or model.get('sstn_ccpad',{}).get(inst.name):
            raise ValueError('unsupported SSTN split role or padded calendar: '+role)
        if inst.orient!='R0' or abs(inst.w-172.8)>.025 or abs(inst.h-30.24)>.025:
            raise ValueError('SSTN split needs current R0 172.8x30.24 slot')
        for port, signature in BASE_PORTS.items():
            if port in ports and ports[port] != signature:
                raise ValueError('SSTN base source ABI mismatch: '+port)
        if any(port not in ports for port,(direction,_) in BASE_PORTS.items() if direction=='output'):
            raise ValueError('SSTN split unsupported absent base output')
        if ports.get('x2i') != ('input',536) or ports.get('x2') != ('output',536):
            raise ValueError('SSTN split payload ABI mismatch')
        allowed=spec['base_role_straps']
        actual_missing={p for p,(d,w) in BASE_PORTS.items() if d=='input' and p not in ports}
        if set(allowed)!=actual_missing:
            raise ValueError('SSTN role straps would mask an active or unlisted port')
        for port, literal in allowed.items():
            if not re.fullmatch(r"[12]'b0+",literal) or int(literal.split("'")[0])!=BASE_PORTS[port][1]:
                raise ValueError('SSTN role strap is not exact-width zero')
        unsupported=set(ports)-set(BASE_PORTS)-{'x2i','x2'}
        if unsupported:
            raise ValueError('SSTN split unknown live ports: '+str(sorted(unsupported)))
        payload=copy.copy(inst);payload.name=inst.name+'__payload'
        if payload.name in names:raise ValueError('duplicate SSTN payload instance')
        if hasattr(inst, 'power_w'):
            original_power = inst.power_w
            inst.power_w = original_power * 566 / 1102
            payload.power_w = original_power - inst.power_w
        payload.master=leaves['payload']['master'];payload.kind='sstn_split_payload'
        payload.x=inst.x+86.4;payload.w,payload.h=86.4,25.92
        inst.master=leaves['base']['master'];inst.kind='sstn_split_base';inst.w,inst.h=84.24,30.24
        extra.append(payload);replacements[inst.name]=payload.name;straps[inst.name]=dict(allowed)
        records.append(dict(instance=inst.name, payload=payload.name,role=role,neutral_input_ports=dict(allowed)))
    if not replacements:
        raise ValueError('SSTN split selected no x2 stations')
    new_buses=[]
    for bid, cls, bits, endpoints in model['buses']:
        out=[]
        for name, port in endpoints:
            payload=replacements.get(name)
            if not payload:out.append((name,port));continue
            base=re.split(r'[\[@]',port,1)[0]
            if base in ('ck','rs'):
                out.extend([(name,port),(payload,port)])
            elif base in ('x2i','x2'):
                out.append((payload,('i' if base=='x2i' else 'o')+port[len(base):]))
            else:out.append((name,port))
        new_buses.append((bid,cls,bits,out))
    model['insts'].extend(extra);model['buses'][:]=new_buses
    model.setdefault('neutral_role_inputs',{}).update(straps)
    model['sstn_split']=dict(schema='s81-sstn-two-leaf-expansion-v1',instances=len(records),roles=records,
                             extra_production_edges=0,clock_delivery='same logical edge; separate actual phi-R per child')
    return True


def populate(source, macro, ports):
    """Plan against the actual published LEF contacts, never a guessed parent pin layout."""
    view=source.bound_views().get(macro.name)
    if not view:raise ValueError('SSTN split child has no bound physical view')
    pins=source.real_lef(view['lef'])['pins']
    macro.ports={};macro.order=[]
    for port,(_,width) in ports.items():
        names=[f'{port}[{i}]' for i in range(width)]
        if width==1 and names[0] not in pins:names=[port]
        if any(n not in pins for n in names):raise ValueError('SSTN split missing actual LEF bit '+port)
        macro.ports[port]=('rects',[(n,*pins[n]) for n in names]);macro.order.append(port)
