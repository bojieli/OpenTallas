#!/usr/bin/env python3
"""Extract current real HWIN endpoint/bit and reset boundaries, without dates.

This reads existing native binder products only. Declared lane cycles remain
separate from physical clock/landing qualification and actual launch bookings.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def named(text):
    result={};i=0
    while i<len(text):
        m=re.search(r'\.(\w+)\s*\(',text[i:])
        if not m:break
        name=m[1];start=i+m.end();depth=1;j=start
        while depth and j<len(text):
            depth+=(text[j]=='(')-(text[j]==')');j+=1
        if depth:raise ValueError('unterminated native binding')
        result[name]=text[start:j-1].strip();i=j
    return result


def instance(text,name):
    m=re.search(r'^\s*(\w+)\s*(?:#\(([^;]*?)\)\s*)?'+re.escape(name)+r'\s*\(',text,re.M)
    if not m:raise ValueError('actual emitted instance absent '+name)
    start=m.end();j=start;depth=1
    while depth and j<len(text):
        depth+=(text[j]=='(')-(text[j]==')');j+=1
    if depth:raise ValueError('unterminated actual emitted instance '+name)
    return dict(module=m[1],params=named(m[2]or''),ports=named(text[start:j-1]))


def bits(text,expr):
    widths={m[3]:int(m[1])+1 if m[1]else 1 for m in
            re.finditer(r'\b(?:wire|reg)\s*(?:\[(\d+):(\d+)\])?\s+(\w+)\s*[,;)]',text)}
    def expand(expr):
        expr=expr.strip()
        if expr.startswith('{')and expr.endswith('}'):
            inner=expr[1:-1];parts=[];start=depth=0
            for i,c in enumerate(inner):
                if c in '{(':depth+=1
                elif c in '})':depth-=1
                elif c==','and depth==0:parts.append(inner[start:i]);start=i+1
            parts.append(inner[start:]);return [b for p in reversed(parts)for b in expand(p)]
        m=re.fullmatch(r'(\w+)(?:\[(\d+)(?::(\d+))?\])?',expr)
        if not m:raise ValueError('unsupported native endpoint expression '+expr)
        name=m[1];hi=int(m[2])if m[2]else widths[name]-1;lo=int(m[3])if m[3]else(int(m[2])if m[2]else 0)
        if lo>hi:raise ValueError('native endpoint bit order reversed')
        return [(name,i)for i in range(lo,hi+1)]
    return expand(expr)


def extract(bind,mutate_source_bit=False):
    bind=Path(bind);rtl=bind/'rtl'
    latency=json.loads((bind/'bind_latency.json').read_text())
    reset=json.loads((bind/'bind_reset.json').read_text())
    if mutate_source_bit:
        hit=next(b for b in latency['buses']if ['leaf','u_seqhost.u_seqhost','mu_c_7n',0]in b['source_bits'])
        hit['source_bits'][hit['source_bits'].index(['leaf','u_seqhost.u_seqhost','mu_c_7n',0])][3]=1
    top=(rtl/'s81_bound_top.sv').read_text();seq=instance(top,'seqhost')
    source_file=rtl/(seq['module']+'.sv');source=source_file.read_text();atomic=instance(source,'u_u_seqhost')
    routes=[];identities={str(source_file):hashlib.sha256(source.encode()).hexdigest()}
    for endpoint in ('7n','7s','0n','0s'):
        bus=next(b for b in latency['buses']if b['src']=='seqhost'and
                 ['leaf','u_seqhost.u_seqhost','mu_c_'+endpoint,0]in b['source_bits'])
        dest=instance(top,bus['dst']);dest_file=rtl/(dest['module']+'.sv');text=dest_file.read_text()
        identities[str(dest_file)]=hashlib.sha256(text.encode()).hexdigest()
        bout=instance(source,'u_bout_'+bus['bus_out']);bin_=instance(text,'u_bin_'+bus['bus_in'])
        if bout['module']not in('ot_dp_st','ot_dp_ste')or bin_['module']not in('ot_dp_st','ot_dp_ste'):
            raise ValueError('actual native boundary register primitive differs')
        emitted=bits(source,bout['ports']['d']);lep=instance(text,'u_u_lep');land=instance(text,'u_u_land')
        consumer={0:bits(text,lep['ports']['mu_c']),1:bits(text,land['ports']['rc'])}
        qname=bin_['ports']['q'];mapped=[]
        for kind,port,width in [(0,'mu_c_'+endpoint,34),(1,'mu_rc_'+endpoint,11)]:
            indices=[]
            for bit in range(width):
                found=[i for i,s in enumerate(bus['source_bits'])if s==['leaf','u_seqhost.u_seqhost',port,bit]]
                if len(found)!=1:raise ValueError('actual source bit missing/duplicated')
                i=found[0];indices.append(i)
                if emitted[i] != ('w_u_seqhost_'+port,bit)or consumer[kind][bit]!=(qname,i):
                    raise ValueError('actual source/consumer pin bit differs: '+repr((endpoint,kind,bit,i,emitted[i],consumer[kind][bit],qname)))
            mapped.append(dict(kind=kind,source_port=port,bits=width,active_bus_indices=indices,
                consumer_module=lep['module']if kind==0 else land['module'],
                consumer_params=lep['params']if kind==0 else land['params'],
                consumer_port='mu_c'if kind==0 else'rc'))
        routes.append(dict(endpoint=endpoint,partition=bus['dst'],lane=bus['lane'],source_bus=bus['bus_out'],
                           consumer_bus=bus['bus_in'],declared_bound_stages=bus['bound_stages'],
                           actual_source_boundary=bout['module'],actual_consumer_boundary=bin_['module'],
                           consumer_boundary_D=bin_['ports']['d'],fields=mapped,
                           reset=reset['parts'][bus['dst']]))
    own=reset['parts']['seqhost'];type_reset=reset['types'][own['type']]
    return dict(schema='opentallas.s81.current_bound_hwin_endpoints.v1',status='ACTUAL_PIN_MAP_STATIC_RESET_BOUNDARY_ONLY',
        source_bind=str(bind),source_top_sha256=hashlib.sha256(top.encode()).hexdigest(),source_wrapper_sha256=identities,
        seqhost_module=seq['module'],seqhost_atomic=atomic['module'],seqhost_params=atomic['params'],
        native_atomic_reset_expression=atomic['ports']['rst_n'],seqhost_reset=own,seqhost_type_reset=type_reset,
        native_atomic_reset_pin_release=(own['release']-type_reset['release_after_pin']if atomic['ports']['rst_n']=='rst_n'else None),
        endpoint_routes=routes,global_HOST_KS_reset_dates_booked=False,clock_landing_phase_qualified=False,
        note='Bound stages are actual emitted lane declarations, not measured global epochs. Native atomic raw reset pin is separate from published tap release; no first HOST/KS date is chosen.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bind',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--mutate-source-bit',action='store_true');a=p.parse_args()
    r=extract(a.bind,a.mutate_source_bit)
    if a.out.exists():raise ValueError('preserve earlier endpoint extraction')
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print('ACTUAL_HWIN_ENDPOINTS',len(r['endpoint_routes']),'180 exact source bits; global epoch held')
