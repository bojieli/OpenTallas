#!/usr/bin/env python3
"""HBM-GAPS-2 plan pin event gqpin (COORD 11-05 12:00, fallback A for gq_land key c9722): q_hub_nw u_hcollgl_Q__q1 keeps
orient R0 and the o_R0 table, but the 579 ld_* M5 pins on the N face take the x of the signed o_MX table (ac72b, gqac2,
run x 20.33..126.31, which routed DRC 0) instead of x 2.95..71.26, which crowded the NW corner against the 2775 W-face M4 pins
(bfcd kit: DRT 13-35k violations, 99% at x0-20 y160-200). y stays on the N face; W/E M4 pins, fault, clk unchanged.
mk_gqpin.py PLAN_DIR (plain die_plan.json + cores/)."""
import json,sys,gzip
from pathlib import Path
pd=Path(sys.argv[1]); D=json.loads((pd/"die_plan.json").read_text())
B="cores/ot_hgi_coll_gq_land__142.56x207.36__canon__fr15__%s__codex_g21__wspread__centry"
MXF,R0F=B%"o_MX"+".json",B%"o_R0"+".json"; NF=B%"o_R0"+"__gqpin.json"
def pins(f):
    p=pd/f
    return json.loads(p.read_text()) if p.exists() else json.load(gzip.open(str(p)+".gz"))
a={p["name"]:p for p in pins(MXF)}; b=pins(R0F)
T=[]; moved=0
for p in b:
    q=dict(p)
    if p["name"].startswith("ld_") and p["layer"]=="M5" and p["y"]>207:
        m=a[p["name"]]
        if m["layer"]!="M5" or m["y"]>1: raise SystemExit("MX pin not on S M5: "+p["name"])
        q["x"]=m["x"]; moved+=1
    T.append(q)
if moved!=579: raise SystemExit("moved %d"%moved)
xs=[p["x"] for p in T if p["layer"]=="M5" and p["y"]>207]
if len(set(xs))!=len(xs): raise SystemExit("N-face x collision")
(pd/NF).write_text(json.dumps(T))
hit=0
for h in D["partition_types"]["q_hub_nw"]["hard_cores"]:
    if h["inst"]=="u_hcollgl_Q__q1":
        if h["pins_file"]!=R0F or h.get("orient","R0")!="R0": raise SystemExit("q1 not as read")
        h["pins_file"]=NF; h["note"]=h.get("note","")+" | HBM-GAPS-2 gqpin: ld_* N-face M5 run moved to x 20.33..126.31 (signed o_MX run x)"; hit+=1
if hit!=1: raise SystemExit("hits")
(pd/"die_plan.json").write_text(json.dumps(D,indent=1)+"\n")
(pd/"gqpin_event.json").write_text(json.dumps(dict(schema="opentallas.hbm_plan_event.gqpin",type="q_hub_nw",inst="u_hcollgl_Q__q1",
  pins_file_from=R0F,pins_file_to=NF,pins_moved=moved,n_face_x=[min(xs),max(xs)],ruling="COORD 11-05 12:00 (A) fallback")))
print("gqpin moved",moved,"N-face x",min(xs),max(xs),"->",NF)
