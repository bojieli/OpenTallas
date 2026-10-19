#!/usr/bin/env python3
"""SAFE-QW-SLICE: deterministic reset partition of scalar/vector NBA state.

Independent nonblocking assignments remain simultaneous. Each <=32-bit slice
has a kept reset leaf; a two-level <=32-way tree adds two reset-release edges.
Arrays, blocking procedural state and unsupported statements fail closed.
"""
import argparse
import json
import re
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
import die_port_bind as P

TOK = re.compile(r'\w+|[^\s]')
NBA = re.compile(r'\b(\w+)\s*(\[[^;]*?\])?\s*<=\s*([^;]*);')

def statement_end(text, start):
    ts = list(TOK.finditer(text, start))
    def par(i):
        assert ts[i].group() == '('
        depth=1;i+=1
        while depth:
            depth += (ts[i].group()=='(') - (ts[i].group()==')');i+=1
        return i
    def stmt(i):
        token=ts[i].group()
        if token=='begin':
            i+=1
            if ts[i].group()==':':i+=2
            while ts[i].group()!='end':i=stmt(i)
            return i+1
        if token=='if':
            i=stmt(par(i+1))
            if i<len(ts) and ts[i].group()=='else':i=stmt(i+1)
            return i
        if token=='for':return stmt(par(i+1))
        if token in ('case','casex','casez','while','fork'):
            raise ValueError(f'unsupported procedural statement {token}')
        while ts[i].group()!=';':i+=1
        return i+1
    return ts[stmt(0)-1].end()

def partition(text, module, reset='rst', clock='ck'):
    text=P.strip_comments(text)
    start=re.search(r'\bmodule\s+'+re.escape(module)+r'\b',text).start()
    end=text.index('endmodule',start)+len('endmodule')
    prefix,suffix=text[:start],text[end:]
    text=text[start:end]
    mods=P.parse_modules(text,'reset_partition input')
    m=next(m for m in mods if m.name==module)
    widths={n:m.width(n,m.env()) for n in m.ports}
    for match in re.finditer(r'\breg\s*(\[[^\]]+\])?\s*([^;]+);',m.body):
        rng=match.group(1)
        if rng:
            hi,lo=rng[1:-1].split(':')
            hv,lv=P.ev(hi,m.env()),P.ev(lo,m.env())
            if hv is None or lv is None:raise ValueError(f'unknown register dimension {rng}')
            width=abs(hv-lv)+1
        else:width=1
        for decl in match.group(2).split(','):
            name=decl.strip().split('=')[0].strip()
            if re.fullmatch(r'\w+',name):widths[name]=width
    pat=re.compile(r'\balways\s*@\s*\([^)]*\bnegedge\s+'+re.escape(reset)+r'\s*\)')
    changes=[];leaves=[]
    for a in pat.finditer(text):
        end=statement_end(text,a.end());block=text[a.start():end]
        assignments=list(NBA.finditer(block))
        targets=sorted({x.group(1) for x in assignments})
        if any(x.group(2) for x in assignments):
            raise ValueError('indexed procedural assignment requires explicit partition')
        clones=[]
        for name in targets:
            if name not in widths:raise ValueError(f'unknown state width {name}')
            width=widths[name]
            for lo in range(0,width,32):
                bits=min(32,width-lo);leaf=len(leaves)
                leaves.append(dict(target=name,lsb=lo,bits=bits))
                def keep(x):
                    if x.group(1)!=name:return ';'
                    rhs=x.group(3)
                    if width==1:return f'{name} <= {rhs};'
                    return f"{name}[{lo} +: {bits}] <= {bits}'(({rhs}) >> {lo});"
                b=NBA.sub(keep,block)
                b=re.sub(r'\b'+reset+r'\b',f'sr_reset[{leaf}]',b)
                clones.append(b)
        changes.append((a.start(),end,'\n'.join(clones)))
    # Each child receives its own reset branch; flattening cannot reconnect
    # independent children onto a single reset leaf.
    loops=[]
    for loop in re.finditer(r'\bfor\s*\(\s*(?:genvar\s+)?(\w+)\s*=\s*0\s*;\s*\1\s*<\s*([^;]+);[^)]*\)\s*begin\b',text):
        count=P.ev(loop.group(2),m.env())
        if count is None:raise ValueError('unknown child generate count: '+loop.group(2))
        stop=statement_end(text,loop.start())
        loops.append((loop.start(),stop,loop.group(1),int(count)))
    for a in re.finditer(r'\.(rst_n|rst)\('+reset+r'\)',text):
        scope=[x for x in loops if x[0]<a.start()<x[1]]
        if len(scope)>1:raise ValueError('nested child generate reset needs explicit partition')
        var,count=(scope[0][2],scope[0][3]) if scope else (None,1)
        leaf=len(leaves)
        for index in range(count):leaves.append(dict(target='child',bits=None,lsb=None,index=index))
        expr=f'{leaf}+{var}' if var else str(leaf)
        changes.append((a.start(),a.end(),f'.{a.group(1)}(sr_reset[{expr}])'))
    if not leaves:raise ValueError(f'no reset consumers {module}.{reset}')
    if len(leaves)>1024:raise ValueError('reset tree needs another level')
    header=f'\nwire [{len(leaves)-1}:0] sr_reset;\nqfd_dv_reset_tree #(.N({len(leaves)})) u_safe_reset (.ck({clock}),.rst_n({reset}),.q(sr_reset));\n'
    changes.append((text.index('endmodule'),text.index('endmodule'),header))
    for start,end,new in sorted(changes,reverse=True):text=text[:start]+new+text[end:]
    return prefix+text+suffix,dict(module=module,reset=reset,leaf_count=len(leaves),max_data_reset_loads=32,reset_release_added_edges=2,child_reset_loads='requires synthesis census; not bounded by data assignment partition',leaves=leaves)

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('source',type=Path);a.add_argument('--module',required=True)
    a.add_argument('--out',type=Path,required=True);a.add_argument('--record',type=Path,required=True);args=a.parse_args()
    source=args.source.read_text()
    if args.module=='qfd_dv_redstn2':source=P.preprocess(P.strip_comments(source),{'OT_QFD_DV_SAFE_STORAGE':''})
    text,record=partition(source,args.module,reset='rst_n' if args.module in ('qfd_dv_redstn2','qfd_dv_stream') else 'rst')
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text('// GENERATED by tools/qwen_dv/reset_partition.py\n'+text)
    args.record.parent.mkdir(parents=True,exist_ok=True);args.record.write_text(json.dumps(record,indent=2)+'\n')
    print(f"RESET_PARTITION {args.module} leaves={record['leaf_count']} maxbits=32 reset+2edges")
if __name__=='__main__':main()
