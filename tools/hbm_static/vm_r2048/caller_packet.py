#!/usr/bin/env python3
"""Materialize an explicit, default-off r2048 source event from actual callers.

Legacy-only lifts preserve original addressability; they never make upper
regular storage reachable. Native clients and a real publication map are
separate required source events. No plan, kit, route or input is modified.
"""
import argparse, hashlib, json, re
from pathlib import Path

INPUTS={**{f'rq{i}':(17,18) for i in range(5)}, **{f'wq{i}':(281,282) for i in range(2)},
        'dq':(281,282),'kq':(281,282),'xq':(276,277),'xq2':(276,277),'pq':(285,286)}
OUTPUTS={'eg':(276,277),'status':(18,18)}


def named_ports(text):
    out={};at=0
    while at<len(text):
        m=re.search(r'\.(\w+)\s*\(',text[at:])
        if not m:break
        start=at+m.end();end=start;depth=1
        while end<len(text) and depth:
            depth+=(text[end]=='(')-(text[end]==')');end+=1
        if depth:raise ValueError('unbalanced actual caller port')
        if m[1] in out:raise ValueError('duplicate caller port '+m[1])
        out[m[1]]=text[start:end-1].strip();at=end
    return out


def emit(source, abi, clocks=None, native=None, oneclk=False):
    cells=[c for c in abi['cells'] if c['path'].startswith('vmb_')]
    expected={f'vmb_{q}{b}' for q in ('SW','SE','NW','NE') for b in range(8)}
    if {c['path'] for c in cells}!=expected or len(cells)!=32:raise ValueError('need exactly32actual VM callers')
    if clocks is not None and set(clocks)!=expected:raise ValueError('explicit macro3 clock map must cover exactly32callers')
    native=native or {};replacements=[];records=[]
    for cell in cells:
        name=cell['path'];ports=cell['ports']
        if cell['module']!='hfd_vms_bank_native_q0_faces' or cell.get('params'):raise ValueError('unexpected actual source bank '+name)
        match=re.search(r'\bhfd_vms_bank_native_q0_faces\s+'+re.escape(name)+r'\s*\((.*?)\);',source,re.S)
        if not match:raise ValueError('actual bank caller absent '+name)
        conns=named_ports(match[1])
        if set(conns)!=set(ports):raise ValueError('actual caller/header port census differs '+name)
        for p,d in ports.items():
            if re.sub(r'\s+','',conns[p])!=re.sub(r'\s+','',d['source_expression']):raise ValueError('actual symbolic connection changed '+name+'.'+p)
        for p,(old,new) in {**INPUTS,**OUTPUTS}.items():
            if ports[p]['width']!=old or ports[p]['direction']!=('input' if p in INPUTS else 'output'):raise ValueError('actual field shape changed '+name+'.'+p)
        prefix='vmgrow__'+name
        wires={p:prefix+'__'+p for p in {**INPUTS,**OUTPUTS}}
        lines=[f'wire [{new-1}:0] {wires[p]};' for p,(_,new) in {**INPUTS,**OUTPUTS}.items()]
        old=lambda p:conns[p]
        new=lambda p:wires[p]
        adapter=[f'.legacy_rq({{{",".join(old(f"rq{i}") for i in reversed(range(5)))}}})', f'.native_rq({{{",".join(new(f"rq{i}") for i in reversed(range(5)))}}})',
                 f'.legacy_wq({{{old("wq1")},{old("wq0")}}})',f'.native_wq({{{new("wq1")},{new("wq0")}}})']
        for p in ('dq','kq','xq','xq2','pq'):adapter += [f'.legacy_{p}({old(p)})',f'.native_{p}({new(p)})']
        adapter += [f'.native_eg({new("eg")})',f'.legacy_eg({old("eg")})',f'.native_status({new("status")})',f'.legacy_status({old("status")})']
        lines.append('ot_vms_legacy_r2048_fields '+prefix+'__fields ('+', '.join(adapter)+');')
        mapped=dict(conns)
        mapped.update(wires)
        overrides=native.get(name,{})
        if set(overrides)-set(INPUTS):raise ValueError('unsupported native client override '+name)
        for p,expr in overrides.items():
            if not isinstance(expr,str) or not expr.strip():raise ValueError('explicit native source expression required')
            mapped[p]=expr
        if oneclk:
            clock_ports=['clk','clk_n','clk_s','clk_e','clk_w','clk_macro0','clk_macro1','clk_macro2']
            if len({re.sub(r'\s+','',conns[p]) for p in clock_ports})!=1:raise ValueError('actual caller clock aliases differ '+name)
            for p in clock_ports[1:]:mapped.pop(p)
        elif clocks is not None:mapped['clk_macro3']=clocks[name]
        elif not oneclk:mapped['clk_macro3']='REQUIRES_PLANNED_MACRO3_CLOCK'
        master='hfd_vms_bank_native_q0_faces_r2048_oneclk' if oneclk else 'hfd_vms_bank_native_q0_faces_r2048'
        lines.append(master+' '+name+' (\n'+',\n'.join(f'    .{p}({expr})' for p,expr in mapped.items())+'\n);')
        replacements.append((match.start(),match.end(),'\n'.join(lines)))
        records.append(dict(path=name,old_master=cell['module'],new_master=master,
            old_connections=conns,native_overrides=overrides,
            status_fault_receiver=dict(expression=old('status'),fault_bit=17,top_net_bits=ports['status']['top_net_bits']),
            macro3_clock=mapped.get('clk_macro3',mapped['clk']),oneclk=oneclk,native_upper_regular_client_requested=bool(overrides)))
    transformed=source
    for start,end,text in sorted(replacements,reverse=True):transformed=transformed[:start]+text+transformed[end:]
    event=dict(schema='opentallas.hbm.vm_r2048.source_event.v1',status='SOURCE_PACKET_ONLY',default_off=True,
        source_sha256=hashlib.sha256(source.encode()).hexdigest(),callers=records,bank_count=32,
        input_field_map=INPUTS,output_field_map=OUTPUTS,
        legacy_reachable_regular_words=2**18,physical_native_capacity_regular_words=2**19,
        added_cycles=0,native_override_expressions_supplied=bool(native),actual_native_17sector_producers_qualified=False,
        holds=['legacy lift alone cannot reach upper regular half; no2^19programme claim',
               'actual native source expressions require own width/producer/clock/region binding',
               'macro3 direct clock entry requires physical tap/PG/lot in atomicplan event',
               'source frontier, strict bind, diagnostics, timing and token qualification remain required'],
        full_token=False,SIGNED=False)
    return transformed,event


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for p in ('source','abi','out'):ap.add_argument('--'+p,type=Path,required=True)
    ap.add_argument('--apply',action='store_true',help='explicitly emit a fresh transformed top (default only packet)')
    ap.add_argument('--macro3-clocks',type=Path)
    ap.add_argument('--oneclk',action='store_true',help='explicit approved ONECLK candidate; requires allactual caller clock aliases identical')
    ap.add_argument('--native-ports',type=Path)
    a=ap.parse_args();read=lambda p:json.loads(p.read_text()) if p else None
    if a.apply and not a.macro3_clocks and not a.oneclk:ap.error('--apply requires explicit macro3 clock expressions; never infer a physical tap')
    source=a.source.read_text();new,event=emit(source,read(a.abi),read(a.macro3_clocks),read(a.native_ports),a.oneclk)
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'event.json').write_text(json.dumps(event,indent=1)+'\n')
    if a.apply:(a.out/'top_r2048.sv').write_text(new)
    print(json.dumps(dict(status=event['status'],callers=32,applied=a.apply,upper_regular_clients=event['native_override_expressions_supplied'],full_token=False)))


if __name__=='__main__':main()
