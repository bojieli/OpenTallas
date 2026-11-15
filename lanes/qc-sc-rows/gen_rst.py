"""QC-SC-ROWS-1115 class (c): reset copies for the sc types. Every ot_dp_st of the type (u_bin_*, u_bout_*, u_ft_*_o_*) takes
rst_n = rst_n_t0 (one copy at the core tap, 690-1040 um from the face registers). reset.consumer_localization rows move
each consumer whose tap-0 copy is > 405 um away onto the nearest published tap relay of EQUAL depth on the same clock
(reset_consumers.localize: same depth => 0 cycles, same clk, registered relay; fail closed at bind).
usage: gen_rst.py IN_PLAN OUT_PLAN OUT_ROWS   (tools/die_plan on sys.path, cwd tools/die_plan)"""
import sys,json,re,pathlib
sys.path.insert(0,".")
import schema, reset_tree as RT
inp,outp,orows=sys.argv[1:4]
raw=json.load(open(inp)); P=schema.Plan(raw,pathlib.Path(inp))
man=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
rows_all={}; rep=[]
for tn,t in sorted(raw["partition_types"].items()):
    if not re.match(r"sl[ew]_sc_v",tn): continue
    T=RT.for_type(P,tn); W,H=t["outline_um"]
    taps={r["q"]:r for r in T["relays"] if re.fullmatch(r"rst_n_t\d+",r.get("q",""))}
    t0=taps["rst_n_t0"]; d0=t0["depth"]
    cand=[r for r in taps.values() if r["depth"]==d0]
    cons=[]
    for b in t["buses"]:
        c=sum(b["window_um"])/2; pos={"E":[W,c],"W":[0,c],"N":[c,H],"S":[c,0]}[b["face"]]
        cons.append((("u_bin_" if b["dir"]=="in" else "u_bout_")+b["name"],pos))
    for s in t.get("ft_slots",[]):
        for i,r in enumerate(s["regs_um"]): cons.append((f"u_ft_{s['name']}_o_{i}",r))
    rows=[]
    for inst,pos in cons:
        cur=man(pos,t0["xy"]); best=min(cand,key=lambda r:man(pos,r["xy"])); nb=man(pos,best["xy"])
        if cur<=405 or nb>=cur: rep.append((tn,inst,round(cur),round(nb),"keep")); continue
        rows.append(dict(instance=inst,pin="rst_n",old_reset="rst_n",new_reset=best["q"],clock_net="clk"))
        rep.append((tn,inst,round(cur),round(nb),best["q"]))
    if rows: t.setdefault("reset",{})["consumer_localization"]=rows; rows_all[tn]=rows
for r in rep: print(*r)
print("types",len(rows_all),"rows",sum(map(len,rows_all.values())),"left >405:",[r for r in rep if r[3]>405])
json.dump(raw,open(outp,"w"),separators=(",",":")); json.dump(rows_all,open(orows,"w"),indent=1)
