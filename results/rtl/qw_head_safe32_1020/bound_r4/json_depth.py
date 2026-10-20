import json,sys,collections
d=json.load(open(sys.argv[1])); m=d['modules'][sys.argv[2]]
cells=m['cells']; names=collections.defaultdict(list)
for n,v in m['netnames'].items():
    for i,b in enumerate(v['bits']):
        if isinstance(b,int): names[b].append((n,i,v.get('attributes',{}).get('src','')))
drv={}
for cn,c in cells.items():
    t=c['type']; dirs=c.get('port_directions',{})
    for p,bits in c['connections'].items():
        if dirs.get(p)=='output' or (p in('Y','Q') and p not in dirs):
            for b in bits:
                if isinstance(b,int): drv[b]=cn
def isff(t): return 'DFF' in t or t.startswith('ot_sram')
memo={}
sys.setrecursionlimit(100000)
def dep(b):
    if not isinstance(b,int): return 0
    if b in memo: return memo[b]
    st=[b]
    while st:
        x=st[-1]
        if x in memo: st.pop(); continue
        cn=drv.get(x)
        if cn is None or isff(cells[cn]['type']): memo[x]=0; st.pop(); continue
        c=cells[cn]; ins=[bb for p,bits in c['connections'].items() if c.get('port_directions',{}).get(p,'input' if p not in('Y',) else 'output')=='input' for bb in bits if isinstance(bb,int)]
        pend=[i for i in ins if i not in memo]
        if pend: st.extend(pend); continue
        memo[x]=1+max([memo[i] for i in ins] or [0]); st.pop()
    return memo[b]
res=[]
for cn,c in cells.items():
    if 'DFF' in c['type']:
        D=c['connections'].get('D',[None])[0]; Q=c['connections'].get('Q',[None])[0]
        res.append((dep(D),cn,names.get(Q,[('?',0,'')])[:2]))
res.sort(key=lambda r:-r[0])
groups=collections.OrderedDict()
for dd,cn,nm in res:
    if dd<=20: break
    key=(nm[0][0] if nm else '?')
    groups.setdefault(key,[dd,0,nm[0][2] if nm else ''])
    groups[key][1]+=1
for k,(dd,n,src) in list(groups.items())[:40]: print(dd,n,k,src[:160])
