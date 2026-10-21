import re,sys,json,collections
nl,cen=sys.argv[1],sys.argv[2]; N=int(sys.argv[3])
txt=open(nl).read()
cells=[]
for m in re.finditer(r'\n\s*([A-Za-z_][\w$]*)\s+(\\\S+|[\w$\[\].]+)\s*\((.*?)\);',txt,re.S):
    t,n,body=m.groups()
    if t in('module','input','output','wire','assign','reg'):continue
    pins=dict((p,v.strip()) for p,v in re.findall(r'\.(\w+)\(([^()]*)\)',body))
    cells.append((t,n.lstrip('\\').strip(),pins))
OUT={'Y','QN','Q','CON','SN','rd_out'}
drv={};loads=collections.defaultdict(list)
for i,(t,n,p) in enumerate(cells):
    for pin,net in p.items():
        if pin in OUT: drv[net]=i
        else: loads[net].append((i,pin))
def named(i): return not re.match(r'_\d+_$',cells[i][1])
def fanin(net,d):
    i=drv.get(net)
    if i is None: return {net}
    if named(i) or d==0: return {re.sub(r'\[\d+\]','[*]',cells[i][1].replace('u_ot_pr_core.',''))}
    s=set()
    for pin,nn in cells[i][2].items():
        if pin not in OUT: s|=fanin(nn,d-1)
    return s
def fanout(net,d):
    c=collections.Counter()
    for j,pin in loads[net]:
        if named(j): c[re.sub(r'\[\d+\]','[*]',cells[j][1].replace('u_ot_pr_core.',''))+'.'+pin]+=1
        elif d>0:
            for pn,nn in cells[j][2].items():
                if pn in OUT: c.update(fanout(nn,d-1))
        else: c['comb']+=1
    return c
c=json.load(open(cen))
seen=collections.Counter()
for v in sorted(c['violations'],key=lambda v:-v['loads']):
    if not v['driver'].startswith('_'): continue
    fi=tuple(sorted(fanin(v['net'],6)))[:5]
    if seen[fi]>=1: seen[fi]+=1; continue
    seen[fi]+=1
    fo=fanout(v['net'],4).most_common(4)
    print(v['loads'],fi,fo)
    N-=1
    if N==0: break
print('GROUPS');
for k,n in seen.most_common(40): print(n,k)
