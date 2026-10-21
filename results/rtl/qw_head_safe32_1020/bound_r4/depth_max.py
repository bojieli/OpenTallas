import re,sys,collections
sys.setrecursionlimit(1000000)
txt=open(sys.argv[1]).read()
# find top module body = last module
mods=[m.start() for m in re.finditer(r'^module ',txt,re.M)]
cells={}
for m in re.finditer(r'^\s*(?:\(\*[^\n]*?\*\)\s*)*(\\\S+|[A-Za-z_][\w$]*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s+(\\\S+|[\w$.\[\]]+)\s*\((.*?)\);',txt,re.S|re.M):
    typ,inst,body=m.group(1),m.group(2),m.group(3)
    if typ in ('module','input','output','wire','assign','reg','inout'):continue
    pins=dict((p,n.strip()) for p,n in re.findall(r'\.(\w+)\(([^()]*)\)',body))
    t=re.sub(r'^\\\$paramod\\qhs_bmath_([a-z0-9_]+).*',r'\1',typ); t=re.sub(r'^qhs_bmath_','',t)
    cells[inst.strip()]=(t,pins)
cnt=collections.Counter(t for t,_ in cells.values())
print('cells',len(cells),cnt.most_common(14))
OUT=('Y','Q','X') 
def seq(t): return t.startswith('dff') or 'sram' in t or t.startswith('ot_')
drv={}
for inst,(t,pins) in cells.items():
    if seq(t):
        for p,n in pins.items():
            if p.startswith('Q') or p.startswith('rd') or p.startswith('dout') or p.startswith('Q'): drv[n]=(inst,'SEQ')
    else:
        for p,n in pins.items():
            if p=='Y': drv[n]=(inst,p)
memo={}
def depth(net):
    if net in memo: return memo[net]
    stack=[(net,0)]
    # iterative DFS
    order=[]; seen=set()
    st=[net]
    while st:
        n=st[-1]
        if n in memo: st.pop(); continue
        d=drv.get(n)
        if not d or d[1]=='SEQ': memo[n]=0; st.pop(); continue
        t,pins=cells[d[0]]
        ins=[v for k,v in pins.items() if k!='Y']
        pend=[v for v in ins if v not in memo]
        if pend and n not in seen:
            seen.add(n); st.extend(pend); continue
        memo[n]=1+max([memo.get(v,0) for v in ins] or [0]); st.pop()
    return memo[net]
worst=[]
for inst,(t,pins) in cells.items():
    if t.startswith('dff'):
        dn=pins.get('D')
        if dn: worst.append((depth(dn),inst))
worst.sort(reverse=True)
hist=collections.Counter(min(d//10*10,200) for d,_ in worst)
print('max_depth',worst[:5]); print('hist(levels//10)',sorted(hist.items()))
print('ffs_over_20',sum(1 for d,_ in worst if d>20),'over_30',sum(1 for d,_ in worst if d>30),'of',len(worst))
