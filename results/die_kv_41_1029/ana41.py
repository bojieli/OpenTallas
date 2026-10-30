# DIE-KV-41 KV-019 readout on a tap-only combo GRT (ana34.py form minus provider F lines/drv rpt). args: W(out_<c> parent) tree.json out.json [prefix]
import json, collections, sys
W=sys.argv[1]; P=833.333; pre=sys.argv[4] if len(sys.argv)>4 else "out_w243_"
tree=json.load(open(sys.argv[2])); taps={x["port"]:x["part"] for x in tree["taps"]}
reg=json.load(open("/srv/opentallas-scratch2/claude/die-kv-2-1027/l128/land128_regions.json"))["part_region"]
out={}
for c in ("TT","FF"):
    R=collections.defaultdict(list); T={}; TS=[]; N=[]
    for l in open(f"{W}/{pre}{c}/arr_{c}.txt"):
        f=l.split()
        if f[0]=="T": T[f[1]]=float(f[2]); TS.append(float(f[4]))
        elif f[0]=="N": N.append(float(f[5]))
    miss=[p for p in taps if p not in T]
    for p,a in T.items(): R[reg[taps[p]]].append(a)
    rs=sorted(((max(v)-min(v)),k) for k,v in R.items())
    du=[]
    for l in open(f"{W}/{pre}{c}/duty_{c}.txt"):
        f=l.split(); r,fa=float(f[2]),float(f[3]); du.append((0.5+(fa-r)/P,f[1]))
    dbad=[x for x in du if abs(x[0]-0.5)>0.05]
    # MPW estimate: min high/low pulse at tap = P/2 +- (fall-rise)
    mp=min(min(P*x[0],P*(1-x[0])) for x in du)
    out[c]=dict(taps=len(T),taps_missing=len(miss),regions=len(rs),spread_worst=[(round(a,1),k) for a,k in rs[-3:]],
        n_over_150=sum(a>150 for a,_ in rs),clk_cell_out_slew_max=round(max(N),1),tap_slew_max=round(max(TS),1),
        duty_range=[round(min(du)[0],3),round(max(du)[0],3)],duty_outside_45_55=len(dbad),min_pulse_est=round(mp,1))
json.dump(out,open(sys.argv[3],"w"),indent=1)
for c,v in out.items(): print(c,json.dumps(v))
