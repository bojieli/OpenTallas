import sys,json,re,collections,itertools
D,PLAN,TOOLS=sys.argv[1:4]; sys.path.insert(0,TOOLS)
import schema as S
P=S.Plan(S.load(PLAN)); M=json.load(open(f"{D}/mesh.json"))
reg={t["port"]:t["region"] for t in M["taps"]}; part={t["port"]:t["part"] for t in M["taps"]}; xy={t["port"]:t["xy"] for t in M["taps"]}
tb=collections.defaultdict(list)
for t in M["taps"]: tb[t["part"]].append(t["port"])
rtag={g["k"]:g["tag"] for g in M["meta"]["regions"]}
conn={tuple(sorted((p["src"]["part"],p["dst"]["part"]))) for p in P.ports.values() if p["src"]["part"] in tb and p["dst"]["part"] in tb and p["src"]["part"]!=p["dst"]["part"]}
pairs=set()
for ts in tb.values(): pairs.update(itertools.combinations(sorted(ts),2))
for u,v in conn:
  if reg[tb[u][0]]!=reg[tb[v][0]]: continue
  pairs.update((a,b) for a in tb[u] for b in tb[v])
out={"pairs":len(pairs)}
for c in ("TT","FF"):
  N={}
  for l in open(f"{D}/tree_{c}.txt"):
    f=l.split()
    if len(f)>=4:N[f[1]]=(float(f[2]),float(f[3]))
  cred={}
  for k,tg in rtag.items():
    nm=[n for n in N if re.match(rf"ckm_n\d+_{tg}$",n)]; cred[k]=(N[nm[0]][0]-N[nm[0]][1]) if nm else 0.
  arr={}
  for l in open(f"{D}/taps_{c}.txt"):
    f=l.split(); arr[f[1]]=(float(f[2]),float(f[3]))
  def dm(a,b):
    cc=min(cred[reg[a]],arr[a][0]-arr[a][1],arr[b][0]-arr[b][1]); return max(arr[a][0]-arr[b][1],arr[b][0]-arr[a][1])-cc
  vals=[(dm(a,b),a,b) for a,b in pairs]; bad=[v for v in vals if v[0]>80]
  kinds=collections.Counter(("intra" if part[a]==part[b] else "cross", part[a] if part[a]==part[b] else part[a]+"|"+part[b]) for _,a,b in bad)
  bad.sort(reverse=True)
  out[c]={"max":round(bad[0][0] if bad else max(vals)[0],2),"n_over80":len(bad),"over80_by":kinds.most_common(20),"top":[(round(v,2),a,b,xy[a],xy[b]) for v,a,b in bad[:10]],
    "p99":round(sorted(v[0] for v in vals)[int(.99*len(vals))],2)}
json.dump(out,open(f"{D}/../c3e_complete_pairs.json","w"),indent=1); print(json.dumps(out,indent=1))
