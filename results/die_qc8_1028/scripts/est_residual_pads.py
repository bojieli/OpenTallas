# residual pads if pads only close the gap to the 150 gate (window = 150 - OCV), after SU early taps (S1)
import json,collections,math
D=json.load(open("/tmp/qc8_est_rows.json"))
reg=json.load(open("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json"))["part_region"]
res=json.load(open("/tmp/qc8_est_s1.json"))
info={x["g"]:x for L in res.values() for x in L}
TT=D["TT"]["rows"];FF=D["FF"]["rows"]
G=collections.defaultdict(list)
for p,r in TT.items(): G[reg[r["part"]]].append(p)
step={"TT":24.019,"FF":18.572}
tot=collections.Counter();taps=collections.Counter();pads=collections.Counter();regs=collections.Counter()
for g,ps in G.items():
  k="c" if g.startswith("c_") else ("su_c" if g.endswith("su_c") else "other")
  x=info[g];rho=x["rho"]
  b={"TT":{p:TT[p]["tree"]+250 for p in ps},"FF":{p:FF[p]["tree"]+FF[p]["lat"]-rho*(TT[p]["lat"]-250) for p in ps}}
  ocv={"TT":x["ocv"][0],"FF":x["ocv"][1]}
  need={}
  for c in b:
    W=150-ocv[c];mx=max(b[c].values())
    for p in ps:
      gap=mx-W-b[c][p]
      if gap>0: need[p]=max(need.get(p,0),math.ceil(gap/step[c]))
  taps[k]+=len(ps);tot[k]+=len(need);pads[k]+=sum(need.values());regs[k]+=bool(need)
for k in taps: print(k,"taps",taps[k],"padded",tot[k],f"({100*tot[k]/taps[k]:.1f}%)","pads",pads[k],"regions",regs[k])
print("all padded share",sum(tot.values())/sum(taps.values()))
