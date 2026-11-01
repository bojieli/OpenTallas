import json,sys
PD=sys.argv[1]
sys.path.insert(0,"/srv/opentallas-scratch2/claude/die-head-48/clk5/tools/die_plan")
import die_sta_related as R
R.CPPR_LCA=True
for c in ("TT","FF"):
  a=json.load(open(f"{PD}/tap_arrivals_{c}.json")); b=json.load(open(f"../st51/proof_l48c_e/tap_arrivals_{c}.json"))
  tb={t["port"]:t for t in b["taps"]}
  d=[]; df=[]
  for t in a["taps"]:
    if t["port"] in tb:
      o=tb[t["port"]]; d.append(max(abs(t["late_ps"]-o["late_ps"]),abs(t["early_ps"]-o["early_ps"]))); df.append(max(abs(t["fall_late_ps"]-o["fall_late_ps"]),abs(t["fall_early_ps"]-o["fall_early_ps"])))
  d.sort(); df.sort()
  sg=sorted(t["late_ps"]-o["late_ps"] for t in a["taps"] if t["port"] in tb for o in [tb[t["port"]]])
  print(c,"existing taps",len(d),"|d| rise p50/p99/max",round(d[len(d)//2],2),round(d[int(.99*len(d))],2),round(d[-1],2),"fall max",round(df[-1],2),"signed late min/max",round(sg[0],2),round(sg[-1],2), ">5ps",sum(x>5 for x in d))
  # measured stage taps vs virtual model on proof_l48c_e
  real={q:t for q,t in tb.items()}
  leg=R.tap_leg(b,real); fl=R.tap_leg_fall(b,real)
  st=[t for t in a["taps"] if t["port"].startswith("__st__")]
  dv=[]
  for t in st:
    tp={}; k=R.virtual_tap(b,tp,t["port"][6:],leg,fl); v=tp[k]; dv.append(t["late_ps"]-v["late_ps"])
  dv.sort(); print(c,"stage taps",len(st),"measured - virtual late p1/p50/p99/max",round(dv[int(.01*len(dv))],1),round(dv[len(dv)//2],1),round(dv[int(.99*len(dv))],1),round(dv[-1],1), "slew max", round(max(t.get("slew_ps",0) for t in st),1))
