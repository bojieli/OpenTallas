import json,sys,math
sys.path.insert(0,"/srv/opentallas-scratch2/claude/die-head-48/clk5/tools/die_plan")
import die_sta_related as R
R.CPPR_LCA=True
pd=sys.argv[1]; BF=sys.argv[2] if len(sys.argv)>2 else "../st51/bind_l48w.json"; PB=sys.argv[3] if len(sys.argv)>3 else "patch_b"
b=json.load(open(BF)); T=833.0; sap=26.5
st={s["id"]:s for s in json.load(open(PB+"/start_stages_l48w_st.json"))["stages"]}
for c in ("TT","FF"):
    P=json.load(open(f"{pd}/tap_arrivals_{c}.json")); taps={t["port"]:t for t in P["taps"]}
    rg=json.load(open(f"../sta/o_l48w_single/regchar/{c}.json")); cq=(rg["clkq_min_nowire_ps"],rg["clkq_max_wire_ps"])
    n=0; worst=1e9
    for pid,x in b["start_ports"].items():
        edge="fall" if b["regions"].get(x["dst"],{}).get("edge_fall") else "rise"
        A,B=taps[x["launch"]],taps[x["capture"]]
        iv=R.ca_pair_interval(A,B,x["launch"],x["capture"],P["cppr_node_range_ps"],None,edge)[:2]
        off=T/2 if edge=="fall" else 0; elo,ehi=iv[0]-cq[1],iv[1]-cq[0]; k=math.floor((elo-off)/T)
        d=min(elo-(off+k*T),off+(k+1)*T-ehi) if math.floor((ehi-off)/T)==k else -1
        worst=min(worst,d)
        if d<sap:
            n+=1
            def info(key,t):
                if key.startswith("__st__"):
                    s=st[key.split("@")[1]]; return f"{s['id']} hop{abs(s['node_xy_um'][0]-s['clock_pin_xy_um'][0])+abs(s['node_xy_um'][1]-s['clock_pin_xy_um'][1]):.0f} sl{t.get('slew_ps',0):.0f}"
                return key
            print(c,edge,"d",round(d,1),"iv",[round(v) for v in iv],"L",info(x["launch"],A),"C",info(x["capture"],B))
    print(c,"fail",n,"worst",round(worst,1))
