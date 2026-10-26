import json,sys,re,collections
plan,unb=sys.argv[1:3]
p=json.load(open(plan)); dead=set(json.load(open(unb)))
lanes={l["id"]:l for l in p["lanes"]}
dpid={x for d in dead for x in lanes[d]["ports"]}
names=dead|dpid
pat=re.compile(r'"(L\d+m?(?:_\d+)?)"')
hits=collections.Counter()
for tn,t in p["partition_types"].items():
    for k,v in t.items():
        for m in pat.findall(json.dumps(v)):
            if m in names: hits[(tn,k)]+=1
for k in ("die","clock","reset","budgets","census"):
    for m in pat.findall(json.dumps(p[k])):
        if m in names: hits[("top",k)]+=1
print("id refs outside ports/lanes/latency:",dict(hits))
# also generic substring scan of lane ids with separators used e.g. "L44:" "L44_" in strings
s=json.dumps(p["partition_types"])
sub=collections.Counter()
for d in dead:
    for m in re.finditer(r'(?<![\w])'+re.escape(d)+r'(?![\dm])',s): sub[d]+=1
print("substring lane-id hits in types:",sum(sub.values()), sub.most_common(8))
