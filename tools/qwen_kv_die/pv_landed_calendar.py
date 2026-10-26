#!/usr/bin/env python3
"""Derive the opt-in PV result-trunk calendar from actual landed crossing depths.

This does not change the column arithmetic or its controller.  The native vehicle
uses all 32 columns, both trunks and both 256-bit halves, with the real inject and
header leaves. Physical allocation and the bound programme remain separate work.
"""
import argparse
import gzip
import json
import re
from pathlib import Path


def derive(bg):
    extra = {}
    for g in bg['landing']:
        for m in g['members']:
            d = int(m['bound_stages']) - int(m['asbuilt_stages'])
            if d <= 0 or not g['sink'].startswith(('pvw_0__', 'pvw_1__')) or not m['source'].startswith(('pvw_0__', 'pvw_1__')):
                continue
            pair = int(g['sink'][4])
            if int(m['source'][4]) != pair:
                raise ValueError('cross-pair PV path')
            a = re.fullmatch(r'pvw_[01]__u_T([01])Q([01])_24_r0', g['sink'])
            if a and m['sink_port'] in ('a', 'y') and m['source'] == f'pvw_{pair}__u_T{a[1]}Q{a[2]}_21_r0.b':
                if m['sink_port'] == 'a':
                    extra[pair, int(a[1]), int(a[2]), 'link'] = d
            elif g['sink'].endswith('__u_RH_r0') and m['sink_port'] in ('a0', 'a1', 'b0', 'b1', 'a0t', 'a1t', 'a0v', 'a1v'):
                c,q=int(m['sink_port'][0] == 'b'),int(m['sink_port'][1])
                if m['source'] != f'pvw_{pair}__u_T{c}Q{q}_45_r0.b':
                    raise ValueError('unmapped header producer')
                if len(m['sink_port']) == 2:
                    extra[pair,c,q,'head'] = d
            else:
                raise ValueError('unmapped changed PV path: ' + str((g['sink'], m)))
    pairs = []
    for p in range(2):
        row = []
        for c in range(2):
            for kind in ('link', 'head'):
                if extra.get((p, c, 0, kind), 0) != extra.get((p, c, 1, kind), 0):
                    raise ValueError('unequal native half depths')
            row.append(dict(link_extra=extra.get((p, c, 0, 'link'), 0), header_extra=extra.get((p, c, 0, 'head'), 0)))
        pairs.append(row)
    result_extra = max(t['link_extra'] + t['header_extra'] for row in pairs for t in row)
    for row in pairs:
        for c, t in enumerate(row):
            t['head_delay'] = result_extra - t['link_extra'] - t['header_extra']
            t['head_tap'] = (0 if c == 0 else 6) + t['head_delay']
            t['injection_tap_extra'] = t['link_extra']
            if t['head_tap'] > 36 or (4 + t['injection_tap_extra']) > 36:
                raise ValueError('calendar exceeds existing 36-bit tap bank')
    return dict(schema='opentallas.kv.pv_landed_calendar.v1', kind='CANDIDATE_NOT_BOUND', result_cycles_added=result_extra,
                arithmetic_cycles_added=0, first_input_age_cycles_added=0, pairs=pairs,
                note='Retap column4/12 injection after node21->24 transport; phase both trunk heads to one output age.')


