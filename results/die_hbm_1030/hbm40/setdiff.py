import json,os,sys
def L(p):
    p=p+"/g0_report.json" if os.path.isdir(p) else p
    return {json.dumps(f,sort_keys=True) for f in json.load(open(p))["findings"]}
B0="/srv/opentallas-scratch2/claude/die-hbm-39/g0/d38s"
for P in sys.argv[1:]:
    for k in ("g0","g0c"):
        A=L(f"{B0}/{k}_report.json"); B=L(f"{P}/{k}_report.json")
        print(P,k,"total",len(B),"new",len(B-A),"gone",len(A-B))
        for s in sorted(B-A): print("  NEW",s[:400])
        for s in sorted(A-B): print("  GONE",s[:400])
