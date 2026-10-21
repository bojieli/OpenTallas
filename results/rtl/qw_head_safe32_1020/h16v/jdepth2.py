# per-register logic depth (generic gates) with the startpoint of the deepest cone; grouped by RTL register name
import json,sys,collections,re
d=json.load(open(sys.argv[1])); m=d['modules'][sys.argv[2]]; TH=int(sys.argv[3]) if len(sys.argv)>3 else 20
cells=m['cells']; names={}
for n,v in m['netnames'].items():
    for i,b in enumerate(v['bits']):
        if isinstance(b,int) and (b not in names or (names[b].startswith('$') and not n.startswith('$')) or (not n.startswith('$') and len(n)>len(names[b]) and not names[b].startswith('$') and False)): names[b]=n
drv={}
for cn,c in cells.items():
    dirs=c.get('port_directions',{})
    for p,bits in c['connections'].items():
        if dirs.get(p)=='output' or (p in('Y','Q') and p not in dirs):
            for b in bits:
                if isinstance(b,int): drv[b]=cn
def isff(t): return 'DFF' in t or t.startswith('ot_sram') or 'dff' in t
memo={}
def ins_of(c): 
    dirs=c.get('port_directions',{})
    return [bb for p,bits in c['connections'].items() if dirs.get(p,'input' if p not in ('Y','Q') else 'output')=='input' for bb in bits if isinstance(bb,int)]
def dep(b):
    st=[b]
    while st:
        x=st[-1]
        if x in memo: st.pop(); continue
        cn=drv.get(x)
        if cn is None or isff(cells[cn]['type']): memo[x]=(0,x); st.pop(); continue
        ins=ins_of(cells[cn]); pend=[i for i in ins if i not in memo]
        if pend: st.extend(pend); continue
        best=max([memo[i] for i in ins] or [(0,x)],key=lambda t:t[0]); memo[x]=(best[0]+1,best[1]); st.pop()
    return memo[b]
def nm(b): return re.sub(r'\[\d+\]','[]',names.get(b,'?'))
g=collections.OrderedDict(); res=[]
for cn,c in cells.items():
    if 'DFF' in c['type']:
        D=c['connections'].get('D',[None])[0]; Q=c['connections'].get('Q',[None])[0]
        if not isinstance(D,int): continue
        dd,s=dep(D); res.append((dd,nm(Q),nm(s)))
res.sort(key=lambda r:-r[0])
for dd,e,s in res:
    if dd<TH: break
    k=(e,s)
    if k not in g: g[k]=[dd,0]
    g[k][1]+=1
for (e,s),(dd,n) in list(g.items())[:int(sys.argv[4]) if len(sys.argv)>4 else 60]: print(f'{dd:3d} {n:4d} {e}  <-  {s}')
if len(sys.argv)>5:
    for pat in sys.argv[5].split(','):
        for cn,c in cells.items():
            if 'DFF' not in c['type']: continue
            Q=c['connections'].get('Q',[None])[0]
            if nm(Q)!=pat: continue
            D=c['connections']['D'][0]; dd,_=dep(D)
            if dd<TH: continue
            print('== PATH',pat,dd); x=D; seen=0
            while True:
                cn2=drv.get(x)
                if cn2 is None or isff(cells[cn2]['type']): print('   start',names.get(x,'?')); break
                ins=ins_of(cells[cn2]); bi=max(ins,key=lambda i:memo[i][0])
                print('  ',memo[x][0],cells[cn2]['type'],names.get(x,'?')[:90])
                x=bi
            break
