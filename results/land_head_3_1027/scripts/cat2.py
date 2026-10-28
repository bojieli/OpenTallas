import json,sys,collections,re
W="/srv/opentallas-scratch2/claude/wt/land-head-3/tools"
sys.path.insert(0,W+"/s81_head"); sys.path.insert(0,W+"/die_plan")
import landed_phase_ocv as L, clk_aocv as CA
Tb=CA.load(W+"/die_plan/clk_aocv_table_g021.json")
plan=json.load(open(sys.argv[2]))
d=sys.argv[1]
t=json.load(open(d+"/clk/tree.json"))
for C,cl in (("TT",250.0),("FF",202.5)):
    arr=L.arrivals(f"{d}/out_{C}/arr_{C}.txt")
    rows=L.analyse(plan,t,arr,CA,Tb,C,cl,416.5,"regions")
    cat=collections.defaultdict(list)
    for r in rows:
        k=re.sub(r"\d+","#",r["port"].split("__")[0]); cat[k].append(r)
    ca=min(416.5-max(r["p_up_ps"],r["p_dn_ps"]) for r in rows)
    print(C, "countaligned_worst", round(ca,1), "maxabsd", max(abs(r["d_ps"]) for r in rows), "maxU", max(max(r["unshared_a_ps"],r["unshared_b_ps"]) for r in rows))
    print(C, "worst", min(r["margin_ps"] for r in rows), "<100", sum(r["margin_ps"]<100 for r in rows), "<0", sum(r["margin_ps"]<0 for r in rows))
    for k,v in sorted(cat.items(), key=lambda kv: min(r["margin_ps"] for r in kv[1]))[:int(sys.argv[3]) if len(sys.argv)>3 else 12]:
        w=min(v,key=lambda r:r["margin_ps"])
        print("  %-14s n=%3d worst %7.1f d %7.1f U %6.0f/%6.0f p %4.0f/%4.0f %s-%s" % (k,len(v),w["margin_ps"],w["d_ps"],w["unshared_a_ps"],w["unshared_b_ps"],w["p_up_ps"],w["p_dn_ps"],w["src"],w["dst"]))
