import re,sys,json,collections
nl,cen=sys.argv[1],sys.argv[2]; pats=sys.argv[3:]
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
c=json.load(open(cen))
done=set()
for v in sorted(c['violations'],key=lambda v:-v['loads']):
    d=re.sub(r'\[\d+\]','[*]',v['driver'])
    if not any(re.search(p,v['driver']) for p in pats): continue
    if d in done: continue
    done.add(d)
    ld=collections.Counter()
    for j,pin in loads[v['net']]:
        n=cells[j][1]
        if re.match(r'_\d+_$',n): ld[cells[j][0].split('_ASAP7')[0]+'.'+pin]+=1
        else: ld[re.sub(r'\[\d+\]','[*]',n.rsplit('.',1)[0].replace('u_ot_pr_core.',''))+'.'+pin]+=1
    print(v['loads'],d,ld.most_common(8))
