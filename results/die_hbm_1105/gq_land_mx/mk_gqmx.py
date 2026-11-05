#!/usr/bin/env python3
"""HBM-GAPS-2 plan event gqmx (COORD 11-05 12:00 ruling B): q_hub_nw u_hcollgl_Q__q1 (ot_hgi_coll_gq_land) takes the
signed o_MX pin table (view ac72b8c34f86, gqac2, already counted) with orient MX, as q_hub_ne u_hcollgl_Q__q1 already does.
Drops the o_R0 table (bfcd846691ef, key c9722, DRT stuck in the NW corner). Same module, same origin, same outline, same
3880 pin names; the clock entry is the core centre and does not move under MX. mk_gqmx.py PLAN_DIR (plain die_plan.json)."""
import json,sys,gzip
from pathlib import Path
pd=Path(sys.argv[1]); D=json.loads((pd/"die_plan.json").read_text())
MXF="cores/ot_hgi_coll_gq_land__142.56x207.36__canon__fr15__o_MX__codex_g21__wspread__centry.json"
R0F="cores/ot_hgi_coll_gq_land__142.56x207.36__canon__fr15__o_R0__codex_g21__wspread__centry.json"
def pins(f):
    p=pd/f
    return json.loads(p.read_text()) if p.exists() else json.load(gzip.open(str(p)+".gz"))
a,b=pins(MXF),pins(R0F)
if sorted(x["name"] for x in a)!=sorted(x["name"] for x in b): raise SystemExit("pin names differ")
ca=[x for x in a if x["name"]=="clk"][0]
if abs(ca["x"]-69.12)>0.1 or abs(ca["y"]-103.68)>0.01: raise SystemExit("clk not at centre")
T=D["partition_types"]["q_hub_nw"]; hit=0
for h in T["hard_cores"]:
    if h["inst"]=="u_hcollgl_Q__q1":
        if h["module"]!="ot_hgi_coll_gq_land" or h["pins_file"]!=R0F or h.get("orient","R0")!="R0": raise SystemExit("q1 not as read")
        ne=[x for x in D["partition_types"]["q_hub_ne"]["hard_cores"] if x["inst"]=="u_hcollgl_Q__q1"][0]
        if ne["pins_file"]!=MXF or ne.get("orient")!="MX" or ne["origin_um"]!=h["origin_um"]: raise SystemExit("ne q1 not as read")
        h["pins_file"]=MXF; h["orient"]="MX"
        h["note"]=h.get("note","")+" | HBM-GAPS-2 gqmx: signed o_MX table (ac72b, gqac2) placed MX, as q_hub_ne q1; o_R0 table c9722 dropped"
        hit+=1
if hit!=1: raise SystemExit("hits %d"%hit)
(pd/"die_plan.json").write_text(json.dumps(D,indent=1)+"\n")
(pd/"gqmx_event.json").write_text(json.dumps(dict(schema="opentallas.hbm_plan_event.gqmx",type="q_hub_nw",inst="u_hcollgl_Q__q1",
  module="ot_hgi_coll_gq_land",pins_file_from=R0F,pins_file_to=MXF,orient_from="R0",orient_to="MX",pins=len(a),
  signed_view="ac72b8c34f86 (gqac2, epyc4 scratch3 die-hbm-66/eco/gqac2/run/i2, routed LEC EQ 13416)",ruling="COORD 11-05 12:00 (B)")))
print("gqmx done: q_hub_nw u_hcollgl_Q__q1 -> o_MX, MX; pins",len(a))
