import json,re,collections,sys
p=json.load(open('in/plan_qc99_s28.json'))
lat=p['latency']['lanes']
C=json.load(open('lane_chains.json'))
rect={}
for line in open('parts.tsv'):
    n,t,o,x0,y0,x1,y1=line.rstrip('\n').split('\t'); rect[n]=(float(y0),float(y1))
MID=(11482.56,12821.76); HC=(14160.96,15500.16)
def row(n):
    y0,y1=rect[n]
    if y1<=MID[0]+1: return 'below'
    if y0>=MID[1]-1: return 'above'
    return 'mid'
groups={}
for g in p['latency_groups']:
    for l in g.get('lanes',[]): groups[l]=g['name']
res=collections.Counter(); bits=collections.Counter(); ex=collections.defaultdict(list)
hcl=collections.Counter()
for lid,ch,w in C:
    rows=[row(n) for n in ch]
    # count vertical mid crossings: transitions below<->above passing mid
    seq=[r for i,r in enumerate(rows) if i==0 or r!=rows[i-1]]
    cross=sum(1 for i in range(len(seq)-2) if seq[i]!=seq[i+2] and seq[i+1]=='mid' and 'mid' not in (seq[i],seq[i+2]))
    # also direct below->above impossible (not adjacent)
    if not cross: continue
    L=lat.get(lid,{})
    pad=L.get('pad',0); cyc=L.get('cycles')
    k='absorbed(pad>=1)' if pad>=1 else 'no_pad'
    res[k]+=1; bits[k]+=w
    if re.search(r'_E0_',lid): ex[k].append((lid,w,cyc,pad,L.get('stations'),groups.get(lid,'')))
print(res,bits)
for k,v in ex.items():
    print('==',k)
    for e in sorted(v,key=lambda e:-e[1])[:40]: print('  ',e)
