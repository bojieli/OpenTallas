"""Audit mapped sequential clock roots against ordered fence regexes; no synthesis."""
import argparse,collections,json,pathlib,re
ap=argparse.ArgumentParser();ap.add_argument("netlist");ap.add_argument("regions");a=ap.parse_args()
s=pathlib.Path(a.netlist).read_text();t=pathlib.Path(a.regions).read_text()
rules=[]
for line in t.splitlines():
 m=re.search(r"name (\w+) type (\w+) regex \{(.*?)\} boxes",line)
 if m:rules.append((m[1],re.compile(m[3])))
c=collections.Counter();bad=[];total=collections.Counter()
for m in re.finditer(r"(\S+)\s+(\S+)\s*\((.*?)\);",s,re.S):
 if "DFF" not in m[1]:continue
 clk=re.search(r"\.CLK\(\s*(ck_dw|ck_de)\s*\)",m[3])
 if not clk:continue
 name=m[2].lstrip("\\");region=next((n for n,r in rules if r.search(name)),"UNCLAIMED")
 total[clk[1]]+=1;c[(clk[1],region)]+=1
 if region!={"ck_dw":"dw","ck_de":"de"}[clk[1]]:bad.append({"clock":clk[1],"region":region,"cell":name})
result={"status":"FAIL" if bad else "PASS","clock_sink_counts":dict(total),"memberships":{str(k):v for k,v in c.items()},"wrong_membership":bad}
print(json.dumps(result,indent=2));assert total=={"ck_dw":1056,"ck_de":1056};assert not bad
