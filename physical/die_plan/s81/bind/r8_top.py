import json,collections,re,sys
d=json.load(open(sys.argv[1]))
c=collections.Counter(); n=collections.Counter(); P=collections.Counter()
for m in d['members']:
    pad=m['pad']
    if not pad: continue
    b=sum(h-l+1 for l,h in m['sink_bits'])
    k=(re.sub(r'\d+','#',m['sink']), m['sink_port'], re.sub(r'\d+','#',m['source']))
    c[k]+=pad*b; n[k]+=1; P[k]=max(P[k],pad)
print('tot',sum(c.values()))
for k,v in c.most_common(int(sys.argv[2]) if len(sys.argv)>2 else 25): print(v,n[k],'maxpad',P[k],k)
