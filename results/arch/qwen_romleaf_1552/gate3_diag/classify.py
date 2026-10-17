import csv,re,collections,statistics as st,sys
ins={}
for r in csv.DictReader(open('insts.tsv'),delimiter='\t'):
    if r['name']=='name':continue
    ins[r['name'].replace('\\','')]=r
rows=list(csv.reader(open('sinks.tsv'),delimiter='\t'))[1:]
def grp(n,depth=4):
    n=re.sub(r'^u_g\.u_tile\.u_tile\.u_logic\.','L.',n)
    n=re.sub(r'\$.*','',n)
    parts=n.split('.')
    g='.'.join(parts[:depth])
    return re.sub(r'\[\d+\]','[*]',g)
out=[]
for clk,src,pin,a,*_ in rows:
    inst=pin.rsplit('/',1)[0]
    r=ins.get(inst)
    out.append((clk,src,inst,float(r['x']),float(r['y']),float(a)))
import pickle;pickle.dump(out,open('sinks.pkl','wb'))
for src in ['ck','ck_rs','ck_rn']:
    by=collections.defaultdict(list)
    for clk,s,inst,x,y,a in out:
        if s==src: by[grp(inst,int(sys.argv[1]) if len(sys.argv)>1 else 5)].append((x,y,a))
    allv=[v for vs in by.values() for v in vs]
    print('==',src,len(allv))
    for g,v in sorted(by.items(),key=lambda kv:-len(kv[1]))[:40]:
        xs=[p[0] for p in v];ys=[p[1] for p in v];a=[p[2] for p in v]
        print(f'{len(v):6d} {g[:66]:66s} x{min(xs):4.0f}-{max(xs):4.0f} y{min(ys):5.0f}-{max(ys):5.0f} arr {min(a):5.0f}/{st.mean(a):5.0f}/{max(a):5.0f}')
