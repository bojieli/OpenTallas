import json,sys
d=json.load(open(sys.argv[1]));plan=json.load(open(sys.argv[2]));cf=sys.argv[3]
cut=set(open(cf).read().split())
a=d["hb4"]["seam"]["all"]
bad={tuple(x["where"].split("->")) for x in a.get("setup_neg_after",[])}
for x in a.get("hold_neg_after",[]) or []: bad.add(tuple(x["where"].split("->")))
new=[p["id"] for p in plan["ports"] if (p["src"]["part"],p["dst"]["part"]) in bad and p["id"] not in cut]
open(cf,"a").write("".join(i+"\n" for i in new));print(len(new))
