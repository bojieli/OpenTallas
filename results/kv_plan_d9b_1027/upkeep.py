import json
r=json.load(open("g0c_q9b/g0_report.json")); L=json.load(open("ledger_d9b.json"))
lanes={f["lane"] for f in r["findings"] if f.get("level")=="ERROR" and f.get("lane")}
moved={w["port"] for w in L["windows"]}
keep=sorted(set(open("keep.txt").read().split())|{p for p in moved if p.rsplit("_",1)[0] in lanes})
open("keep.txt","w").write(" ".join(keep)); print("lanes",sorted(lanes),"keep",len(keep))
