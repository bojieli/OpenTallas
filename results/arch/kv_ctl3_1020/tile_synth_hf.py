import re,sys,collections
txt=open(sys.argv[1]).read()
m=re.search(r'module\s+\S+\s*\((.*?)\);',txt,re.S)
cells=re.findall(r'\n\s*(\S+)\s+(\S+)\s*\((.*?)\);',txt,re.S)
drv={};loads=collections.defaultdict(list);cin={}
OUT={'Y','QN','Q','CON','SN'}
for typ,name,body in cells:
    if typ in('module','input','output','wire','assign','reg'):continue
    pins=re.findall(r'\.(\w+)\(\s*([^()]*?)\s*\)',body)
    if not pins: continue
    cin[name]=(typ,pins)
    for pin,net in pins:
        if pin in OUT: drv[net]=(name,typ,pin)
        else: loads[net].append((name,typ,pin))
# assigns alias
for a,b in re.findall(r'assign\s+(\S+)\s*=\s*(\S+)\s*;',txt):
    pass
def isbuf(t): return t.startswith(('BUF','INV','HB'))
def sinks(net):
    out=[];st=[net];seen=set()
    while st:
        x=st.pop()
        for n,t,p in loads[x]:
            if isbuf(t):
                for pp,nn in cin[n][1]:
                    if pp=='Y' and nn not in seen: seen.add(nn);st.append(nn)
            else: out.append((n,t,p))
    return out
res=[]
nets=set(drv)|set(loads)
for net in nets:
    if net in drv and isbuf(drv[net][1]): continue
    s=[x for x in sinks(net) if x[2]!='CLK']
    rs=[x for x in s if x[2] in('RESETN','SETN')]
    d=[x for x in s if x[2] not in('RESETN','SETN')]
    if len(d)>32 or len(rs)>32: res.append((len(d),len(rs),net,drv.get(net,('PORT',))[0]))
res.sort(reverse=True)
for r in res[:25]: print(r)
print('flops',sum(1 for n,(t,p) in cin.items() if 'DFF' in t))
