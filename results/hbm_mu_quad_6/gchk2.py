import json, sys
d = json.load(open(sys.argv[1])); T = d["partition_types"]
def R(c): x, y = c["origin_um"]; w, h = c["outline_um"]; return (x, y, x + w, y + h)
def ov(a, b): return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
for tn in ["q_mca","q_mcb","q_spu0","q_spt1","vsN5","q_spb1","PHY_N","q_b010","q_b001"]:
    t=T[tn]; print(tn, (t.get("note") or "")[:300], "| contents", [(c["inst"],c.get("cells")) for c in t["contents"]][:6], "| ft_slots", len(t.get("ft_slots",[])), "buses", len(t.get("buses",[])))
for tn in ["q_hub_nw","q_hub_ne","root","q_su31","q_su01","q_su00"]:
    t=T[tn]; hc=[(c["inst"],R(c)) for c in t["hard_cores"]]; hn={n for n,_ in hc}
    sc=[(c["inst"],R(c)) for c in t["contents"] if "origin_um" in c and c["inst"] not in hn]
    real=[(s,h,round(ov(sr,hr))) for s,sr in sc for h,hr in hc if ov(sr,hr)>100 and not h.startswith(s+"_") and not h.startswith(s+".") ]
    ss=[(a,b,round(ov(ar,br))) for i,(a,ar) in enumerate(sc) for b,br in sc[i+1:] if ov(ar,br)>100 and not b.startswith(a) and not a.startswith(b)]
    print(tn,"soft-on-foreign-hard",len(real),real[:4],"| soft-soft",len(ss),ss[:3])
# stations in hard detail
def inside(p,r,e=0.5): return r[0]+e<p[0]<r[2]-e and r[1]+e<p[1]<r[3]-e
for tn in ["q_su11","q_hub_nw","root","q_su21"]:
    t=T[tn]; hc=[(c["inst"],R(c)) for c in t["hard_cores"]]
    ex=[(s["conn"][:50],p,n) for s in t.get("internal_stations",[]) for p in s.get("regs_um",[]) for n,r in hc if inside(p,r)][:3]
    fx=[(s["name"],p,n) for s in t.get("ft_slots",[]) for p in s.get("regs_um",[]) for n,r in hc if inside(p,r)][:3]
    print(tn,"st",ex,"ft",fx)
