import json,collections,sys
k=sys.argv[1]
t=json.load(open(f"kit_{k}/clock/tree.json")); taps={x["port"]:x["part"] for x in t["taps"]}
reg=json.load(open("/srv/opentallas-scratch2/claude/die-kv-2-1027/l128/land128_regions.json"))["part_region"]
for c in ["TT","FF"]:
  R=collections.defaultdict(list)
  for l in open(f"out_{k}_{c}/arr_{c}.txt"):
    f=l.split()
    if f[0]=="T" and f[1] in taps: R[reg[taps[f[1]]]].append(float(f[2]))
  rs=sorted(((max(v)-min(v)),k2) for k2,v in R.items())
  print(k,c,"region spread worst",[(round(a,1),k2) for a,k2 in rs[-5:]],"n>150",sum(a>150 for a,_ in rs),"regions",len(rs))
