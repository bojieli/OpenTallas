import json,re,collections,sys
d=json.load(open(sys.argv[1]))
r=d["remaining"]
def g(n):
    n=re.sub(r'\\?\[\d+\\?\]','[]',n); n=re.sub(r'\$_\w+$','',n)
    return '.'.join(n.split('.')[:5])
c=collections.Counter(); mx=collections.defaultdict(float)
for e in r:
    k=(g(e["source"]),g(e["capture"]),e["source_fixed"],e["capture_fixed"]); c[k]+=1; mx[k]=max(mx[k],e["distance"])
for k,v in c.most_common(20): print(v, round(mx[k],1), k)
