"""QC-SC-ROWS-1115: station rows for the 9 sc types (zero-logic hops > 405 um) as internal_stations + lane bumps + u_bin sidecar.
usage: gen_sc.py BASE_PLAN BASE_SIDECAR OUT_PLAN OUT_SIDECAR OUT_ROWS"""
import json,re,sys,math,collections
base,bside,oplan,oside,orows=sys.argv[1:6]
raw=json.load(open(base)); side=json.load(open(bside)); pt=raw["partition_types"]
man=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
def hops(s):
    p=[s["from_um"]]+s["regs_um"]+[s["to_um"]]; return [round(man(p[i],p[i+1])) for i in range(len(p)-1)]
def cen(b): return sum(b["window_um"])/2
def box(h):
    x,y=h["origin_um"]; w,hh=h["outline_um"]
    if h.get("orient","R0") in ("R90","R270","MXR90","MYR90"): w,hh=hh,w
    return (x,y,x+w,y+hh)
delta=collections.defaultdict(dict); rows={}; table=[]
for tn in sorted(pt):
    if not re.match(r"sl[ew]_sc_v",tn): continue
    t=pt[tn]; W,H=t["outline_um"]; hc=t["hard_cores"]; assert len(hc)==1
    bx=box(hc[0])
    for b in t["buses"]:
        if b["name"] not in ("x_fe_i","x_fe_o","x_ctl_o","x_ctl_i","flt_fe_i"): continue   # measured bin/bout<->core zero-logic hops over 405 (slw_sc_v3 a10, sle_sc_v1 a10); other buses: bin sits at the core, ring legs belong to the landing ring
        c=cen(b); P={"E":[W,c],"W":[0,c],"N":[c,H],"S":[c,0]}[b["face"]]; P=[round(P[0],3),round(P[1],3)]
        # core connect point = nearest point on the core box to the face pin (hard-core pins sit on the box edge)
        Q=[round(min(max(P[0],bx[0]),bx[2]),3),round(min(max(P[1],bx[1]),bx[3]),3)]
        d=man(P,Q); n=max(0,math.ceil(d/400.0)-1)
        table.append((tn,b["name"],b["dir"],b["width"],b["face"],round(d),n))
        if n==0: continue
        if any(e["conn"]=="bus:"+b["name"] for e in t.get("internal_stations",[])): table.append((tn,b["name"],"EXISTING ROW KEPT"));continue
        inp=b["dir"]=="in"
        regs=[[round(P[0]+(Q[0]-P[0])*k/(n+1),3),round(P[1]+(Q[1]-P[1])*k/(n+1),3)] for k in range(1,n+1)]
        if not inp: regs=regs[::-1]
        s=dict(conn="bus:"+b["name"],from_um=P if inp else Q,to_um=Q if inp else P,regs_um=regs,bits=int(b["width"]),
               launch="face flop" if inp else "core",capture="core" if inp else "face flop",bit_route="per_bit",
               note="S4q4 QC-SC-ROWS-1115 FABLE-PD-QC-0945 item 5: sc face -> hard-core edge, %d stations, hop <= 400 um; placed dump slw_sc_v3 a10 x_fe_i 771 um / x_fe_o 790 um / x_ctl_o 511 um"%n)
        t.setdefault("internal_stations",[]).append(s); delta[tn][b["name"]]=n; rows.setdefault(tn,[]).append(s)
        if inp:
            ub=[round((s["from_um"][0]+regs[0][0])/2,3),round((s["from_um"][1]+regs[0][1])/2,3)]
            side["types"].setdefault(tn,{})[b["name"]]={"u_bin":ub,"route_um":sum(hops(s)),"plan_stations":n,"first_hop_um":hops(s)[0],"note":"QC-SC-ROWS u_bin at mid first hop"}
lane_of={}
for ln in raw["lanes"]:
    for p in ln["ports"]: lane_of[p]=ln
parts={q["name"]:q["type"] for q in raw["partitions"]}
bump=collections.defaultdict(lambda:{"src":0,"dst":0})
for q in raw["ports"]:
    for e in ("src","dst"):
        tn=parts.get(q[e]["part"])
        if tn in delta and q[e]["bus"] in delta[tn]:
            bump[lane_of[q["id"]]["id"]][e]=max(bump[lane_of[q["id"]]["id"]][e],delta[tn][q[e]["bus"]])
byid={l["id"]:l for l in raw["lanes"]}; cnt=collections.Counter(); lb={}
for lid,v in bump.items():
    d=v["src"]+v["dst"]; byid[lid]["fixed_cycles"]=int(byid[lid].get("fixed_cycles",0))+d; cnt[d]+=1; lb[lid]=d
mx=max((h for r in rows.values() for s in r for h in hops(s)),default=0)
print("rows",{k:len(v) for k,v in rows.items()}); print("lanes bumped",len(bump),dict(cnt),"max hop",mx)
for r in table: print(*r)
json.dump(raw,open(oplan,"w"),separators=(",",":")); json.dump(side,open(oside,"w"),indent=1)
json.dump({"rows":rows,"lane_bumps":lb,"sidecar":{tn:side["types"].get(tn,{}) for tn in rows}},open(orows,"w"),indent=1)
