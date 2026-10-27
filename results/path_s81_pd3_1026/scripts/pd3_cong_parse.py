import re,sys,json,collections
rpt=sys.argv[1]
V=[];cur={}
for ln in open(rpt):
    if ln.startswith("violation type"): cur={"dir":ln.split(":")[1].strip().split()[0]}
    elif "srcs:" in ln: cur["nets"]=re.findall(r"net:(\S+)",ln)
    elif "comment:" in ln:
        m=re.search(r"capacity:(\d+) usage:(\d+) congestion:(\d+)",ln); cur["cap"],cur["use"],cur["ov"]=map(int,m.groups())
    elif "bbox" in ln:
        m=re.search(r"\(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)",ln); cur["bb"]=list(map(float,m.groups())); V.append(cur)
print("viol",len(V),"sum_ov",sum(v["ov"] for v in V), "by dir",collections.Counter(v["dir"] for v in V))
pre=collections.Counter()
for v in V:
    for n in v["nets"]:
        p=re.sub(r"\[\d+\]$","",n); p=re.sub(r"\d+","#",p); pre[p]+=1
print(pre.most_common(25))
xs=[v["bb"][0] for v in V]; ys=[v["bb"][1] for v in V]
print("x range",min(xs),max(xs),"y range",min(ys),max(ys))
cap0=sum(1 for v in V if v["cap"]==0); print("cap0 gcells",cap0, "ov on cap0",sum(v["ov"] for v in V if v["cap"]==0))
json.dump(V,open(sys.argv[2],"w"))
