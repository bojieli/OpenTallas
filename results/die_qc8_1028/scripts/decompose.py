import json,collections,statistics
D=json.load(open("/tmp/qc8_est_rows.json"))
reg=json.load(open("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json"))["part_region"]
for c in ["TT","FF"]:
  rows=D[c]["rows"];com=D[c]["com"]
  G=collections.defaultdict(list)
  for p,r in rows.items(): G[reg[r["part"]]].append((p,r))
  print(c,"common",com,"regions",len(G),"ent None",sum(1 for r in rows.values() if r["ent"] is None))
  cls=collections.Counter();stats=[]
  for g,L in G.items():
    base=[r["base"] for _,r in L];tree=[r["tree"] for _,r in L]
    comtree=[r["tree"] for _,r in L if not r["core"]] or [0]
    mx=max(L,key=lambda x:x[1]["base"])
    stats.append(dict(g=g,n=len(L),spread=max(base)-min(base),tree_spread=max(tree)-min(tree),
      ncore=sum(r["core"] for _,r in L),maxset=(mx[1]["type"],mx[1]["tap"],mx[1]["lat"]),
      lats=sorted(set(round(r["lat"],1) for _,r in L)),entry_to_tap=[r["tree"]-r["ent_arr"] for _,r in L if r["ent_arr"]]))
  pref=collections.Counter(s["g"].split("_")[0]+"_"+("su" if "su" in s["g"] else s["g"].split("_")[-1][:2]) for s in stats)
  # group regions by name class
  def kls(g):
    return g.split("_")[0]+("_su_c" if g.endswith("su_c") else "")
  K=collections.defaultdict(list)
  for s in stats: K[kls(s["g"])].append(s)
  for k,L in sorted(K.items()):
    sp=[s["spread"] for s in L];ts=[s["tree_spread"] for s in L]
    e2t=[x for s in L for x in s["entry_to_tap"]]
    ms=collections.Counter(s["maxset"][0]+":"+str(s["maxset"][2]) for s in L).most_common(3)
    print(f" {k:10s} regs {len(L):3d} taps {sum(s['n'] for s in L):5d} spread med/max {statistics.median(sp):6.1f}/{max(sp):6.1f} tree med/max {statistics.median(ts):6.1f}/{max(ts):6.1f} ent->tap {min(e2t) if e2t else 0:.0f}-{max(e2t) if e2t else 0:.0f} maxset {ms} lats {L[0]['lats']}")
