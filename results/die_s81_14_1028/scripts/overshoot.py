# per early core tap (built go13 proof + declared core insertion credit): delivered core clock-pin arrival vs the
# median plain-tap arrival of the same partition (late, FF/TT); >0 = core pins later than plain, <0 = earlier
import json,statistics as st,collections,sys
for C in ("TT","FF"):
    d=json.load(open(f"proof_corelat/tap_arrivals_{C}.json"))
    by=collections.defaultdict(list); cores=[]
    for t in d["taps"]:
        (cores if "__clk_c" in t["port"] else by[t["part"]]).append(t) if "__clk_c" in t["port"] else by[t["part"]].append(t)
    cores=[t for t in d["taps"] if "__clk_c" in t["port"]]
    off=[]
    for t in cores:
        pl=[x["late_ps"] for x in by[t["part"]]]
        if not pl: continue
        off.append((t["late_ps"]-st.median(pl), t["port"]))
    off.sort(); v=[o for o,_ in off]
    print(C,"n",len(v),"p1 %.0f p10 %.0f p50 %.0f p90 %.0f p99 %.0f"%tuple(v[int(q*(len(v)-1))] for q in (.01,.1,.5,.9,.99)),
          "| <-180:",sum(1 for x in v if x<-180)," >+180:",sum(1 for x in v if x>180)," |off|<=60:",sum(1 for x in v if abs(x)<=60))
    print("  most early", [(round(o),p) for o,p in off[:6]]); print("  most late", [(round(o),p) for o,p in off[-4:]])
    reg=collections.Counter(p.split("__")[0][2:] for o,p in off if o<-180); print("  <-180 by part (top)", reg.most_common(8))
