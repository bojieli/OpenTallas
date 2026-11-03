import json,sys,collections as C,math
P="/srv/opentallas-scratch2/claude/die-head-48/clk_st51/proof_l48w_sth/"
p=json.load(open(sys.argv[1])); ca=set(json.load(open(sys.argv[2]))["ports"])
A={c:json.load(open(P+f"tap_arrivals_{c}.json")) for c in ("TT","FF")}
ty={x["name"]:x["type"] for x in p["partitions"]}
taps={c:C.defaultdict(list) for c in A}
for c in A:
    for t in A[c]["taps"]: taps[c][t["part"]].append(t)
T=833.0; REG={"TT":dict(cqmax=84.5,cqmin=52.1,su=15.0,ho=16.4),"FF":dict(cqmax=59.5,cqmin=37.0,su=8.0,ho=13.2)}
UH=25.0; LCQ=73.0; LCQMIN=15.0
def lca(a,b):
    n=0
    while n<min(len(a),len(b)) and a[n]==b[n]: n+=1
    return a[:n]
def credit(c,a,b):
    node=lca(a["tree_path"],b["tree_path"])
    while node and node not in A[c]["node_late_ps"]: node=node[:-1]
    return (A[c]["node_late_ps"][node]-A[c]["node_early_ps"][node]) if node else 0.0
def near(sa,sb):
    best=None
    for a in sa:
        for b in sb:
            dd=math.dist(a["xy_um"],b["xy_um"])
            if best is None or dd<best[0]: best=(dd,a,b)
    return best
out=[];agg=C.defaultdict(lambda:dict(n=0,hold_plain=1e9,hold_latch=1e9,setup_plain=1e9,setup_latch=1e9,skew_max=0,dist=0))
for x in p["ports"]:
    s,d=x["src"]["part"],x["dst"]["part"]
    if s not in taps["FF"] or d not in taps["FF"]: continue
    _,a,b=near(taps["FF"][s],taps["FF"][d])
    # same taps in TT by port name
    tt={t["port"]:t for t in taps["TT"][s]+taps["TT"][d]}
    at,bt=tt[a["port"]],tt[b["port"]]
    crf=credit("FF",a,b); r=REG["FF"]
    hold_plain=(a["early_ps"]+r["cqmin"])-(b["late_ps"]+r["ho"])-UH+crf
    hold_latch=(a["fall_early_ps"]+T/2+LCQMIN)-(b["late_ps"]+r["ho"])-UH+crf
    r=REG["TT"]; na=(at["late_ps"]+at["early_ps"])/2; nb=(bt["late_ps"]+bt["early_ps"])/2
    naf=(at["fall_late_ps"]+at["fall_early_ps"])/2
    wire=0.0
    setup_plain=(nb+T)-(na+r["cqmax"]+wire)-r["su"]
    setup_latch=(nb+T)-(naf+T/2+LCQ+wire)-r["su"]
    form="landed_CA" if x["id"] in ca else "seam"
    k=(form,ty[s],ty[d]); g=agg[k]; g["n"]+=1
    for f,v in (("hold_plain",hold_plain),("hold_latch",hold_latch),("setup_plain",setup_plain),("setup_latch",setup_latch)): g[f]=round(min(g[f],v),1)
    g["skew_max"]=round(max(g["skew_max"],abs(nb-na)),1); g["dist"]=round(max(g["dist"],_),1)
    out.append(dict(port=x["id"],form=form,src=s,dst=d,src_type=ty[s],dst_type=ty[d],width=x["width"],launch_tap=a["port"],capture_tap=b["port"],
        tap_dist_um=round(_,1),L_tt_nom=round(na,1),C_tt_nom=round(nb,1),L_ff_early=round(a["early_ps"],1),C_ff_late=round(b["late_ps"],1),
        cppr_ff=round(crf,1),hold_plain_ff=round(hold_plain,1),hold_latch_ff=round(hold_latch,1),setup_plain_tt=round(setup_plain,1),setup_latch_tt=round(setup_latch,1)))
json.dump(dict(model=dict(T=T,reg=REG,unc_hold=UH,latch_ckq_tt=LCQ,latch_ckq_min_ff=LCQMIN,taps="l48w sth die clock (die-head-48/clk_st51/proof_l48w_sth), nearest launch/capture tap pair (face register leaf proxy)",
    cppr="last common tree node, FF late-early"),rows=out),open(sys.argv[3],"w"),indent=0)
for k,g in sorted(agg.items()):
    print(k,g)
