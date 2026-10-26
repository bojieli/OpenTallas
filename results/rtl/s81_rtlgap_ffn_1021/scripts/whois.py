import json,re,sys,collections
# whois.py <outdir> [n]: census violations -> driver inputs + a few load cells' output nets (names copies / regs)
d=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 40
r=json.load(open(d+'/native_census.json')); txt=open(d+'/mapped.v').read()
cells={}; users=collections.defaultdict(list)
for m in re.finditer(r'\n\s*(\w+)\s+(\\?\S+)\s*\((.*?)\);',txt,re.S):
    pins=[(p,x.strip()) for p,x in re.findall(r'\.(\w+)\(([^()]*)\)',m.group(3))]
    cells[m.group(2)]=(m.group(1),pins)
    for p,x in pins:
        if p not in ('Q','QN','Y','CON','SN'): users[x].append(m.group(2))
def onet(c): return [x for p,x in cells[c][1] if p in ('Q','QN','Y','CON','SN')]
for v in sorted(r['violations'],key=lambda x:-x['loads'])[:n]:
    c=v['driver'].split('/')[0]
    if c not in cells: print(v['loads'],v['driver']); continue
    t,pins=cells[c]; net=[x for p,x in pins if p==v['driver'].split('/')[1]][0]
    us=users[net]; samp=[]
    for u in us[:200]:
        o=onet(u)
        if o and not o[0].startswith('_'): samp.append(o[0])
    print(v['loads'],t,[x for p,x in pins if p not in ('Q','QN','Y')][:5],'->',sorted(set(samp))[:6])
