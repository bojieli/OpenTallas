#!/usr/bin/env python3
"""Extract private PC output FFs before P&R, preserving each original D/clock/reset and edge.

The input is a techmapped synthesis netlist. Every selected output must trace
through BUF/INV cells to a top-level FF; anything else is a hard error. Original
FFs retain all internal consumers. Each port gets its own kept FF and identical
polarity chain. Output FF sharing is removed with zero additional cycles.
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[5]/'tools/die_plan'))
try:
    import face_guard as FG
except ImportError:
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import face_guard as FG


def transform(text, top, ports):
    mods=FG.parse(text)
    if top not in mods: raise ValueError(f'missing top {top}')
    M=mods[top];F=FG.Flat(mods,top)
    top_cells={n for _,n,_ in M.cells}
    drv=collections.defaultdict(list)
    for ci,(typ,name,pp) in enumerate(F.cells):
        for p,(direc,bits) in pp.items():
            if direc=='out':
                for bit in bits:drv[F.find(bit)].append((ci,p))
    rename={p:f'ot_pc_internal_{i}' for i,p in enumerate(ports)}
    newcells=[];wires=list(rename.values());report=[]
    def net(bit):
        if bit in rename:return rename[bit]
        if bit.startswith('CONST_'):
            val=bit[6:].lower()
            if val not in ('0','1','x','z'):raise ValueError(f'unknown constant {bit}')
            return "1'b"+val
        if re.search(r'\\'+re.escape(bit)+r'\s',text):return '\\'+bit+' '
        if re.fullmatch(r'[A-Za-z_][\w$]*(?:\[[0-9]+\])?',bit):return bit
        # Escaped vector base followed by a true select.
        q=re.fullmatch(r'(.*)\[([0-9]+)\]',bit)
        if q and re.search(r'\\'+re.escape(q[1])+r'\s',text):return '\\'+q[1]+' ['+q[2]+']'
        raise ValueError(f'cannot serialize net {bit!r}')
    def clone(ci,outpin,newout,tag):
        typ,name,pp=F.cells[ci]
        if name not in top_cells:raise ValueError(f'FF/chain is not in top module: {name}')
        cs=[]
        for p,(di,bits) in pp.items():
            if len(bits)!=1:raise ValueError(f'expected scalar cell pin {name}.{p}')
            cs.append(f'.{p}({newout if p==outpin else net(bits[0])})')
        newcells.append(f'  (* keep = 1 *) {typ} ot_pc_copy_{tag} ({", ".join(cs)});')
    for i,port in enumerate(ports):
        chain=[];r=F.find(port);seen=set()
        while True:
            if r in seen:raise ValueError(f'cycle on {port}')
            seen.add(r);ds=drv.get(r,[])
            if len(ds)!=1:raise ValueError(f'{port}: expected one driver at {r}, got {ds}')
            ci,op=ds[0];typ,name,pp=F.cells[ci]
            if FG.is_ff(typ):break
            if not re.match(r'^(BUF|INV|HB)',typ):raise ValueError(f'{port}: non BUF/INV path {typ}')
            ins=[b for di,bs in pp.values() if di=='in' for b in bs]
            if len(ins)!=1:raise ValueError(f'{port}: non unary chain {typ}')
            chain.append((ci,op));r=F.find(ins[0])
        q=f'ot_pc_private_{i}_q';wires.append(q);clone(ci,op,q,f'{i}_ff')
        prev=q
        for j,(bi,bop) in enumerate(reversed(chain)):
            typ,name,pp=F.cells[bi];out=f'ot_pc_private_{i}_b{j}';wires.append(out)
            cs=[]
            for p,(di,bits) in pp.items():cs.append(f'.{p}({out if di=="out" else prev})')
            newcells.append(f'  {typ} ot_pc_copy_{i}_b{j} ({", ".join(cs)});');prev=out
        newcells.append(f'  assign {port} = {prev};')
        report.append(dict(port=port,original_ff=name,cycles=0,polarity_cells=len(chain)))
    # Replace references to the old output bits only in the top body, preserving
    # the vector port declarations. Every selected bit then has a private driver.
    start=text.index('module '+top+'(') if 'module '+top+'(' in text else text.index('module '+top+' ')
    end=text.index('endmodule',start)
    body=text[start:end]
    for port,new in rename.items():
        body=re.sub(r'(?<![\w$\\.])'+re.escape(port)+r'(?![\w$])',new,body)
    extra='\n  // Private same-edge port FF copies; original FFs serve internal loads only.\n'
    extra+='\n'.join('  wire '+w+';' for w in wires)+'\n'+'\n'.join(newcells)+'\n'
    return text[:start]+body+extra+text[end:],dict(module=top,copies=report,added_ff=len(ports),added_cycles=0)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('input');ap.add_argument('output');ap.add_argument('--top',required=True);ap.add_argument('--report',required=True);a=ap.parse_args()
    ports=[f'o_grp[{i}]' for i in range(297)]+['pc__fo[0]']
    out,rep=transform(Path(a.input).read_text(),a.top,ports)
    Path(a.output).write_text(out);Path(a.report).write_text(json.dumps(rep,indent=2)+'\n');print(f'PRIVATE_OUTPUTS {a.top} {len(ports)} FF copies; 0 added cycles')

if __name__=='__main__':main()
