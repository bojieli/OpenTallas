import json,sys,collections,re
r=json.load(open(sys.argv[1]))
c=collections.Counter(); ex={}
for f in r["findings"]:
    if f["level"]!="ERROR": continue
    k=f["check"]; c[k]+=1; ex.setdefault(k,f["msg"][:260])
for k,v in c.most_common(): print(v,k,"|",ex[k])
