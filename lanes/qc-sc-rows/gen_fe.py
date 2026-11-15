"""QC-SC-ROWS-1115 fe family: station gaps of S4q4c (face -> core-centre model) against MEASURED placed dumps.
usage: gen_fe.py BASE_PLAN BASE_SIDECAR SCAN_TXT... OUT_PLAN OUT_SIDECAR OUT_ROWS ; scan txt = placed_scan NEED/REACH lines of sle_fe_v1 (x2) and sle_fe_v2 dumps.
Rules: core leg / bus leg groups: stations >= ceil(max/400)-1 on that bus; pass-through bin->bout: stations(in)+stations(out) >= ceil(max/400)-1;
ring -> bin groups on a bus without a row: 1 station + u_bin at mid first hop (QC-FWST form). Applied to same-named buses of the sibling types
(sle_fe_v1_* <- v1 dumps, sle_fe_v2/v3 <- v2 dump, slw_fe_* <- sle v1/v2 by bus name = INFERENCE)."""
import json,re,sys,math,copy,collections
base,bside=sys.argv[1:3]; scans=sys.argv[3:-3]; oplan,oside,orows=sys.argv[-3:]
raw=json.load(open(base)); side=json.load(open(bside)); pt=raw["partition_types"]
man=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
need=collections.defaultdict(dict)   # family -> bus -> (kind, max)
pas=collections.defaultdict(dict)    # family -> (busin,busout) -> max
for f in scans:
    fam="v2" if "fe_v2" in f else "v1"
    for ln in open(f):
        m=re.match(r"\s+(NEED-STATION|REACH)\s+(\S+) -> (\S+)\t.* max (\d+)um",ln)
        if not m: continue
        src,dst,mx=m[2],m[3],int(m[4])
        src=src.replace("u_bound.",""); dst=dst.replace("u_bound.","")
        if src.startswith("u_core.") and dst.startswith("u_bout_"): b,k=dst[7:],"core"
        elif src.startswith("u_bin_") and dst.startswith("u_core."): b,k=src[6:],"core"
        elif src.startswith("u_bin_") and dst.startswith("u_bout_"):
            pas[fam][(src[6:],dst[7:])]=max(mx,pas[fam].get((src[6:],dst[7:]),0)); continue
        else: continue
        need[fam][b]=(k,max(mx,need[fam].get(b,("",0))[1]))
def bus(t,n): return next((b for b in t["buses"] if b["name"]==n),None)
def cen(b): return sum(b["window_um"])/2
delta=collections.defaultdict(dict); rows={}; log=[]
def setrow(tn,bn,n,why):
    t=pt[tn]; W,H=t["outline_um"]; core=[round(W/2,3),round(H/2,3)]; b=bus(t,bn)
    if b is None: return
    c=cen(b); P={"E":[W,c],"W":[0,c],"N":[c,H],"S":[c,0]}[b["face"]]; P=[round(P[0],3),round(P[1],3)]
    inp=b["dir"]=="in"
    regs=[[round(P[0]+(core[0]-P[0])*k/(n+1),3),round(P[1]+(core[1]-P[1])*k/(n+1),3)] for k in range(1,n+1)]
    if not inp: regs=regs[::-1]
    s=dict(conn="bus:"+bn,from_um=P if inp else list(core),to_um=list(core) if inp else P,regs_um=regs,bits=int(b["width"]),
           launch="face flop" if inp else "core",capture="core" if inp else "face flop",bit_route="per_bit",
           note="S4q4 QC-SC-ROWS-1115 fe gap vs placed dump: %s, %d stations"%(why,n))
    st=t.setdefault("internal_stations",[]); old=next((e for e in st if e["conn"]==s["conn"]),None)
    delta[tn][bn]=n-(len(old["regs_um"]) if old else 0)
    if old: st[st.index(old)]=s
    else: st.append(s)
    rows.setdefault(tn,[]).append(s)
    if inp:
        ub=[round((P[0]+regs[0][0])/2,3),round((P[1]+regs[0][1])/2,3)]
        side["types"].setdefault(tn,{})[bn]={"u_bin":ub,"route_um":man(P,core),"plan_stations":n,"first_hop_um":round(man(P,regs[0])),"note":"QC-SC-ROWS fe gap, u_bin at mid first hop"}
def have(tn,bn):
    e=next((e for e in pt[tn].get("internal_stations",[]) if e["conn"]=="bus:"+bn),None); return len(e["regs_um"]) if e else 0
for tn in sorted(pt):
    if not re.match(r"sl[ew]_fe_v",tn): continue
    fam="v2" if re.match(r"sl[ew]_fe_v[23]",tn) else "v1"
    for bn,(k,mx) in need[fam].items():
        if bus(pt[tn],bn) is None: continue
        req=math.ceil(mx/400)-1
        if have(tn,bn)<req: setrow(tn,bn,req,"%s leg max %d um (%s dump)"%(k,mx,fam))
    for (bi,bo),mx in pas[fam].items():
        if bus(pt[tn],bi) is None or bus(pt[tn],bo) is None: continue
        req=math.ceil(mx/400)-1
        if have(tn,bi)+have(tn,bo)<req: setrow(tn,bo,req-have(tn,bi),"pass-through %s->%s max %d um (%s dump)"%(bi,bo,mx,fam))
# lanes (same additive rule as gen_fwst)
lane_of={}
for ln in raw["lanes"]:
    for p in ln["ports"]: lane_of[p]=ln
parts={q["name"]:q["type"] for q in raw["partitions"]}
bump=collections.defaultdict(lambda:{"src":0,"dst":0})
for q in raw["ports"]:
    for e in ("src","dst"):
        tn=parts.get(q[e]["part"])
        if tn in delta and q[e]["bus"] in delta[tn] and delta[tn][q[e]["bus"]]>0:
            bump[lane_of[q["id"]]["id"]][e]=max(bump[lane_of[q["id"]]["id"]][e],delta[tn][q[e]["bus"]])
byid={l["id"]:l for l in raw["lanes"]}; lb={}
for lid,v in bump.items():
    d=v["src"]+v["dst"]; byid[lid]["fixed_cycles"]=int(byid[lid].get("fixed_cycles",0))+d; lb[lid]=d
print("fe rows",{k:[(s["conn"][4:],len(s["regs_um"])) for s in v] for k,v in rows.items()}); print("lanes bumped",len(lb),collections.Counter(lb.values()))
json.dump(raw,open(oplan,"w"),separators=(",",":")); json.dump(side,open(oside,"w"),indent=1); json.dump({"rows":rows,"lane_bumps":lb},open(orows,"w"),indent=1)
