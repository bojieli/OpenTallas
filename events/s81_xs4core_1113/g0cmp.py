import json,sys,collections,re
def load(d):
    r=json.load(open(d+"/g0_report.json"))
    fs=r.get("findings") or r.get("issues") or r.get("items") or []
    if not fs:
        for k,v in r.items():
            if isinstance(v,list) and v and isinstance(v[0],dict) and ("check" in v[0] or "severity" in v[0]): fs=v;break
    return r,fs
r0,f0=load(sys.argv[1]); r1,f1=load(sys.argv[2])
sev=lambda i:(i.get("severity") or i.get("level") or i.get("sev") or "").upper()
key=lambda i:(i.get("check"),sev(i),i.get("msg") or i.get("message") or json.dumps(i,sort_keys=True))
print("keys",list(r1.keys())[:12], "sample",json.dumps(f1[0])[:300] if f1 else None)
for lab,S in (("ERROR","ERROR"),("WARN","WARN")):
    a=collections.Counter(key(i) for i in f0 if sev(i).startswith(S)); b=collections.Counter(key(i) for i in f1 if sev(i).startswith(S))
    new=b-a; gone=a-b
    print(lab,"base",sum(a.values()),"new plan",sum(b.values()),"added",sum(new.values()),"removed",sum(gone.values()))
    c=collections.Counter(k[0] for k in new.elements()); print("  added by check",c.most_common(30))
    c=collections.Counter(k[0] for k in gone.elements()); print("  removed by check",c.most_common(30))
    if lab=="ERROR":
        for k in list(new)[:40]: print("   +",k[0],str(k[2])[:330])
