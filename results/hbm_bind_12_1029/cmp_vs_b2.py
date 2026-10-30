import json,re,sys
def load(d):
    r=json.load(open(d+"/out/bind_report.json"))
    u=sorted(e for e in r["errors"] if e.startswith("UNPLANNED"))
    bits=sum(int(re.search(r": (\d+) as-built crossing bits",e).group(1)) for e in u)
    other=[e for e in r["errors"] if not e.startswith("UNPLANNED")]
    t=json.load(open(d+"/out/bind_tied.json"))
    return r,u,bits,other,t
R="/srv/opentallas-scratch2/claude/"
a=load(R+"die-hbm-23/b2"); b=load(R+"hbm-bind-12-1029/"+sys.argv[1])
for n,x in (("b2",a),(sys.argv[1],b)):
    r,u,bits,other,t=x
    print(n,"n_errors",r["n_errors"],"UNPLANNED",len(u),"bits",bits,"unmapped",len(r["unmapped"]) if hasattr(r["unmapped"],"__len__") else r["unmapped"],
          "open_outputs",r["open_outputs"],"dissolved",r["dissolved"],"tied_by_port",len(r["tied_by_port"]),"warnings",len(r["warnings"]))
    print("  tied.json keys",list(t.keys())[:8] if isinstance(t,dict) else len(t))
    for e in other: print("  OTHER",e[:400])
print("UNPLANNED set equal:",a[1]==b[1])
print("tied.json equal:",a[4]==b[4])
ws=set(map(str,b[0]["warnings"]))-set(map(str,a[0]["warnings"])); print("new warnings",len(ws),list(ws)[:5])
for k in ("undriven","multiply_bound","multi","tied"):
    for x,n in ((a,"b2"),(b,"new")):
        if k in x[0]: print(n,k,x[0][k] if not hasattr(x[0][k],"__len__") else len(x[0][k]))
