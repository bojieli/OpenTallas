#!/usr/bin/env python3
"""Build four physical ECTLK interfaces from the actual selected native HG call.

The archived column projector supplies only the approved bit ownership/drop map.
Controller parameters and parent connections come from --hg. A liveness file
is an untrusted interface proposal until current synthesis and reconstruction
prove it. Sparse inputs become contiguous spans, preserving original bit indices.
No logic is rescheduled; all four clocks are the selected HG's one die clock.
"""
import argparse
import copy
import importlib.util
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[4]
ARCH=REPO/'results/arch/kv_plan_1025/ectlk_columns'


def spans(bits):
    out=[]
    for b in sorted(bits):
        if not out or b!=out[-1][-1]+1:out.append([b])
        else:out[-1].append(b)
    return out


def build(hg, plan, live, out, template, sources):
    text=Path(hg).read_text()
    m=re.search(r'qkd_ectl3_kiss_st\s*#\((.*?)\)\s+u_ectl\s*\((.*?)\n\s*\);',text,re.S)
    if not m:raise ValueError('expected exactly the selected qkd_ectl3_kiss_st u_ectl call')
    params={k:int(v) for k,v in re.findall(r'\.(\w+)\(\s*(\d+)\s*\)',m[1])}
    if set(params)!={'HXK','MUT','QK_ISSUE_AGE','RESPONSE_LAT'}:raise ValueError(params)
    connections=dict(re.findall(r'\.(\w+)\(([^\n]*?)\)\s*(?:,|$)',m[2],re.M))
    clock=re.sub(r'\s+','',connections.get('ck',''))
    cm=re.fullmatch(r'\{(\w+),\1,\1\}',clock)
    if not cm:raise ValueError('quarter replacement requires the actual single-clock native call')
    spec=importlib.util.spec_from_file_location('ectlk_column_projector',ARCH/'ectlk_columns.py')
    project=importlib.util.module_from_spec(spec);spec.loader.exec_module(project)
    archive=(ARCH/'qkd_ectlk_columns.sv').read_text()
    h=re.search(r'module qkd_ectlk_reference\s*\((.*?)\n\);',archive,re.S)[1]
    ports=[(d,n,int(b)+1) for d,b,n in project.DECL.findall(h+'\n')]
    if {n for d,n,w in ports}!=set(connections):raise ValueError('native controller port census changed')
    pref='qkd_ectl3_kiss_st #('+', '.join(f'.{k}({v})' for k,v in params.items())+') u_leaf'
    reference='module qkd_ectlk (\n'+h+'\n);\n    '+pref+' (\n'+',\n'.join(f'        .{n}({n})' for d,n,w in ports)+'\n    );\nendmodule\n'
    legacy=json.loads((Path(plan)/'cores/qkd_ectlk_pins.json').read_text())
    lp=[]
    for pin in legacy['pins']:
        mm=re.fullmatch(r'(.*)\[(\d+)\]',pin['name'])
        if not mm:raise ValueError(pin['name'])
        x,y=pin['x'],pin['y'];edge=min([(x,'W'),(881.28-x,'E'),(y,'S'),(216-y,'N')])[1]
        lp.append(dict(bus=mm[1],bit=int(mm[2]),face=edge,x=x,y=y))
    rtl,manifest=project.generate(reference,lp)
    live=json.loads(Path(live).read_text())['quarters']
    mapping={};pin_deltas={};core_specs={}
    for q in range(4):
        name=f'qkd_ectlk_q{q}'
        a=rtl.index('module '+name+' (');b=rtl.index('\nendmodule',a)
        body=rtl[a:b];head,logic=body.split(');',1)
        old_ports={n:(d,int(hi)+1) for d,hi,n in project.DECL.findall(head+'\n')}
        new_ports={};bm={}
        for n,(direction,width) in old_ports.items():
            if direction=='output':
                new_ports[n]=(direction,width-1,0);continue
            bs=live[name]['live_inputs'].get(n,[])
            if not bs:continue
            for ix,run in enumerate(spans(bs)):
                pn=n if ix==0 else f'{n}_{run[0]}'
                new_ports[pn]=(direction,run[-1],run[0])
                for bit in run:bm[n,bit]=(pn,bit)
        # Every surviving RHS names a real physical input; discarded fields are
        # candidates for pruning only, and remain subject to the full miter.
        def repl(mm):
            old,n,bit=mm[1],mm[2],int(mm[3]);dst=bm.get((n,bit))
            return f'assign {old} = '+(f'{dst[0]}[{dst[1]}]' if dst else "1'b0")+';'
        logic=re.sub(r'assign\s+(old_\w+\[\d+\])\s*=\s*(\w+)\[(\d+)\];',repl,logic)
        declarations=[f'    {d} wire [{hi}:{lo}] {n}' for n,(d,hi,lo) in new_ports.items()]
        replacement='module '+name+' (\n'+',\n'.join(declarations)+'\n);'+logic
        rtl=rtl[:a]+replacement+rtl[b:]
        # Fix the composition call's widths explicitly; connecting a whole bus
        # to [1023:256] would incorrectly take its low 768 bits.
        call=re.search(r'    '+name+r' u_q'+str(q)+r' \((.*?)\n    \);',rtl,re.S)
        oldcall=call[0];con=[]
        for n,(d,hi,lo) in new_ports.items():
            if d=='output':con.append(f'.{n}(q{q}_{n})')
            elif n=='ck':con.append(f'.ck(ck[{q}])')
            else:
                src=n if n in old_ports else n.rsplit('_',1)[0]
                con.append(f'.{n}({src}[{hi}:{lo}])')
        rtl=rtl.replace(oldcall,'    '+name+' u_q'+str(q)+' (\n        '+',\n        '.join(con)+'\n    );',1)
        pins=json.loads((Path(plan)/f'cores/{name}_pins.json').read_text())
        pinlist=pins['pins'] if isinstance(pins,dict) else pins
        delta={}
        for pin in pinlist:
            pm=re.fullmatch(r'(.*)\[(\d+)\]',pin['name']);bus,bit=pm[1],int(pm[2])
            if old_ports.get(bus,('output',))[0]=='input':
                dst=bm.get((bus,bit))
                if dst is None:raise ValueError(f'{name}: current pin absent in liveness {bus}[{bit}]')
                oldname=pin['name']
                newname=f'{dst[0]}[{dst[1]}]'
                if 'name' in pin:pin['name']=newname
                if oldname!=newname:delta[oldname]=newname
        expected={f'{n}[{bit}]' for n,(d,hi,lo) in new_ports.items() for bit in range(lo,hi+1)}
        actual={p['name'] for p in pinlist}
        if actual!=expected:raise ValueError((name,'pin/port mismatch',sorted(actual-expected)[:4],sorted(expected-actual)[:4]))
        cj=copy.deepcopy(template);cj.update(module=name,type='kv3_hg',inst=f'ectl_q{q}',files=[str(p) for p in sources]+[str(out/'qkd_ectlk_columns.sv')],bound=str(out/'reference/kv3_hg_part.sv'))
        cj['port_decl']={n:list(v) for n,v in new_ports.items()}
        cj['pin_class']={f'{n}[{i}]':('clk' if n=='ck' else 'rst' if n=='rst_n' else 'data') for n,(d,hi,lo) in new_ports.items() for i in range(lo,hi+1)}
        cj['pin_bits']=sorted(expected)
        cj['report']={'added':[],'straps':[],'gap_bits':[],'clock_nets':{'clk':'ck[0]'},'native_profile':params,'source_instance':'u_ectl','quarter':q,'input_liveness':'PROPOSAL_REQUIRES_CURRENT_SYNTH'}
        cj['consistency']={'verdict':'REQUIRES_CURRENT_RECONSTRUCTION_AND_NATIVE_EMIT'}
        cj['clock_contract']={'domain':'one die clock','source':cm[1],'same_edge':True}
        core_specs[name]=cj;pin_deltas[name]={'renamed':delta,'pins':pins}
        mapping[name]={'physical_ports':cj['port_decl'],'native_input_bit_map':{f'{pn}[{pb}]':f'{n}[{ib}]' for (n,ib),(pn,pb) in bm.items()},'output_bits':manifest['quarters'][q]['output_bits']}
    native=[]
    for direction,n,width in ports:
        if direction=='input' and n!='ck':
            native.append(f'    wire [{width-1}:0] ectq_in_{n} = {connections[n]};')
    covered={}
    for q in range(4):
        name=f'qkd_ectlk_q{q}';c=[]
        for n,(d,hi,lo) in core_specs[name]['port_decl'].items():
            if d=='output':
                wire=f'ectq_q{q}_{n}';native.append(f'    wire [{hi}:{lo}] {wire};');c.append(f'.{n}({wire})')
                bits=manifest['quarters'][q]['output_bits'][n]
                for i,original_bit in enumerate(bits):
                    width=next(w for direction,p,w in ports if p==n)
                    target=connections[n] if width==1 else f'{connections[n]}[{original_bit}]'
                    native.append(f'    assign {target} = {wire}[{i}];')
                    if (n,original_bit) in covered:raise ValueError('multiple quarter drivers')
                    covered[n,original_bit]=q
            elif n=='ck':c.append(f'.ck({cm[1]})')
            else:
                src=n if n in manifest['compact_abi'] else n.rsplit('_',1)[0]
                original=manifest['compact_abi'][src]['bits']
                mapped=[original[i] for i in range(lo,hi+1)]
                if mapped==list(range(mapped[0],mapped[-1]+1)):
                    expr=f'ectq_in_{src}[{mapped[-1]}:{mapped[0]}]'
                else:expr='{'+', '.join(f'ectq_in_{src}[{i}]' for i in reversed(mapped))+'}'
                c.append(f'.{n}({expr})')
        native += [f'    {name} ectl_q{q} (', '        '+',\n        '.join(c), '    );']
    for direction,n,width in ports:
        if direction!='output':continue
        for bit in range(width):
            if (n,bit) not in covered:
                if bit not in project.DROPS.get(n,set()):raise ValueError(f'unmapped live output {n}[{bit}]')
                target=connections[n] if width==1 else f'{connections[n]}[{bit}]'
                native.append(f"    assign {target} = 1'b0; // approved dead static field")
    native_text=text[:m.start()]+'\n'.join(native)+text[m.end():]
    out.mkdir(parents=True,exist_ok=True);(out/'reference').mkdir(exist_ok=True)
    (out/'reference/kv3_hg_part.sv').write_text(text)
    (out/'reference/kit_rtl.json').write_text(json.dumps({'hard_macros':{}}))
    (out/'qkd_ectlk_columns.sv').write_text(rtl)
    (out/'kv3_hg_part_quarters.sv').write_text(native_text)
    for name,cj in core_specs.items():
        (out/f'{name}_core.json').write_text(json.dumps(cj,indent=1)+'\n')
        (out/f'{name}_pins.json').write_text(json.dumps(pin_deltas[name]['pins'],indent=1)+'\n')
    rec={'schema':'opentallas.ectlk.native_quarters.v1','native_profile':params,'clock':cm[1],'native_connections':connections,'added_cycles':0,'quarter_map':mapping,'pin_renames':{n:p['renamed'] for n,p in pin_deltas.items()},'status':'RECONSTRUCTION_AND_CURRENT_SYNTH_REQUIRED'}
    (out/'native_quarters.json').write_text(json.dumps(rec,indent=1)+'\n')
    return rec


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hg',required=True);p.add_argument('--plan-dir',required=True);p.add_argument('--live',required=True);p.add_argument('--template',required=True);p.add_argument('--sources',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();sources=[Path(x) for x in Path(a.sources).read_text().splitlines() if x.strip()]
    r=build(a.hg,a.plan_dir,a.live,Path(a.out).resolve(),json.loads(Path(a.template).read_text()),sources)
    print(json.dumps({'profile':r['native_profile'],'pin_renames':{k:len(v) for k,v in r['pin_renames'].items()},'status':r['status']}))
