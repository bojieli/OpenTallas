import json,sys,re,collections
p=json.load(open(sys.argv[1]))
T=p['partition_types']
rows=[]
for q in p['partitions']:
    t=T[q['type']]; w,h=t['outline_um']
    if q.get('orient','R0') in ('R90','R270','MXR90','MYR90'): w,h=h,w
    x,y=q['origin_um']
    rows.append((q['name'],q['type'],q.get('orient','R0'),x,y,x+w,y+h))
rows.sort(key=lambda r:(r[4],r[3]))
with open('parts.tsv','w') as f:
    for r in rows: f.write('\t'.join(map(str,r))+'\n')
names=[r[0] for r in rows]
pat=collections.Counter(re.sub(r'[EW]\d','?',re.sub(r'_\d\d$','_nn',n)) for n in names)
for k,v in sorted(pat.items()): print(v,k)
