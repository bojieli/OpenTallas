import json,collections
P=json.load(open("/srv/opentallas-scratch2/claude/die-head-19/ports_r1.json"))
AP=833/8
tile={"TT":dict(F=(192.6,196.7),C=(189.4,212.7),R=(501.4,539.8)),"FF":dict(F=(157.6,161.2),C=(155.9,176.9),R=(401.5,435.6))}
S={"TT":38.4+23.3+4.1,"FF":34.1+21.0+3.6}  # tile-like intra spreads R+C+F (assumed for unbuilt types)
W={"TT":1.0,"FF":1.0}
g=collections.defaultdict(list)
for o in P:
    if o["ring"]=="declared": g[(o["ts"],o["td"])].append(o)
rows=[]
for (ts,td),os_ in sorted(g.items(),key=lambda x:min(o["ml"] for o in x[1])):
    line=[f"{ts}->{td}",str(len(os_)//2)]
    for C in ("TT","FF"):
        oc=[o for o in os_ if o["C"]==C]
        smin=max(100-o["ml"] for o in oc); smax=min(o["mh"]-AP for o in oc)
        t=tile[C]
        if td=="hd_tile":   # unknown = fwd_out(ts): shift_lo = R_e - F_l - w - C_l >= smin ; shift_hi = R_l - F_e - C_e <= smax
            q="fwd_out(%s)"%ts; hi=t["R"][0]-W[C]-t["C"][1]-smin; lo=t["R"][1]-t["C"][0]-smax
            line.append(f"{q} in [{max(lo,0):.0f}, {hi:.0f}] (late/early edge)")
        elif ts=="hd_tile": # unknown = reader(td)-fclk_in(td): writer = tile F + w + C
            q="reader-fclk_in(%s)"%td; lo=smin+t["F"][1]+W[C]; hi=smax+t["F"][0]
            line.append(f"{q} early-late >= {lo:.0f}, late-early <= {hi:.0f}")
        else:
            lo=smin+S[C]/2+W[C]; hi=smax-S[C]/2
            line.append(f"m in [{lo:.0f}, {hi:.0f}]")
    rows.append(" | ".join(line))
print("pair | ports | TT | FF"); print("\n".join(rows))
