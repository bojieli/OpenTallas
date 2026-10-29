# DIE-KV-34 clock check readout (same as DIE-KV-33 ana.py) + duty from rise/fall tap arrivals. args: clkdir tree.json out.json
import json, collections, re, sys
W=sys.argv[1]; P=833.333
tree=json.load(open(sys.argv[2])); taps={x["port"]:x["part"] for x in tree["taps"]}
reg=json.load(open("/srv/opentallas-scratch2/claude/die-kv-2-1027/l128/land128_regions.json"))["part_region"]
out={}
for c in ("TT","FF"):
    R=collections.defaultdict(list); T={}; F=[]; N=[]; TS=[]
    for l in open(f"{W}/out_{c}/arr_{c}.txt"):
        f=l.split()
        if f[0]=="T": T[f[1]]=float(f[2]); TS.append(float(f[4]))
        elif f[0]=="F": F.append((f[1],float(f[2]),float(f[3]),float(f[4])))
        elif f[0]=="N": N.append(float(f[5]))
    miss=[p for p in taps if p not in T]
    for p,a in T.items():
        if p in taps: R[reg[taps[p]]].append(a)
    rs=sorted(((max(v)-min(v)),k) for k,v in R.items())
    drv=open(f"{W}/out_{c}/drv_{c}.rpt").read().splitlines()
    vio=[l for l in drv if "VIOLATED" in l]
    ckv=[l for l in vio if re.match(r"\s*(ck_|t_|root|lf_|leaf)",l) or "/CLK " in l]
    du=[]
    for l in open(f"{W}/out_{c}/duty_{c}.txt"):
        f=l.split(); r,fa=float(f[2]),float(f[3]); du.append((0.5+(fa-r)/P, f[1]))
    dbad=[x for x in du if abs(x[0]-0.5)>0.05]
    fa=[x[1] for x in F]
    out[c]=dict(taps=len(T),taps_missing=len(miss),tap_arr=[round(min(T.values()),1),round(max(T.values()),1)],
        regions=len(rs),spread_worst=[(round(a,1),k) for a,k in rs[-3:]],n_over_150=sum(a>150 for a,_ in rs),
        clk_cell_out_slew_max=round(max(N),1),tap_slew_max=round(max(TS),1),
        provider_ff=len(F),provider_ff_clk_arr=[round(min(fa),1),round(max(fa),1)],provider_ff_clk_slew_max=round(max(x[3] for x in F),1),
        ff_clk_slew_over_320=sum(x[3]>320 for x in F),
        duty_range=[round(min(du)[0],3),round(max(du)[0],3)],duty_outside_45_55=len(dbad),
        drv_violations=len(vio),drv_clock_pin_violations=len(ckv),drv_clock_examples=ckv[:3])
json.dump(out,open(sys.argv[3],"w"),indent=1)
for c,v in out.items(): print(c,json.dumps(v))