def emit(model):
    L = ['`timescale 1ns/1ps', 'module tb_pv_landed;', 'reg clk=0; always #0.4165 clk=~clk;',
         'integer cyc=0, errors=0; always @(posedge clk)cyc<=cyc+1;',
         'function automatic [511:0] word(input integer p,input integer s,input integer epoch);',
         'integer k; begin for(k=0;k<16;k=k+1)word[32*k+:32]=32\'h9e3779b9*(1+p*100003+s*71+k*907+epoch*1009);end endfunction',
         'wire pulse=((cyc%512)==150); wire[15:0] epoch=16\'(cyc/512);']
    for p, row in enumerate(model['pairs']):
        finals = []
        for c, t in enumerate(row):
            prev = ['','']
            for j in range(48 if c == 0 else 50):
                if j == 24:
                    for q in range(2):
                        for d in range(t['link_extra']):
                            n=f'p{p}c{c}q{q}j{j}land{d}'
                            L += [f'wire[257:0] {n}; ot_qkd_rlys #(.W(258)) {n}i(.ck(clk),.a({prev[q]}),.b({n}));'];prev[q]=n
                inj = j <= 45 and j % 3 == 0
                if inj:
                    s = 8*(c+2*((j//3)&1))+(j//3)//2
                    n = t['head_tap'] if j == 0 else s-(0 if c == 0 else 8)+(t['injection_tap_extra'] if j == 24 else 0)
                    # The native select source is the pre-landing token; its tap includes that landing's depth.
                    src = 'pulse' if j == 0 else (f'p{p}c{c}q0j{j-1}[257]')
                    dl=f'dl{p}_{c}_{s}';sel=f'sel{p}_{c}_{s}';pre=f'pre{p}_{c}_{s}'
                    L += [f'wire[35:0] {dl}; qkd_rlys_36 {dl}i(.ck(clk),.a({{{dl}[34:0],{src}}}),.b({dl}));']
                    L += [f'wire {sel}='+ (src if n == 0 else f'{dl}[{n-1}]')+';',
                          f'wire {pre}='+ (sel if j == 0 else (src if n == 1 else f'{dl}[{n-2}]'))+';']
                for q in range(2):
                    node=f'p{p}c{c}q{q}j{j}';L += [f'wire[257:0] {node};']
                    if inj:
                        dat=f'data{p}_{c}_{s}_{q}';L += [f'wire[511:0] full{dat}=word({p},{s},int\'(epoch));',f'wire[255:0] {dat}=full{dat}[{q*256}+:256];']
                        y=f'{{{sel},{sel},{dat}}}' if j == 0 else f'{{{prev[q]}[257],{sel},{dat}}}'
                        a=y if j == 0 else prev[q]
                        L += [f'qkd_rlyi_258s {node}i(.ck(clk),.s({pre}),.a({a}),.y({y}),.b({node}));']
                    else:
                        L += [f'ot_qkd_rlys #(.W(258)) {node}i(.ck(clk),.a({prev[q]}),.b({node}));']
                    prev[q]=node
            for q in range(2):
                for d in range(t['header_extra']):
                    n=f'head{p}_{c}_{q}_{d}';L += [f'wire[257:0] {n};ot_qkd_rlys #(.W(258)) {n}i(.ck(clk),.a({prev[q]}),.b({n}));'];prev[q]=n
            finals.append(prev)
        a,b=finals;L += [f'wire ov{p};wire[4:0] beat{p};wire[15:0] ep{p};wire[511:0] data{p};']
        L += [f'qkd_pv_rs_hd_f hd{p}(.ck(clk),.a0({a[0]}),.a1({a[1]}),.b0({b[0]}),.b1({b[1]}),'+
              f'.a0v({{31{{{a[0]}[256]}}}}),.a1v({{31{{{a[1]}[256]}}}}),.a0t({a[0]}[257]),.a1t({a[1]}[257]),.ep(epoch),'+
              f'.o_valid(ov{p}),.o_beat(beat{p}),.o_epoch(ep{p}),.o_data(data{p}));']
        L += [f'integer count{p}=0,last{p}=-1;always @(negedge clk)if(cyc>128&&ov{p})begin',
              f'if(beat{p}!==5\'(count{p}%32)||data{p}!==word({p},count{p}%32,int\'(ep{p}))||(count{p}%32!=0&&cyc!=last{p}+1))begin errors=errors+1;$display("PV_MISMATCH pair{p} cycle%0d beat%0d count%0d",cyc,beat{p},count{p});end',
              f'if(count{p}%32==0&&cyc%512!={200+model["result_cycles_added"]})begin errors=errors+1;$display("PV_AGE_MISMATCH pair{p} cycle%0d",cyc);end',
              f'count{p}=count{p}+1;last{p}=cyc;end']
    L += ['initial begin repeat(2100)@(negedge clk);if(count0!=128||count1!=128)errors=errors+1;',
          '$display("PV_LANDED_NATIVE counts%0d/%0d errors%0d",count0,count1,errors);if(errors)$fatal(1,"PV calendar mismatch");$finish;end','endmodule']
    return '\n'.join(L)+'\n'


def rewrite_netlist(source, target, model):
    """Retap real existing shift-bank pins, preserving their register feedback.

    The physical landing supplies the transport stages; they are not duplicated
    in this source rewrite. A fresh elaboration must measure the new selector
    paths. This is deliberately not a rewire-table depth override.
    """
    seen = set()
    nhead = model['pairs'][0][0]['head_delay']
    if nhead != 3:
        raise ValueError('source rewrite currently implements the B38 three-stage head bank')
    with gzip.open(source, 'rt') as fi, gzip.GzipFile(filename=str(target), mode='wb', mtime=0) as gz:
        for line in fi:
            if line.startswith('module qfd_die '):
                line += ('  wire [35:0] n_pvw_0__w_DL0_land;\n'
                         '  qkd_rlys_36 pvw_0__u_DL0_land_r0 (.ck(n_clk_core_c[0]), '
                         '.a({n_pvw_0__w_DL0_land[34:0], n_pvw_0__yv_w[0]}), .b(n_pvw_0__w_DL0_land));\n')
                seen.add('head-bank')
            m = re.search(r'qkd_rlyi_258s pvw_([01])__u_T([01])Q([01])_(0|24)_r0 ', line)
            if m:
                p,c,q,j = map(int,m.groups()); key=(p,c,q,j); pre=f'n_pvw_{p}__'
                if j == 24:
                    s = 4+8*c; d=model['pairs'][p][c]['injection_tap_extra']
                    old=f'.s({pre}rs_sp[{s}])'
                    if line.count(old)!=1: raise ValueError('unexpected native select wiring '+str(key))
                    line=line.replace(old,f'.s({pre}w_DL{s}[{2+d}])')
                    old=(f'{pre}w_DL4[3]' if c==0 else f'{pre}rs_sel[12]')
                    if line.count(old)!=1: raise ValueError('unexpected native V wiring '+str(key))
                    line=line.replace(old,f'{pre}w_DL{s}[{3+d}]');seen.add(key)
                elif c == 1:
                    old=f'{pre}rs_sp[8]'
                    if line.count(old)!=5:raise ValueError('unexpected head tag wiring '+str(key))
                    line=line.replace(old,f'{pre}w_DL8[{model["pairs"][p][c]["head_tap"]-1}]');seen.add(key)
                elif p == 0:
                    old=f'{pre}yv_w[0]'
                    if line.count(old)!=5:raise ValueError('unexpected T0 head wiring '+str(key))
                    line=line.replace(old,f'{pre}w_DL0_land[{nhead-1}]');seen.add(key)
            gz.write(line.encode())
    if len(seen)!=15:
        target.unlink(missing_ok=True)
        raise ValueError('incomplete source rewrite: '+str(seen))
    return dict(changed_inject_instances=14, new_leaf='pvw_0__u_DL0_land_r0', new_leaf_type='qkd_rlys_36',
                new_flops=36, source=str(source), target=str(target), verdict='NEEDS_FRESH_BIND_AND_PLAN')


if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('bus_groups',type=Path);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--source-netlist',type=Path,help='B38 native flattened netlist; emit opt-in source retaps')
    a=ap.parse_args()
    model=derive(json.loads(a.bus_groups.read_text()));a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'calendar.json').write_text(json.dumps(model,indent=2)+'\n');(a.out/'tb.sv').write_text(emit(model));print(json.dumps(model,sort_keys=True))
    if a.source_netlist:
        rec=rewrite_netlist(a.source_netlist,a.out/'die_bound_native_mission.v.gz',model)
        (a.out/'source_rewrite.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec,sort_keys=True))
