#!/usr/bin/env python3
"""Project the static ECTLK into four independently clocked output cones.

No logic is rescheduled: synthesis prunes each copy to its connected outputs.
The authoritative pin-bit map, not bus centres, chooses ownership. This is an
RTL candidate; inputs must be reduced from synthesized liveness before pinning.
"""
import argparse
import json
import re
from pathlib import Path

DROPS = {'so': set(range(13)) | {25} | set(range(282,410)),
         'req_v': {0}, 'req_t': {13}, 'si': set(range(537,633))}
DECL = re.compile(r'^\s*(input|output)\s+wire\s+\[(\d+):0\]\s+(\w+)\s*[,\n]', re.M)


def generate(source, pins, width=881.28):
    ports = [(d, n, int(msb)+1) for d, msb, n in DECL.findall(source)]
    if not ports or {n for _,n,_ in ports} != {p['bus'] for p in pins}:
        raise ValueError('source/pins bus census differs')
    bypin = {(p['bus'], p['bit']): p for p in pins}
    compact = {}
    for direction, name, size in ports:
        if name == 'ck':
            continue
        bits = [b for b in range(size) if b not in DROPS.get(name,set())]
        if bits:
            compact[name] = {'direction':direction, 'bits': bits}
    expected = {'so':271, 'req_t':13, 'si':537}
    for name,size in expected.items():
        if len(compact[name]['bits']) != size:
            raise ValueError(f'wrong static ABI for {name}')
    ownership = [{} for _ in range(4)]
    for name, port in compact.items():
        if port['direction'] != 'output':
            continue
        for bit in port['bits']:
            pin = bypin[name,bit]
            q = 0 if pin['face']=='W' else 3 if pin['face']=='E' else min(3,int(4*pin['x']/width))
            ownership[q].setdefault(name,[]).append(bit)
    def decl(direction,name,size):
        return f'    {direction} wire [{size-1}:0] {name}'
    inp = [(n,p['bits']) for n,p in compact.items() if p['direction']=='input']
    original_name = re.search(r'\bmodule\s+(\w+)\s*\(',source).group(1)
    renamed = re.sub(r'\b'+original_name+r'\b',original_name+'_reference',source)
    chunks = [renamed]
    quarter_maps=[]
    for q in range(4):
        outputs=ownership[q]
        quarter_maps.append({'module':f'qkd_ectlk_q{q}', 'input_bits':dict(inp), 'output_bits':outputs,
                             'input_liveness':'NOT_SYNTHESIZED', 'clock':'ck', 'added_schedule_cycles':0})
        declarations = [decl('input','ck',1)] + [decl('input',n,len(bs)) for n,bs in inp]
        declarations += [decl('output',n,len(bs)) for n,bs in outputs.items()]
        lines = [f'module qkd_ectlk_q{q} (', ',\n'.join(declarations), ');']
        connections=[]
        for direction,name,size in ports:
            if name=='ck':
                connections.append('.ck({3{ck[0]}})')
                continue
            lines.append(f'    wire [{size-1}:0] old_{name};')
            if direction=='input':
                live = compact.get(name,{}).get('bits',[])
                index={bit:i for i,bit in enumerate(live)}
                for bit in range(size):
                    rhs=f'{name}[{index[bit]}]' if bit in index else "1'b0"
                    lines.append(f'    assign old_{name}[{bit}] = {rhs};')
            else:
                for i,bit in enumerate(outputs.get(name,[])):
                    lines.append(f'    assign {name}[{i}] = old_{name}[{bit}];')
            connections.append(f'.{name}(old_{name})')
        lines += [f'    {original_name}_reference u_ref (', '        '+',\n        '.join(connections), '    );', 'endmodule']
        chunks.append('\n'.join(lines))
    # Compact composition ABI: exact counterpart to the approved static pin drop.
    ds=[decl('input','ck',4)] + [decl('input',n,len(bs)) for n,bs in inp]
    ds += [decl('output',n,len(p['bits'])) for n,p in compact.items() if p['direction']=='output']
    lines=['module qkd_ectlk_columns (', ',\n'.join(ds), ');']
    for q,outs in enumerate(ownership):
        con=[f'.ck(ck[{q}])']+[f'.{n}({n})' for n,_ in inp]
        for name,bits in outs.items():
            lines.append(f'    wire [{len(bits)-1}:0] q{q}_{name};')
            con.append(f'.{name}(q{q}_{name})')
            for i,bit in enumerate(bits):
                idx=compact[name]['bits'].index(bit)
                lines.append(f'    assign {name}[{idx}] = q{q}_{name}[{i}];')
        lines += [f'    qkd_ectlk_q{q} u_q{q} (', '        '+',\n        '.join(con), '    );']
    lines+=['endmodule']
    chunks.append('\n'.join(lines))
    # Legacy shim is for component equivalence only, never a physical core.
    lines=['module qkd_ectlk_columns_legacy (', ',\n'.join(decl(d,n,w) for d,n,w in ports), ');']
    con=['.ck({4{ck[0]}})']
    for direction,name,size in ports:
        if name=='ck': continue
        live=compact.get(name,{}).get('bits',[])
        if not live:
            if direction=='output': lines.append(f"    assign {name} = {size}'d0;")
            continue
        lines.append(f'    wire [{len(live)-1}:0] compact_{name};')
        con.append(f'.{name}(compact_{name})')
        if direction=='input':
            for i,bit in enumerate(live): lines.append(f'    assign compact_{name}[{i}] = {name}[{bit}];')
        else:
            index={bit:i for i,bit in enumerate(live)}
            for bit in range(size):
                rhs=f'compact_{name}[{index[bit]}]' if bit in index else "1'b0"
                lines.append(f'    assign {name}[{bit}] = {rhs};')
    lines += ['    qkd_ectlk_columns u_columns (', '        '+',\n        '.join(con), '    );', 'endmodule']
    chunks.append('\n'.join(lines))
    return '\n\n'.join(chunks)+'\n', {'schema':'opentallas.ectlk.columns.v1', 'source_module':original_name,
        'status':'RTL_CANDIDATE_NOT_PHYSICAL', 'added_schedule_cycles':0, 'quarters':quarter_maps,
        'compact_abi':compact, 'dropped_bits':{n:sorted(v) for n,v in DROPS.items()},
        'physical_obligations':['synthesized input liveness and private pin-flop preflight',
             'per-quarter area versus proposed outline', 'reset/start wavefront and actual-bit geometry review']}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('source',type=Path); ap.add_argument('pins',type=Path); ap.add_argument('out',type=Path)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    rtl, manifest=generate(a.source.read_text(),json.loads(a.pins.read_text()))
    (a.out/'qkd_ectlk_columns.sv').write_text(rtl)
    (a.out/'columns.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('output bits per column:',[sum(len(v) for v in q['output_bits'].values()) for q in manifest['quarters']])
if __name__=='__main__': main()
