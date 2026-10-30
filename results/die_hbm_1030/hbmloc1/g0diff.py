import json,os,sys,re,collections
def L(p,lv=("ERROR",)):
    p=p+"/g0_report.json" if os.path.isdir(p) else p
    return [f for f in json.load(open(p))["findings"] if f.get("level") in lv]
base,new=sys.argv[1],sys.argv[2]
for k in ("g0","g0c"):
    A={json.dumps(f,sort_keys=True) for f in L(f"{base}/{k}_report.json")}
    B={json.dumps(f,sort_keys=True) for f in L(f"{new}/{k}_report.json")}
    print(k,"base",len(A),"new-total",len(B),"NEW",len(B-A),"GONE",len(A-B))
    c=collections.Counter(json.loads(s)["check"] for s in B-A); print(" new by check",dict(c))
    for s in sorted(B-A)[:int(sys.argv[3]) if len(sys.argv)>3 else 40]: print("  NEW",json.loads(s)["check"],json.loads(s)["msg"][:260])
