import sys,json,collections
from pathlib import Path
WT="/srv/opentallas-scratch2/claude/wt/die-hbm-49"
sys.path.insert(0,WT+"/tools/die_plan")
import kit_contract as K, check as C, schema as S
PD="/srv/opentallas-scratch2/claude/die-hbm-48/plan/d44g"
CM=json.load(open("/srv/opentallas-scratch2/claude/die-hbm-48/kits/plan_d44f_cm/core_macros.json"))
CE=json.load(open(PD+"/clock_entries.json"))
P=S.Plan(json.load(open(PD+"/die_plan.json")))
def ent(mod):
    out=set()
    for tn,t in P.types.items():
        for c in t.get("hard_cores",[]) or []:
            if c.get("module")==mod:
                e=(CE.get(tn) or {}).get(c.get("inst")) or (CE.get(tn) or {}).get(__import__("re").sub(r"__q\d+$","",c.get("inst") or ""))
                out.add((tn,c.get("inst"),json.dumps(e)[:160] if e else None))
    return out
for kd in sys.argv[1:]:
    kd=Path(kd); cfg=K._mk(kd); mod=cfg["DESIGN_NAME"]
    print("==",kd.name, "core",K._core(kd),"halo",cfg.get("MACRO_PLACE_HALO"),"MPT",cfg.get("MACRO_PLACEMENT_TCL"))
    pins=json.load(open(kd/"pins.json"))
    ps=pins if isinstance(pins,list) else pins.get("pins",pins)
    print(" pins type",type(ps), (ps[0] if isinstance(ps,list) else list(ps.items())[:1]))
    print(" islands",K._island_rects(kd)[:6])
    try: print(" clkgeo",K.clock_pin_geometry(kd)[1].get("entries",[])[:6])
    except Exception as e: print(" clkgeo err",e)
    es=ent(mod); print(" plan entries n",len(es)); 
    for e in sorted(es,key=str)[:4]: print("  ",e)
    e=CM["cores"].get(mod,{}); print(" cm",e.get("status"),len(e.get("macros",[]) or []),e.get("outline_um"),str(e.get("basis"))[:60])
