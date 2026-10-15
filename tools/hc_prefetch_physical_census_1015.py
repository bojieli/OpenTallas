#!/usr/bin/env python3
"""Summarize source-exact Yosys CDC root widths, recursively through hierarchy.
Use after production-parameter hierarchy/proc/opt/memory_map/opt; no timing claim.
"""
import argparse, collections, json
from pathlib import Path

def census(data, top):
    mods=data['modules']; roots=collections.Counter(); macros=collections.Counter(); unresolved=[]
    cells_by_root=collections.defaultdict(collections.Counter); widths=collections.Counter()
    if top not in mods:
        candidates=[n for n,m in mods.items() if n.endswith('\\'+top) and int(str(m.get('attributes',{}).get('top','0')),2)==1]
        if len(candidates)!=1: raise ValueError(f'No unique elaborated top for {top}: {candidates}')
        top=candidates[0]
    def walk(name, mapping, path):
        mod=mods[name]
        def bit(b): return mapping.get(b, f'{path}:{b}') if isinstance(b,int) else b
        for cn,c in mod.get('cells',{}).items():
            typ=c['type']; con=c.get('connections',{}); here=f'{path}/{cn}'
            if typ in mods and not mods[typ].get('attributes',{}).get('blackbox',0):
                childmap={}
                for pn,port in mods[typ].get('ports',{}).items():
                    for a,b in zip(port['bits'],con.get(pn,[])): childmap[a]=bit(b)
                walk(typ, childmap, here)
            elif 'dff' in typ.lower():
                ck=con.get('CLK',con.get('C',[]))
                if len(ck)==1:
                    root=str(bit(ck[0]));width=len(con.get('Q',[]));roots[root]+=width
                    cells_by_root[root][typ]+=1;widths[width]+=1
                else: unresolved.append({'path':here,'type':typ,'clock':ck})
            elif typ.startswith('ot_sram_'): macros[typ]+=1
            elif typ.startswith('$mem'): unresolved.append({'path':here,'type':typ})
    rootmap={}
    for pn,port in mods[top]['ports'].items():
        for i,b in enumerate(port['bits']): rootmap[b]=pn if len(port['bits'])==1 else f'{pn}[{i}]'
    walk(top,rootmap,top)
    primitive=bool(widths) and set(widths)=={1} and all(t.startswith('$_') for counts in cells_by_root.values() for t in counts)
    return {'top':top,'root_sequential_bits':dict(roots),'root_sequential_cells':{r:dict(c) for r,c in cells_by_root.items()},'sequential_cell_width_histogram':dict(widths),'bitwise_primitive_mapping_complete':primitive,'SRAM_clock_pins_additional':dict(macros),'unresolved':unresolved,'counts_are':('bitwise technology primitives before library mapping/clock gating, not CTS sinks or timing' if primitive else 'optimized generic sequential bits before technology mapping/clock gating, not CTS sinks or timing')}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('netlist',type=Path);ap.add_argument('--top',default='ot_hbm_svc_prefetch_block_cdc');ap.add_argument('--output',type=Path);a=ap.parse_args()
    result=census(json.loads(a.netlist.read_text()),a.top);s=json.dumps(result,indent=2)+'\n'
    if a.output: a.output.write_text(s)
    else: print(s,end='')
