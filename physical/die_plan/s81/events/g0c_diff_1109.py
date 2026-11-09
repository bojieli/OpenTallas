import json,collections,re,sys
def L(f):
    r=json.load(open(f"chk_{f}/g0_report.json"))
    return collections.Counter((x["level"],x["check"],x["msg"]) for x in r["findings"])
b=L("base")
for f in sys.argv[1:]:
    n=L(f); new=n-b; gone=b-n
    print("########",f,"NEW",sum(new.values()),"GONE",sum(gone.values()))
    for tag,c in (("NEW",new),("GONE",gone)):
        k=collections.Counter()
        for (lv,ck,m),v in c.items():
            svc = "svc_" in m
            mm=re.sub(r"svc_(hi|lo)_dsdv_svc_rs(_w)?__t\d","svc_\\1_T",m)
            k[(lv,ck,svc,re.sub(r"[-\d.]+","#",mm)[:120])]+=v
        for key,v in k.most_common(40 if tag=="NEW" else 12): print(tag,v,key)
