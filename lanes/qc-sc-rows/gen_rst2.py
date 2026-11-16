"""QC-SC-ROWS-1115 reset localization v2: tree = the type own clock.landing_contract.collector_tree (what bind.py publishes), every row
is dry-run through reset_consumers.localize on the type EMITTED RTL (bind rtl dir of a plan that has no rows), failing types get no rows.
usage: gen_rst2.py IN_PLAN BIND_RTL_DIR OUT_PLAN OUT_ROWS REPORT   (cwd tools/die_plan of the tree whose reset_consumers is used)"""
import sys,json,re,os
sys.path.insert(0,".")
import reset_consumers as RC
inp,rtl,outp,orows,rep_f=sys.argv[1:6]
raw=json.load(open(inp)); man=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
rows_all={}; rep=[]
for tn,t in sorted(raw["partition_types"].items()):
    if not re.match(r"sl[ew]_sc_v",tn): continue
    t.get("reset",{}).pop("consumer_localization",None)
    tree=t["clock"]["landing_contract"]["collector_tree"]; W,H=t["outline_um"]
    f=os.path.join(rtl,t["module"]+"__"+tn+".sv")
    if not os.path.exists(f): f=os.path.join(rtl,t["module"]+".sv")
    if not os.path.exists(f): f=os.path.join(rtl,tn+".sv")
    if not os.path.exists(f): rep.append((tn,"NO_EMITTED_RTL",f)); continue
    txt=open(f).read()
    taps={r["q"]:r for r in tree["relays"] if re.fullmatch(r"rst_n_t\d+",r.get("q",""))}
    t0=taps.get("rst_n_t0")
    if not t0: rep.append((tn,"NO_TAP0")); continue
    cand=[r for r in taps.values() if r["depth"]==t0["depth"]]
    cons=[]
    for b in t["buses"]:
        c=sum(b["window_um"])/2; pos={"E":[W,c],"W":[0,c],"N":[c,H],"S":[c,0]}[b["face"]]
        cons.append((("u_bin_" if b["dir"]=="in" else "u_bout_")+b["name"],pos))
    for s in t.get("ft_slots",[]):
        for i,r in enumerate(s["regs_um"]): cons.append((f"u_ft_{s["name"]}_o_{i}",r))
    rows=[]; bad=0
    for inst,pos in cons:
        cur=man(pos,t0["xy"]); best=min(cand,key=lambda r:man(pos,r["xy"])); nb=man(pos,best["xy"])
        if cur<=405 or nb>=cur: continue
        row=dict(instance=inst,pin="rst_n",old_reset="rst_n",new_reset=best["q"],clock_net="clk")
        try: RC.localize(txt,[row],tree,{}); rows.append(row)
        except Exception as e: bad+=1; why=str(e)[:160]
    rep.append((tn,"rows",len(rows),"rejected",bad, why if bad else ""))
    if rows and not bad: t.setdefault("reset",{})["consumer_localization"]=rows; rows_all[tn]=rows
    elif rows: rep.append((tn,"PARTIAL kept none",)); 
for r in rep: print(*r)
print("types with rows",len(rows_all),"rows",sum(map(len,rows_all.values())))
json.dump(raw,open(outp,"w"),separators=(",",":")); json.dump(rows_all,open(orows,"w"),indent=1)
