import json,os,sys
def L(p):
    if os.path.isdir(p): p=p+"/g0_report.json"
    return {json.dumps(f,sort_keys=True) for f in json.load(open(p))["findings"]}
for P in sys.argv[1:]:
    for k in ("g0","g0c"):
        A=L(f"/srv/opentallas-scratch2/claude/die-hbm-38/g0/d35c/{k}_report.json"); B=L(f"{P}/{k}_report.json")
        print(P,k,"new",len(B-A),"gone",len(A-B))
        for s in sorted(B-A): print("  NEW",s[:300])
        for s in sorted(A-B): print("  GONE",s[:300])
