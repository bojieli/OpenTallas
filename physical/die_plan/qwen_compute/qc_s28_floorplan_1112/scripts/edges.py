import json,sys,re,collections
p=json.load(open(sys.argv[1]))
T=p['partition_types']
rect={}
for line in open('parts.tsv'):
    n,t,o,x0,y0,x1,y1=line.rstrip('\n').split('\t'); rect[n]=(t,float(x0),float(y0),float(x1),float(y1))
def fam(n):
    m=re.match(r'sl_([EW]\d)_(.+)$',n)
    if m: return m.group(1),m.group(2)
    m=re.match(r'c_([EW]\d)_(\w\w_\d\d)$',n)
    if m: return m.group(1),m.group(2)
    return '-',n
lat=p['latency']['lanes']
ports={q['id']:q for q in p['lanes'] if 'src' in q}
agg=collections.defaultdict(lambda:[0,0,[],0.0,collections.Counter()])
nl=0
pl={}
for L in p['lanes']:
    for q in L['ports']: pl[q]=L['id']
for L in p['ports']:
    if 'src' not in L: continue
    nl+=1
    s,d=L['src']['part'],L['dst']['part']; w=L.get('width',0)
    (ss,fs),(sd,fd)=fam(s),fam(d)
    rel='same' if ss==sd else ('x' if '-' in (ss,sd) else 'xslice')
    lid=pl.get(L['id'],L['id'])
    cyc=lat.get(lid,{}).get('cycles')
    a=rect[s];b=rect[d]
    dist=abs((a[1]+a[3])/2-(b[1]+b[3])/2)+abs((a[2]+a[4])/2-(b[2]+b[4])/2)
    key=(fs,fd,rel)
    g=agg[key]; g[0]+=w; g[1]+=1; g[2].append(cyc); g[3]+=w*dist/1000; g[4][L.get('kind')]+=1
print('lanes',nl, 'lat keys',len(lat))
rows=sorted(agg.items(),key=lambda kv:-kv[1][0])
with open('fam_edges.tsv','w') as f:
    f.write('src\tdst\trel\tbits_total\tlanes\tbits_per_slice\tcyc_min\tcyc_max\tbit_mm\tkinds\n')
    for (a,b,r),(bits,n,cyc,bm,k) in rows:
        cy=[c for c in cyc if c is not None]
        ns=12 if r!='x' or a.startswith(('tf','tn','bf','bn')) or b.startswith(('tf','tn','bf','bn')) else 1
        f.write(f"{a}\t{b}\t{r}\t{bits}\t{n}\t{bits/12 if r!='x' else bits}\t{min(cy) if cy else ''}\t{max(cy) if cy else ''}\t{bm:.0f}\t{dict(k)}\n")
print(open('fam_edges.tsv').read()[:9000])
