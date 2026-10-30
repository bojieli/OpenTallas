# DIE-KV-33 KV-006 clock check analysis: region spread (land128 part_region via tree.json taps), provider FF CLK arrivals, clock DRV.
import json, collections, re, sys
W="/srv/opentallas-scratch2/claude/die-kv-33-1029/clk"
tree=json.load(open(sys.argv[1])); taps={x["port"]:x["part"] for x in tree["taps"]}
reg=json.load(open("/srv/opentallas-scratch2/claude/die-kv-2-1027/l128/land128_regions.json"))["part_region"]
out={}
for c in ("TT","FF"):
    R=collections.defaultdict(list); T={}; F=[]; N=[]
    for l in open(f"{W}/out_{c}/arr_{c}.txt"):
        f=l.split()
        if f[0]=="T": T[f[1]]=float(f[2]);
        elif f[0]=="F": F.append((f[1],float(f[2]),float(f[3]),float(f[4])))
        elif f[0]=="N": N.append(float(f[5]))
    miss=[p for p in taps if p not in T]
    for p,a in T.items():
        if p in taps: R[reg[taps[p]]].append(a)
    rs=sorted(((max(v)-min(v)),k) for k,v in R.items())
    drv=open(f"{W}/out_{c}/drv_{c}.rpt").read().splitlines()
    vio=[l for l in drv if "VIOLATED" in l]
    ckv=[l for l in vio if re.match(r"\s*(ck_|t_|root)",l) or "/CLK " in l]
    fa=[x[1] for x in F]
    out[c]=dict(taps=len(T),taps_missing=len(miss),tap_arr_min=round(min(T.values()),1),tap_arr_max=round(max(T.values()),1),
        regions=len(rs),spread_worst=[(round(a,1),k) for a,k in rs[-5:]],n_over_150=sum(a>150 for a,_ in rs),
        clk_cell_out_slew_max=round(max(N),1),tap_slew_max=round(max(float(l.split()[4]) for l in open(f"{W}/out_{c}/arr_{c}.txt") if l[0]=="T"),1),
        provider_ff=len(F),provider_ff_clk_arr=[round(min(fa),1),round(max(fa),1)],provider_ff_clk_slew_max=round(max(x[3] for x in F),1),
        drv_violations=len(vio),drv_clock_pin_violations=len(ckv),drv_clock_examples=ckv[:5])
json.dump(out,open(f"{W}/clock_check.json","w"),indent=1)
for c,v in out.items(): print(c,json.dumps(v))
