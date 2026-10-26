"""b1e step 4a: vm_wr_q re-pin. Both instances (q_hub_nw/q_hub_ne u_smw_Q) select the W-face copies of wq_t1/wq_t3
(pin_select wq_tN -> wq_tN__W); the superset table carried both faces, which the RTL top (one wq_tN port) cannot match.
New table: wq_t1/wq_t3 pins sit at the former __W sites; the unused E-face copies and the __W names are dropped.
0 logic, 0 cycles; pin_select/unused_pins entries for wq_t1/wq_t3 removed."""
import json,sys,re,hashlib
plan_dir=sys.argv[1]; rep=sys.argv[2]
pf="cores/ot_hbm_sm_vm_wr_q_t_lanes4__142.56x388.8__q_hub_u_smw_Q.json"
pins=json.load(open(f"{plan_dir}/{pf}"))
old=hashlib.sha256(open(f"{plan_dir}/{pf}","rb").read()).hexdigest()
out=[];drop=0;ren=0
for q in pins:
    b=re.sub(r"\[\d+\]$","",q["name"])
    if b in ("wq_t1","wq_t3"): drop+=1; continue
    if b in ("wq_t1__W","wq_t3__W"):
        q=dict(q,name=q["name"].replace("__W","")); ren+=1
    out.append(q)
names=[q["name"] for q in out]; assert len(names)==len(set(names))
xy=[(q["layer"],q["x"],q["y"]) for q in out]; assert len(xy)==len(set(xy))
s=json.dumps(out); open(f"{plan_dir}/{pf}","w").write(s)
p=json.load(open(f"{plan_dir}/die_plan.json")); n=0
for tn,t in p["partition_types"].items():
    for h in t.get("hard_cores",[]):
        if h["module"]=="ot_hbm_sm_vm_wr_q_t_lanes4":
            assert h["pin_select"]=={"wq_t1":"wq_t1__W","wq_t3":"wq_t3__W"}, h["pin_select"]
            del h["pin_select"]; h["unused_pins"]=[u for u in h["unused_pins"] if u not in ("wq_t1","wq_t3")]
            if not h["unused_pins"]: del h["unused_pins"]; h.pop("unused_pins_policy",None)
            h["note"]+=" | b1e re-pin: wq_t1/wq_t3 on the W face (former __W sites), E copies dropped (both instances used W)"
            n+=1
assert n==2,n
ps=json.dumps(p,indent=1); open(f"{plan_dir}/die_plan.json","w").write(ps)
json.dump(dict(pins_file=pf,pins_before=len(pins),pins_after=len(out),dropped_E_copies=drop,renamed_W=ren,instances=n,
               pins_sha_before=old,pins_sha_after=hashlib.sha256(s.encode()).hexdigest(),
               layers={l:sum(1 for q in out if q["layer"]==l) for l in sorted({q["layer"] for q in out})}),open(rep,"w"),indent=1)
print(open(rep).read())
