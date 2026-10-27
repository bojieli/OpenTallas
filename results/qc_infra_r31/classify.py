import json,collections,re,sys
d=json.load(open(sys.argv[1])); s=json.load(open(sys.argv[2]))
e=[v for v in d.values() if isinstance(v,list)][0]
by={n["edge"]:n for n in s["nets"]}
c=collections.Counter(); yl=collections.Counter(); fam=collections.Counter()
for x in e:
    m=re.match(r"(.*?) (M\d) ideal ([\d.]+)",x["detail"]); n=by.get(x["edge"],{})
    c[(m.group(2),n.get("ndr"),m.group(1).split()[0])]+=1; yl[(m.group(2),m.group(3))]+=1; fam[x["edge"].split(":")[0]+":"+re.sub(r"\d","",x["edge"].split(":")[1])[:6]]+=1
print(len(e)); print(c.most_common()); print(len(yl),yl.most_common(10)); print(fam.most_common(10))
