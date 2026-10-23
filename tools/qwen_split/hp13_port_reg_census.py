#!/usr/bin/env python3
"""Per top-port bit: registered (flop D/Q within <=4 buf/inv), macro-direct, or unregistered. Netlist = yosys flat-ish .v"""
import re,sys,collections,json
src=open(sys.argv[1]).read(); top=sys.argv[2]
m=re.search(r'\nmodule '+re.escape(top)+r'\((.*?)\);(.*?)\nendmodule',src,re.S); body=m.group(2)
ports={}
for d,w,names in re.findall(r'^\s*(input|output)\s+(\[\d+:\d+\])?\s*([^;]+);',body,re.M):
    hi,lo=(map(int,w[1:-1].split(':')) if w else (0,0))
    for n in names.split(','):
        n=n.strip()
        ports[n]=(d,hi,lo)
# assigns
alias=collections.defaultdict(set)
def bits(expr):
    expr=expr.strip()
    if expr.startswith('{'):
        out=[]
        for p in re.split(r',(?![^\[]*\])',expr[1:-1]): out+=bits(p)
        return out
    mm=re.match(r'^(\\\S+|[\w$.]+)\s*\[(\d+):(\d+)\]$',expr)
    if mm:
        n,h,l=mm.group(1),int(mm.group(2)),int(mm.group(3)); return [f'{n}[{i}]' for i in range(h,l-1,-1)]
    mm=re.match(r'^(\\\S+|[\w$.]+)\s*\[(\d+)\]$',expr)
    if mm: return [f'{mm.group(1)}[{mm.group(2)}]']
    if re.match(r"^\d+'",expr): return ['CONST']*int(expr.split("'")[0])
    n=expr
    if n in ports:
        d,h,l=ports[n]; return [f'{n}[{i}]' for i in range(h,l-1,-1)]
    return [n]
for a,b in re.findall(r'^\s*assign\s+(.+?)\s*=\s*(.+?);',body,re.M):
    for x,y in zip(bits(a),bits(b)): alias[x].add(y); alias[y].add(x)
loads=collections.defaultdict(list); drv={}
inst_re=re.compile(r'^\s*(\\\S+|[\w$]+)\s+(\\\S+|[\w$.\[\]]+)\s*\((.*?)\);',re.M|re.S)
OUTP={'Y','Q','QN','X','H','L','CON','SN','rd_out'}
types={}
for t,i,conns in inst_re.findall(body):
    if t in('input','output','wire','assign','reg'):continue
    types[i]=t
    for pin,expr in re.findall(r'\.(\w+)\s*\(([^()]*)\)',conns):
        for b in bits(expr):
            if pin in OUTP: drv[b]=(i,pin)
            else: loads[b].append((i,pin))
def isseq(t): return bool(re.search(r'DFF|DHL|DLL|SDF|ASYNC|ICG|dff_p',t))
def isbuf(t): return bool(re.match(r'(BUF|INV|HB|CKINV|CKBUF)',t)) or '_not' in t
def ismac(t): return t.startswith('ot_rom') or t.startswith('ot_sram')
def cls_in(b):
    front={b}|alias[b]; seen=set(front); kinds=set()
    for d in range(6):
        nf=set()
        for n in front:
            for i,p in loads[n]:
                t=types[i]
                if isseq(t): kinds.add('R' if p in ('D',) else 'X')
                elif ismac(t): kinds.add('M')
                elif isbuf(t): nf|=outs[i]
                else: kinds.add('N')
        front=set(x for x in nf if x not in seen); seen|=front
        if not front: break
    if kinds<= {'R'} and kinds: return 'R'
    if kinds=={'M'}: return 'M'
    return 'N' if 'N' in kinds else ''.join(sorted(kinds)) or 'U'
outs=collections.defaultdict(set)
for b,(i,p) in drv.items(): outs[i].add(b)
def cls_out(b):
    n=b
    for d in range(5):
        cand=[n]+list(alias[n])
        dd=[drv[c] for c in cand if c in drv]
        if not dd:
            if any(c=='CONST' or c.startswith("1'") for c in cand): return 'C'
            return 'N?'
        i,p=dd[0]; t=types[i]
        if isseq(t): return 'R'
        if ismac(t): return 'M'
        if isbuf(t):
            ins=[b2 for b2,l in loads.items() if any(x[0]==i for x in l)]
            if not ins: return 'N'
            n=ins[0]; continue
        if t.startswith('TIE'): return 'C'
        return 'N'
    return 'N'
res=collections.defaultdict(collections.Counter)
for n,(d,h,l) in ports.items():
    for k in range(l,h+1):
        b=f'{n}[{k}]'
        c=cls_in(b) if d=='input' else cls_out(b)
        res[n][c]+=1
json.dump({n:{'dir':ports[n][0],'w':ports[n][1]-ports[n][2]+1,**res[n]} for n in ports},open(sys.argv[3],'w'),indent=0)
tot=collections.Counter()
for n in ports:
    for c,v in res[n].items(): tot[c]+=v
print(tot)
for n in ports:
    if any(c not in('R',) for c in res[n]): print(ports[n][0],n,ports[n][1]-ports[n][2]+1,dict(res[n]))
