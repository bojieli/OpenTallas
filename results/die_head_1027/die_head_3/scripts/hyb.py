import json,sys
from collections import Counter
d=json.load(open(sys.argv[1]));plan=json.load(open(sys.argv[2]));mp=json.load(open(sys.argv[3]))["part_region"]
neg=d["hb4"]["seam"]["all"]["setup_neg_after"]
pairs={(x["where"].split("->")[0],x["where"].split("->")[1]) for x in neg}
print("pairs setup<0 after HB4:",len(pairs))
ports=[p for p in plan["ports"] if (p["src"]["part"],p["dst"]["part"]) in pairs]
inreg=[p for p in plan["ports"] if mp[p["src"]["part"]]==mp[p["dst"]["part"]]]
rev=[p for p in inreg if (p["dst"]["part"],p["src"]["part"]) in pairs]
print("ports to cross (with-clock):",len(ports),"bits",sum(p.get("width",1) for p in ports),"; in-region ports",len(inreg),"bits",sum(p.get("width",1) for p in inreg))
print("reverse (counter-clock) ports of the same pairs staying in-region:",len(rev))
print(Counter(p["id"].rsplit("__",1)[0].rstrip("0123456789") for p in ports).most_common(12))
