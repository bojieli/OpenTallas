import json,hashlib,sys,os
P="/srv/opentallas-scratch2/claude/hbm-vsn-xtap-t39w/plan_t39w/"
OUT="/srv/opentallas-scratch2/claude/hbm-cores-c/g0pins/"
sha=lambda p: hashlib.sha256(open(p,"rb").read()).hexdigest()
def retable(f, x1, x2, y, suffix):
    pins=json.load(open(P+"cores/"+f)); new=[]
    for q in pins:
        q=dict(q)
        if q["name"]=="fifo_clk": q["x"]=x1; q["y"]=y
        if q["name"]=="hbm_clk": q["x"]=x2; q["y"]=y
        new.append(q)
    nf=f.replace(".json","__%s.json"%suffix); json.dump(new,open(OUT+nf,"w"))
    return nf, sha(P+"cores/"+f), sha(OUT+nf), sum(1 for a,b in zip(pins,new) if a!=b), len(pins)
# accepted variant (clk50): pins 50.040 / 50.232, y 64.8; entry xy keeps the original pin-to-xy offset (+0.024, +0.216)
g0=retable("ot_wbq_root_g__216x129.6__d44v_p51.json",50.04,50.232,64.8,"clk50")
g1=retable("ot_wbq_root_g1__216x129.6__vC5.json",50.04,50.232,64.8,"clk50")
# lattice-aligned alternative: entry xy on the 4.32 PG lattice (51.84, 64.8), pins at xy+0.024 / +0.216
a0=retable("ot_wbq_root_g__216x129.6__d44v_p51.json",51.864,52.056,64.8,"clk52")
a1=retable("ot_wbq_root_g1__216x129.6__vC5.json",51.864,52.056,64.8,"clk52")
ce=json.load(open(P+"clock_entries.json"))
d=json.load(open(P+"die_plan.json"))
edits=[]
for t,v in ce.items():
    for inst,r in v.items():
        if r.get("native_module") in ("ot_wbq_root_g0","ot_wbq_root_g1"):
            edits.append(dict(type=t,inst=inst,module=r["native_module"],
              old=dict(xy_um=r["xy_um"],island_um=r["island_um"],clock_pin_sites_um=r["clock_pin_sites_um"]),
              new=dict(xy_um=[50.016,64.8],island_um=[45.696,60.48,54.336,69.12],clock_pin_sites_um={"fifo_clk":[50.04,64.8],"hbm_clk":[50.232,64.8]}),
              alt_lattice=dict(xy_um=[51.84,64.8],island_um=[47.52,60.48,56.16,69.12],clock_pin_sites_um={"fifo_clk":[51.864,64.8],"hbm_clk":[52.056,64.8]})))
pf=[]
for tn,t in d["partition_types"].items():
    for h in t.get("hard_cores") or []:
        if h["module"] in ("ot_wbq_root_g0","ot_wbq_root_g1"):
            old=h["pins_file"]; new=old.replace(".json","__clk50.json"); pf.append(dict(type=tn,inst=h["inst"],module=h["module"],old=old,new=new))
ev={"schema":"opentallas.hbm_plan_event_delta.v1","event":"wbq_root_clkpins_1112","lane":"HBM-CORES-C (DIE-HBM-101)","date":"2026-11-12",
 "NOT_APPLIED":"delta only; DIE-HBM-101 folds it into the HBM event line (head pEv6) and runs G0",
 "base_plan":"plan_t39w die_plan.json sha256 "+sha(P+"die_plan.json")+", clock_entries.json sha256 "+sha(P+"clock_entries.json"),
 "why":"fifo_clk/hbm_clk (interior M5 clock entry pins) sit inside the bottom SRAM macro (kit macro stack x 100.032..191.832, y 14.892..125.268): DRT-0073 / pin-top DRC; the plan entry was authored as 'in the S logic band below the macros' but the Codex vS6 macro geometry leaves 14.9 um.",
 "tables":{"g0":dict(old=g0[0].replace("__clk50","") ,new=g0[0],old_sha256=g0[1],new_sha256=g0[2],rows_changed=g0[3],rows=g0[4]),
           "g1":dict(old=g1[0].replace("__clk50",""),new=g1[0],old_sha256=g1[1],new_sha256=g1[2],rows_changed=g1[3],rows=g1[4])},
 "pins_file_edits":pf,"clock_entries_edits":edits,
 "alt_lattice_tables":{"g0":dict(new=a0[0],new_sha256=a0[2]),"g1":dict(new=a1[0],new_sha256=a1[2])},
 "alt_note":"entry xy 50.016 is not on the 4.32 PG lattice that the 'sub frame' source note names for the old entries (108.0 = 25 x 4.32); the alt variant keeps xy on the lattice (51.84 = 12 x 4.32) with pins +0.024/+0.216 from it",
 "not_verified":"other plan consumers of the clock entry (bind_clock_landings, clock_regions, core_conns clock taps, region tap lists) were not traced; G0 should be run on the folded plan",
 "counts":{"pins_file_edits":len(pf),"clock_entries_edits":len(edits)}}
json.dump(ev,open(OUT+"wbq_root_clkpins_1112_delta.json","w"),indent=1)
rc={"schema":"opentallas.receipt.v1","delta_sha256":sha(OUT+"wbq_root_clkpins_1112_delta.json"),"files":{f:sha(OUT+f) for f in sorted(os.listdir(OUT)) if f.endswith(".json") and not f.startswith("wbq_root_clkpins_1112_receipt")},"generator":"mkclkdelta.py","host":"epyc9","applied_to_a_plan":False}
json.dump(rc,open(OUT+"wbq_root_clkpins_1112_receipt.json","w"),indent=1)
print(ev["counts"],g0[3],g1[3],rc["delta_sha256"][:16])
