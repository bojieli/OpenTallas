#!/usr/bin/env python3
"""Summarize source-exact Yosys CDC root widths, recursively through hierarchy.
Use after production-parameter hierarchy/proc/opt/memory_map/opt; no timing claim.
"""
import argparse, collections, json
from pathlib import Path

def census(data, top):
    mods=data['modules']; roots=collections.Counter(); macros=collections.Counter(); unresolved=[]
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
                if len(ck)==1: roots[str(bit(ck[0]))]+=len(con.get('Q',[]))
                else: unresolved.append({'path':here,'type':typ,'clock':ck})
            elif typ.startswith('ot_sram_'): macros[typ]+=1
            elif typ.startswith('$mem'): unresolved.append({'path':here,'type':typ})
    rootmap={}
    for pn,port in mods[top]['ports'].items():
        for i,b in enumerate(port['bits']): rootmap[b]=pn if len(port['bits'])==1 else f'{pn}[{i}]'
    walk(top,rootmap,top)
    return {'top':top,'root_sequential_bits':dict(roots),'SRAM_clock_pins_additional':dict(macros),'unresolved':unresolved,'counts_are':'optimized generic sequential bits before technology mapping/clock gating, not CTS sinks or timing'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('netlist',type=Path);ap.add_argument('--top',default='ot_hbm_svc_prefetch_block_cdc');ap.add_argument('--output',type=Path);a=ap.parse_args()
    result=census(json.loads(a.netlist.read_text()),a.top);s=json.dumps(result,indent=2)+'\n'
    if a.output: a.output.write_text(s)
    else: print(s,end='')
