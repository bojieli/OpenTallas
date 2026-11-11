import json,sys,re,collections
def E(f):
  r=json.load(open(f)); c=collections.Counter()
  for x in r["findings"]:
    if isinstance(x,dict) and str(x.get("level") or x.get("severity")).upper()=="ERROR":
      m=str(x.get("msg") or x.get("message") or ""); c[(x.get("check"), re.sub(r"\d+\.\d+","#",m)[:200])]+=1
  return c
b,q=E(sys.argv[1]),E(sys.argv[2])
new=q-b; gone=b-q
print("base",sum(b.values()),"new",sum(q.values()),"NEW",sum(new.values()),"GONE",sum(gone.values()))
for k,v in new.most_common(15): print(" NEW",v,k[0],k[1][:200])
for k,v in collections.Counter({(k[0],k[1][:70]):v for k,v in gone.items()}).most_common(8): print(" GONE",v,k)
