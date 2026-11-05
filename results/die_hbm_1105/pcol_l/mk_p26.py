#!/usr/bin/env python3
"""HBM part 26: pcol_l north pin block moves over the central routing channel (x +101.52). mk_p26.py PLAN_DIR
The block sat over the west macro column, where M2/M3/M4 are blocked: GRT-0116. South pins and clk already sit at x 129."""
import json,sys,pathlib
pd=pathlib.Path(sys.argv[1]); M="ot_hbm_su_pcol_l"; OLD="cores/ot_hbm_su_pcol_l__257.04x423.36__d44v_split.json"; NEW="cores/ot_hbm_su_pcol_l__257.04x423.36__p26.json"; DX=101.52; H=423.36
T=json.load(open(pd/OLD)); n=0
for p in T:
    if H-p["y"]<1.5 and p["layer"]=="M5": p["x"]=round(p["x"]+DX,3); n+=1
(pd/NEW).write_text(json.dumps(T))
D=json.load(open(pd/"die_plan.json")); c=0
for k,t in D["partition_types"].items():
    for h in t.get("hard_cores",[]):
        if h.get("module")==M and h.get("pins_file")==OLD: h["pins_file"]=NEW; c+=1
(pd/"die_plan.json").write_text(json.dumps(D,indent=1)+"\n")
(pd/"part26_event.json").write_text(json.dumps(dict(schema="opentallas.hbm_plan_event.part26",module=M,pins_moved=n,dx_um=DX,rows=c,pins_file=NEW)))
print("part 26 pins",n,"rows",c,"x range",min(p["x"] for p in T if H-p["y"]<1.5),max(p["x"] for p in T if H-p["y"]<1.5))
