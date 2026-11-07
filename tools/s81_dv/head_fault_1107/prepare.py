"""Isolate an explicit local count-guard frontier; no codecs/arithmetic/die run.

Control expressions are copied from the selected parent, and clocks come from
the caller's retained TT/FF profile. No clock, start origin, K or guard is tuned.
Zero payload is a boundary premise; upstream fault propagation is not modeled.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

INST = re.compile(r'^\s*(ot_\w+)\s+(\w+)\s*\(\n(.*?)^\s*\);', re.M|re.S)
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')
PRIMS = {'ot_dp_rrelay','ot_dp_rgate','ot_dp_rsync','ot_dp_rsync_s2',
         'ot_dp_rsync_s3','ot_dp_head_raw_export_pair','ot_dp_landing_origin_s',
         'ot_dp_landing_root','ot_dp_landing_relay','ot_dp_origin_export_ff'}
OUT = {'q','export_q','start','start_d','sync_rst_n'}
BUSES = ['a_rx_i','b7_rx_i','b_i','h_rx_i','lepk_i0']


def ports(s):
    h = s[s.find('module '):s.find(');')+2]
    return {m[3]:(m[1],m[2] or '') for m in re.finditer(
        r'\b(input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(\[[^\]]+\]\s*)?(\w+)', h)}


def refs(expr):
    expr = re.sub(r"\d+'[sS]?[bBdDhHoO][0-9a-fA-FxXzZ_]+", '', expr)
    return re.findall(r'\b[A-Za-z_]\w*\b', expr)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--parent',type=Path,required=True)
    p.add_argument('--tt',type=Path,required=True)
    p.add_argument('--ff',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--parts',default='ctl',help='explicit comma-separated local count-guard frontier')
    a = p.parse_args(); a.out.mkdir(exist_ok=False,parents=True)
    tt = json.loads(a.tt.read_text())['phase']; ff = json.loads(a.ff.read_text())['phase']
    assert set(tt)==set(ff)
    readset = {}; definitions = {}; mapping = {}
    def source(mod):
        path=a.parent/(mod+'.sv'); s=path.read_text()
        readset[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return s
    parent = source('s81_head_top'); pp=ports(parent)
    instances = list(INST.finditer(parent))
    selected = a.parts.split(','); specs=[]; extra_by_module={}
    for part in selected:
        im=next(m for m in instances if m[2]==part)
        mod=im[1]; conn=dict(CONN.findall(im[3])); src=source(mod)
        for cm in re.finditer(r'(ot_dp_clk_landing_cas\s*#\([^;]*?\))\s+(u_cland_\w+)\s*\((.*?)\);',src,re.S):
            bus=cm[2][len('u_cland_'):]; pins=dict(CONN.findall(cm[3]))
            reset=pins['rst_n']; assert re.fullmatch(r'\w+',reset),(part,bus,reset)
            extra_by_module.setdefault(mod,set()).add(reset)
            specs.append(dict(part=part,bus=bus,params=cm[1].partition('ot_dp_clk_landing_cas')[2],
                              reset=reset,conn=conn))
    if not specs:raise ValueError('explicit frontier contains no literal CA rings')
    def control(mod):
        if mod in definitions:return definitions[mod][:2]
        s=source(mod); ps=ports(s); drivers={}
        for m in re.finditer(r'^\s*(?:\(\*[^\n]*?\*\)\s*)?(ot_dp_\w+)(?:\s*#\([^\n]*\))?\s+(\w+)\s*\((.*?)\);',s,re.M|re.S):
            if m[1] not in PRIMS:continue
            conn=dict(CONN.findall(m[3]))
            obj=dict(text=m[0], deps=[r for k,e in conn.items() if k not in OUT for r in refs(e)],
                     outputs=[e for k,e in conn.items() if k in OUT and e])
            for k,e in conn.items():
                if k in OUT and e:
                    assert re.fullmatch(r'\w+',e);assert e not in drivers;drivers[e]=obj
        for m in re.finditer(r'^\s*assign\s+(\w+)\s*=\s*([^;]+);',s,re.M):
            if m[1] not in drivers:drivers[m[1]]=dict(text=m[0],deps=refs(m[2]))
        targets=[k for k,(d,_) in ps.items() if d=='output' and k.startswith(
            ('rst_o_','start_o_','rst_start_raw_','fclk_out_','cland_fstart_out_'))]
        extra = sorted(extra_by_module.get(mod,set()))
        need=set();used=set();primary=set()
        def walk(n):
            if n in need:return
            need.add(n)
            if n in ps and ps[n][0]=='input':primary.add(n);return
            if n not in drivers:raise ValueError(f'{mod}: no literal control driver for {n}')
            obj=drivers[n];used.add(id(obj));need.update(obj.get('outputs',[]))
            for d in obj['deps']:walk(d)
        for n in targets+extra:walk(n)
        chosen=[];seen=set()
        for obj in drivers.values():
            if id(obj) in used and id(obj) not in seen:chosen.append(obj['text']);seen.add(id(obj))
        cn='control_'+mod; names=sorted(primary)+targets
        lines=[f'module {cn}(', ',\n'.join(
            [f'input wire {ps[n][1]}{n}' for n in sorted(primary)]+
            [f'output wire {ps[n][1]}{n}' for n in targets]),');']
        lines+=['wire '+n+';' for n in sorted(need-primary-set(targets))]
        lines+=chosen+['endmodule']
        definitions[mod]=(cn,names,'\n'.join(lines));return cn,names
    lines=['`timescale 1ns/1fs','module head_guard_tb;',
           'reg rst_n=0,refclk=0;always #0.4165 refclk=~refclk;integer cycles=0;',
           'always@(negedge refclk)begin cycles++;if(cycles==64)rst_n=1;end']
    for n,(d,w) in pp.items():
        if n=='rst_n' or n in tt or n.startswith('clk_region_'):continue
        lines.append('wire '+w+n+("=1'b0;" if n=='start' else ';'))
    lines += [line for line in parent[parent.find(');')+2:].splitlines() if re.match(r'^\s*wire\b',line)]
    for n in tt:
        def wave(v):
            r=v['rise_ps']; f=v['fall_ps'];assert 416.5+f-r>0 and 416.5+r-f>0
            return f'#{(416.5+r)/1000:.9f} {n}=1;forever begin #{(416.5+f-r)/1000:.9f} {n}=0;#{(416.5+r-f)/1000:.9f} {n}=1;end'
        lines += [f'reg {n}=0;',f'initial begin if($test$plusargs("FF"))begin {wave(ff[n])} end else begin {wave(tt[n])} end end']
    for m in instances:
        mod,n,b=m.groups()
        if n=='u_die_start_stages':lines.append(m[0]);continue
        assert 'pc_'+n in tt,(mod,n)
        cn,names=control(mod);conn=dict(CONN.findall(b));cs=[]
        for port in names:
            e='pc_'+n if port=='clk' or port.startswith('clk_t') else conn[port]
            cs.append('.'+port+'('+e+')')
        lines.append(cn+' '+n+'('+','.join(cs)+');')
        mapping[n]=dict(module=mod,ports=names)
    probes=[]
    labels=[]
    for spec in specs:
        part=spec['part'];bus=spec['bus'];params=spec['params'];conn=spec['conn']
        label=part+'__'+bus;name='probe_'+label;labels.append(label)
        w=int(re.search(r'\.W\((\d+)\)',params)[1])
        lines += [f'wire [{w-1}:0] q_{label};wire ready_{label},fault_{label};',
            f'ot_dp_clk_landing_cas{params} {name}(.fclk({conn["fclk_in_"+bus]}),'+
            f'.t_rst_n({conn["cland_fstart_in_"+bus]}),.clk(pc_{part}),'+
            f'.rst_n({part}.{spec["reset"]}),.strap_k({conn["strap_ca_k_"+bus]}+($test$plusargs("SHIFT4")?6\'d4:6\'d0)),'+
            f".d({w}'d0),.q(q_{label}),.ready(ready_{label}),.fault(fault_{label}));",
            f'reg seen_{label}=0;always@(negedge refclk)if(fault_{label}&&!seen_{label})begin seen_{label}=1;$display("FIRST_GUARD_FAULT {label} c%0d ready%b",cycles,ready_{label});end']
        probes.append(dict(part=part,bus=bus,width=w,clock=conn['fclk_in_'+bus],
                           reader_start=spec['reset'],writer_start=conn['cland_fstart_in_'+bus],K=conn['strap_ca_k_'+bus]))
    lines+=['always@(negedge refclk)if(cycles==800)begin']
    for b in labels:lines.append(f'$display("GUARD_FINAL {b} ready%0d fault%0d",ready_{b},fault_{b});')
    lines += ['$finish;end','endmodule']
    (a.out/'tb.sv').write_text('\n'.join(lines)+'\n')
    (a.out/'controls.sv').write_text('\n'.join(v[2] for v in definitions.values())+'\n')
    (a.out/'scope.json').write_text(json.dumps(dict(scope='explicit local CA guards only; no upstream faults, arithmetic, codecs or whole-die proof',
        frontier_parts=selected,
        primitive_control_parts=len(mapping),clocks=len(tt),probes=probes,source_readset=readset,
        TT_profile_sha256=hashlib.sha256(a.tt.read_bytes()).hexdigest(),FF_profile_sha256=hashlib.sha256(a.ff.read_bytes()).hexdigest(),
        production_enabled=False,physical_signoff=False),indent=2)+'\n')
    print('PREPARED',len(mapping),'control parts,',len(tt),'source clocks,',len(probes),'local guard probes')


if __name__=='__main__':main()
