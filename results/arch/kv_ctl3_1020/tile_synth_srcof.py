import sys,re,collections
txt=open(sys.argv[1]).read()
# cells with attributes
blocks=re.findall(r'((?:\s*\(\*[^*]*\*\)\s*)*)\n\s*(\S+)\s+(\S+)\s*\((.*?)\);',txt,re.S)
OUT={'Y','QN','Q','CON','SN'}
cin={};loads=collections.defaultdict(list);src={}
for attrs,typ,name,body in blocks:
    if typ in('module','input','output','wire','assign','reg'):continue
    pins=re.findall(r'\.(\w+)\(\s*([^()]*?)\s*\)',body)
    if not pins: continue
    cin[name]=(typ,pins)
    m=re.search(r'src = "([^"]*)"',attrs); src[name]=m.group(1) if m else ''
    for p,n in pins:
        if p not in OUT: loads[n].append((name,typ,p))
def outs(n): return [nn for pp,nn in cin[n][1] if pp in OUT]
for t in sys.argv[2:]:
    o=outs(t)[0]; res=collections.Counter(); f=[o]; seen={o}
    for d in range(5):
        nx=[]
        for x in f:
            for n,ty,p in loads[x]:
                if 'DFF' in ty: res[re.sub(r'.*/','',src[n].split('|')[-1])]+=1
                else:
                    for nn in outs(n):
                        if nn not in seen: seen.add(nn);nx.append(nn)
        f=nx
    print(t, res.most_common(4))
