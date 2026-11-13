# Plan-level latency audit (COORD 16:2x BASELINE-HIDDEN ruling), modelled on native_istations.annotate:
#  (1) table fixed == lane fixed_cycles for every lane
#  (2) for every port whose SRC partition type is native (asbuilt internal_stations_types, bus filter
#      internal_stations_buses), lane fixed_cycles == src OUT station count + max dst IN station count
import json,sys
d=json.load(open(sys.argv[1])); a=json.load(open(sys.argv[2]))
T=d["partition_types"]; P=d["partitions"]
parts=P if isinstance(P,dict) else {x["name"]:x for x in P}
sel=set(a.get("internal_stations_types",[])); busf=a.get("internal_stations_buses",{})
ports={p["id"]:p for p in d["ports"]}; tab=d["latency"]["lanes"]
def rows(part,bus):
    t=T.get(parts.get(part,{}).get("type"),{})
    return [e for e in t.get("internal_stations",[]) if e.get("conn")=="bus:"+bus]
lanes_of={}
for L in d["lanes"]:
    for q in L["ports"]: lanes_of[q]=L
mis=[];nf=0;nn=0;seen=set()
for L in d["lanes"]:
    lid=L["id"]; lf=int(L.get("fixed_cycles",0)); tf=int((tab.get(lid) or {}).get("fixed",-1))
    if lf or tf>0: nf+=1
    if tf!=lf: mis.append((lid,"TABLE",f"table fixed {tf} != lane fixed_cycles {lf}"))
    for q in L["ports"]:
        p=ports.get(q)
        if not p or p["src"]["part"] not in parts: continue
        st=parts[p["src"]["part"]]["type"]; sb=p["src"]["bus"]
        if st not in sel: continue
        if st in busf and sb not in busf[st]: continue
        r=rows(p["src"]["part"],sb)
        if not r: continue
        c=max(len(e["regs_um"]) for e in r)
        last=ports[L["ports"][-1]]["dst"]; nxt=[ports[x]["dst"] for x in L["ports"] if x in ports]
        rcv=max((len(e["regs_um"]) for e in rows(last["part"],last["bus"])),default=0)
        nn+=1
        if lf!=c+rcv and (lid,q) not in seen:
            seen.add((lid,q)); mis.append((lid,"NATIVE",f"port {q} {p['src']['part']}({st}).{sb}: src {c} + dst {rcv} != lane fixed_cycles {lf}"))
print(sys.argv[1].split("/")[-2],"lanes",len(d["lanes"]),"fixed-cycle lanes",nf,"native ports",nn,"mismatches",len(mis))
for m in mis: print("  ",*m)
# reset rows: report type reset sync_stages vs die
rs=d["reset"].get("sync_stages")
bad=[(k,t["reset"].get("sync_stages")) for k,t in T.items() if isinstance(t.get("reset"),dict) and t["reset"].get("sync_stages") not in (None,rs)]
print("reset: die sync_stages",rs,"types differing",bad[:10])
