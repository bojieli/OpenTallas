"""HBM-LOC-1 estimate: gap/cycle deltas for floorplan re-home options (NW half; NE = MY mirror).
usage: python3 est.py die_plan.json pairs81.tsv"""
import json,sys,math,collections
d=json.load(open(sys.argv[1])); pt=d["partition_types"]
P={p["name"]:dict(p) for p in d["partitions"]}
for n,p in P.items():
    p["w"],p["h"]=pt[p["type"]]["outline_um"]
REACH=405.0
def rect(p,ov):
    x,y=p["origin_um"]
    if p["name"] in ov: x=ov[p["name"]]
    return (x,y,x+p["w"],y+p["h"])
def gap(a,b,ov):
    A=rect(P[a],ov);B=rect(P[b],ov)
    dx=max(0,B[0]-A[2],A[0]-B[2]); dy=max(0,B[1]-A[3],A[1]-B[3])
    return round(dx+dy,3)
def cyc(g): return math.ceil(g/REACH)+2
ports={p["id"]:p for p in d["ports"]}
lat=d["latency"]["lanes"]
lanes=[]
for L in d["lanes"]:
    ps=[ports[i] for i in L["ports"] if i in ports]
    if not ps: continue
    s=ps[0]["src"]["part"]; t=ps[-1]["dst"]["part"]
    lanes.append(dict(id=L["id"],src=s,dst=t,width=ps[0]["width"],cyc=lat.get(L["id"],{}).get("cycles"),parts=[ps[0]["src"]["part"]]+[q["dst"]["part"] for q in ps]))
pairs=[l.rstrip("\n").split("\t") for l in open(sys.argv[2]) if not l.startswith(("src","#"))]
pairs=[(a,b,int(w)) for a,b,w,*_ in pairs if a.startswith("NW") or b.startswith("NW") or (a=="root" and b.startswith("NW"))]
# options: NW partition -> new x origin
OPT={
 "S0":{},
 "S1":{"NW_su00":0.0,"NW_su01":2108.16,"NW_su10":4043.52,"NW_spu0":6246.72,"NW_su11":7931.52,"NW_b113":10290.24},
 "S1b":{"NW_su00":0.0,"NW_su10":2108.16,"NW_su01":4311.36,"NW_spu0":6246.72,"NW_su11":7931.52,"NW_b113":10290.24},
 "C1":{"NW_su31":0.0,"NW_b110":1805.76,"NW_b111":9650.88,"NW_b102":10480.32,"NW_b103":11188.8},
}
OPT["Sa"]={"NW_b112":0.0,"NW_b113":1209.6,"NW_su00":3067.2,"NW_su01":5175.36,"NW_spu0":7110.72,"NW_su10":8795.52,"NW_su11":10998.72}
OPT["C2"]={"NW_b110":0.0,"NW_b111":414.72,"NW_su20":1218.24,"NW_su21":3222.72,"NW_spu1":5114.88,"NW_su30":6583.68,"NW_su31":8648.64,"NW_b103":10480.32,"NW_b102":11188.8}
OPT["L1"]=dict(OPT["Sa"],**OPT["C2"])
sel=sys.argv[3].split(",") if len(sys.argv)>3 else list(OPT)
SU=[n for n in P if n.startswith("NW_su")]
for o in sel:
    ov=OPT[o]
    print("=== option",o,ov)
    tot=collections.Counter()
    for a,b,w in pairs:
        g0=gap(a,b,{}); g1=gap(a,b,ov)
        if a in ov or b in ov or o=="S0":
            print("  UNPL %-8s->%-8s %5d b gap %8.1f -> %8.1f  cyc %3d -> %3d"%(a,b,w,g0,g1,cyc(g0),cyc(g1)))
    for l in lanes:
        if not (l["src"].startswith("NW") or l["dst"].startswith("NW") or l["src"]=="root"): continue
        if l["src"].startswith("NE") or l["dst"].startswith("NE"): continue
        if l["src"] in ov or l["dst"] in ov:
            g0=gap(l["src"],l["dst"],{}); g1=gap(l["src"],l["dst"],ov)
            dc=math.ceil(g1/REACH)-math.ceil(g0/REACH)
            if dc!=0:
                print("  LANE %-6s %-8s->%-8s %5d b plan %s cyc gap %8.1f -> %8.1f dcyc %+d %s"%(l["id"],l["src"],l["dst"],l["width"],l["cyc"],g0,g1,dc,"" if dc==0 else "<<"))

    # lanes passing THROUGH moved partitions (intermediate stations)
    thr=[l for l in lanes if any(p in ov for p in l["parts"][1:-1]) and not (l["src"].startswith("NE") or l["dst"].startswith("NE"))]
    print("  THROUGH-moved lanes: %d lanes / %d b: %s"%(len(thr),sum(l["width"] for l in thr)," ".join(l["id"]+"("+str(l["width"])+")" for l in thr)[:1500]))
    # overlap / alignment checks: every moved partition: list abutting neighbours before/after
    for n in ov:
        nb0=sorted(m for m in P if m!=n and not m.startswith("NE") and gap(n,m,{})==0)
        nb1=sorted(m for m in P if m!=n and not m.startswith("NE") and gap(n,m,ov)==0)
        print("  ABUT %-8s lost %s gained %s"%(n,sorted(set(nb0)-set(nb1)),sorted(set(nb1)-set(nb0))))
