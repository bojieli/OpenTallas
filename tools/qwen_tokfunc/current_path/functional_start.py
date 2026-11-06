#!/usr/bin/env python3
"""Materialize a declared CA START tree on one nominal simulation clock.

Uses the same origin/PAD/EDGE_FALL and bounded reset-relay law as
start_stage_emit. Geometry, clock skew, and physical qualification remain
outside this functional provider. Real partition origins remain real inputs.
"""
import argparse, hashlib, json, re
from pathlib import Path

def emit(ca, module='ot_die_start_stages_fn'):
    if ca.get('start_tree') != 'clock':
        raise ValueError('requires an explicit clock START tree')
    regs=ca['regions']; pins=ca.get('start_pins',{}); edges=ca.get('start_ports',{})
    # Compressed eW sidecars omit virtual=False/True; their st:<path> names
    # are the declared virtual-node namespace, also referenced by start_pins.
    virtual={n for n,r in regs.items() if r.get('virtual',n.startswith('st:'))}
    if not virtual: raise ValueError('no declared virtual stages')
    ids={n:'s'+hashlib.sha256(n.encode()).hexdigest()[:16] for n in sorted(virtual)}
    if len(set(ids.values()))!=len(ids):raise ValueError('stage ID collision')
    roots=[n for n,r in regs.items() if r.get('parent') is None]
    if len(roots)!=1:raise ValueError('requires one declared root')
    incoming={};outs=[];ins=set();raw=set()
    for pid,e in edges.items():
        u,v=e['src'],e['dst']
        if u not in regs or v not in regs:raise ValueError(f'unknown region at {pid}')
        if v in incoming:raise ValueError(f'two parents for {v}')
        incoming[v]=u
        if regs[v].get('parent')!=u:raise ValueError(f'parent mismatch at {pid}')
        if v in virtual and u not in virtual:ins.add('rs_'+u);raw.add('rraw_'+u)
        if u in virtual and v not in virtual:outs.append(('pst_'+v,u))
    for n in virtual:
        if n!=roots[0] and incoming.get(n)!=regs[n].get('parent'):raise ValueError(f'missing parent for {n}')
    if len(set(n for n,_ in outs))!=len(outs):raise ValueError('duplicate START output')
    if pins:
        if ins!=set(pins['die_input_nets']):raise ValueError('declared rs pin mismatch')
        if raw!={p['net'] for p in pins['reset_inputs']}:raise ValueError('declared reset pin mismatch')
        if {n for n,_ in outs}!={p['net'] for p in pins['die_outputs']}:raise ValueError('declared pst pin mismatch')
    reset_wave=bool(ca.get('start_reset_wave'))
    if not reset_wave and raw:raw=set()
    ports=['input wire clk']+(['input wire rst_raw_n'] if roots[0] in virtual or not reset_wave else [])
    ports+=['input wire '+n for n in sorted(ins|raw)]+['output wire '+n for n,_ in sorted(outs)]
    sv=['`timescale 1ns/1fs',f'module {module} (',',\n'.join(ports),');']
    def start(n):return ids[n]+'_start' if n in virtual else 'rs_'+n
    for n in sorted(virtual):
        i=ids[n];r=regs[n];parent=r.get('parent');ef=int(bool(r.get('edge_fall')));pad=int(r.get('pad',0) or 0)
        if pad<0:raise ValueError('negative PAD')
        sv.append(f'wire {i}_start;')
        reset='rst_raw_n'
        if parent is not None and reset_wave:
            src=ids[parent]+'_raw' if parent in virtual else 'rraw_'+parent
            reset=i+'_raw';sv.append(f'wire {reset};')
            sv.append(f'ot_die_start_reset_relay_fn #(.EDGE_FALL({ef})) r_{i}(.clk(clk),.d({src}),.q({reset}));')
        if parent is None:
            sv.append(f'wire {i}_raw = rst_raw_n; wire {i}_start_d;')
            settle=int(ca.get('root_settle_cycles',64))
            if settle<1:raise ValueError('invalid SETTLE')
            sv.append(f'ot_dp_landing_root #(.SETTLE({settle})) u_{i}(.clk(clk),.rst_raw_n(rst_raw_n),.start({i}_start),.start_d({i}_start_d));')
        else:
            sv.append(f'ot_dp_landing_origin #(.PAD({pad}),.EDGE_FALL({ef})) u_{i}(.clk(clk),.rst_raw_n({reset}),.p_start({start(parent)}),.start({i}_start));')
    sv += [f'assign {n}={start(src)};' for n,src in sorted(outs)]+['endmodule']
    if reset_wave:
        sv += ['module ot_die_start_reset_relay_fn #(parameter bit EDGE_FALL=0)(input wire clk,input wire d,output wire q);','reg r0,r1;wire x;','if(EDGE_FALL) begin:gf reg rf;always@(negedge clk)rf<=d;assign x=rf;end else begin:gr assign x=d;end','always@(posedge clk)begin r0<=x;r1<=r0;end','assign q=r1;endmodule']
    return '\n'.join(sv)+'\n',dict(virtual_stages=len(virtual),real_root=roots[0] if roots[0] not in virtual else None,inputs=sorted(ins|raw),outputs=sorted(n for n,_ in outs),reset_wave=reset_wave,scope='Ideal common-clock functional carrier only; no geometry, measured skew, or native boot verdict')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sidecar',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--module',default='ot_die_start_stages_fn');a=p.parse_args()
    d=json.loads(a.sidecar.read_text());ca=d.get('count_aligned',d);sv,meta=emit(ca,a.module);a.out.mkdir(exist_ok=False,parents=True);(a.out/'start_stages_fn.sv').write_text(sv);meta['input_sidecar_sha256']=hashlib.sha256(a.sidecar.read_bytes()).hexdigest();(a.out/'start_stages_fn.json').write_text(json.dumps(meta,indent=1)+'\n');print('FUNCTIONAL_START_STAGED',meta['virtual_stages'],'real root',meta['real_root'],'ports',len(meta['inputs']),len(meta['outputs']))
