#!/usr/bin/env python3
"""Prepare an opt-in SerDes shore-band plan delta; never edits the input plan.

The explicit bottom replaces the historical highest-face-window heuristic.
Existing PMA/SRAM masters retain their outlines and all logical interfaces.
Outputs expected-before rows plus a candidate plan and tap delta for binding.
The tap delta is geometry only: a successor die clock proof remains required.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def band(t, bottom, guard=63.64):
    w, h = t["outline_um"]
    if not 0 < bottom < h - guard:
        raise ValueError("shore bottom must leave positive core and PHY bands")
    for s in t.get("ft_slots", []):
        for f, k in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if s.get(f) == "N" or (s.get(f) in ("W", "E") and s[k][1] > bottom + 1e-6):
                raise ValueError("shore band overlaps a face window")
    for b in t.get("buses", []):
        if b["face"] == "N" or (b["face"] in ("W", "E") and b["window_um"][1] > bottom + 1e-6):
            raise ValueError("shore band overlaps a bus window")
    ly = round(bottom + guard, 4)
    return [0, bottom, w, h], [guard, ly], [round(w-2*guard, 4), round(h-ly, 4)], [0, 0, w, bottom]


def to_die(P, inst, rect):
    p = P.parts[inst]
    ox, oy = p["origin_um"]
    w, h = P.types[p["type"]]["outline_um"]
    f = {"R0": lambda x,y:(ox+x,oy+y), "MX":lambda x,y:(ox+x,oy+h-y),
         "MY":lambda x,y:(ox+w-x,oy+y), "R180":lambda x,y:(ox+w-x,oy+h-y)}[p.get("orient","R0")]
    a,b = f(*rect[:2]), f(*rect[2:])
    return [round(min(a[0],b[0]),4),round(min(a[1],b[1]),4),round(max(a[0],b[0]),4),round(max(a[1],b[1]),4)]


def prepare(plan, src, names, bottom, helpers):
    before = copy.deepcopy(plan)
    pma = module(helpers / "delta_pma_views_1031.py")
    kp4 = module(helpers / "delta_kp4_srams_1031.py")
    P0 = S.Plan(before, str(src))
    details = []
    for tn in names:
        t = plan["partition_types"][tn]
        ko, lo, wh, strip = band(t, bottom)
        phy = [c for c in t["contents"] if c.get("module") == "ot_pdie_serdes"]
        if len(phy) != 1:
            raise ValueError(f"{tn}: exactly one PHY lot required")
        c = phy[0]
        old_parts = {q["physical_master"]:copy.deepcopy(q) for q in c["physical_parts"]}
        need = {q[1] for q in pma.LEAVES} | {q[1] for q in kp4.LEAVES}
        if not need <= old_parts.keys():
            raise ValueError(f"{tn}: missing PMA/SRAM pair")
        c["origin_um"],c["outline_um"] = lo,wh
        t["clock"]["keepouts_um"] = [ko]
        got = pma.place(lo, wh)
        if got is None or got[2] is None:
            raise ValueError(f"{tn}: PMA pair cannot fit")
        x,yt,yr = got
        for master,y in ((pma.LEAVES[0][1],yt),(pma.LEAVES[1][1],yr)):
            q = next(q for q in c["physical_parts"] if q["physical_master"] == master)
            q["origin_um"] = [x,y]
        P = S.Plan(plan, str(src))
        taps = [(x,y) for _,x,y in S.tap_grid(P,tn)]
        got = kp4.place(t,taps)
        fallback = False
        if got is None:
            got = kp4.place(t,taps,ft_bands=False)
            fallback = True
        if got is None:
            raise ValueError(f"{tn}: no legal decoder SRAM pair site")
        for inst,master,w,x,y in got:
            q = next(q for q in c["physical_parts"] if q["physical_master"] == master)
            q["origin_um"] = [x,y]
        # Preserve all clock CDC metadata; only the physically moved PMA clock pin changes.
        rx = next(q for q in c["physical_parts"] if q["physical_master"] == "ot_s81_pma_rxm")
        pin = kp4.rck_pad_clock(P,t,rx,c["physical_parts"])["pins"][0]
        existing = next(p for p in t["clock"]["pad_clock"]["pins"] if p["name"] == "io_pma_rck")
        existing["xy_um"] = pin["xy_um"]
        lot = [*lo,round(lo[0]+wh[0],4),round(lo[1]+wh[1],4)]
        insts = []
        for inst,p in P.parts.items():
            if p["type"] != tn: continue
            domains = [q for q in plan["die"]["pg"]["domains"] if q["name"] == f"phy_{inst}"]
            ios = [q for q in plan["die"]["io"] if q["name"] == f"io_{inst}_u_phy"]
            if len(domains) != 1 or len(ios) != 1:
                raise ValueError(f"{inst}: unambiguous domain/io required")
            d,io = domains[0],ios[0]
            d["rect_um"], d["phy_macro_um"] = to_die(P,inst,ko),to_die(P,inst,lot)
            d["bumps"]["rect_um"] = list(d["phy_macro_um"])
            d["core_strip_um"] = [to_die(P,inst,strip)]
            io["rect_um"] = list(d["phy_macro_um"])
            io["sites"] = math.floor(wh[0]/150)*math.floor(wh[1]/150)
            insts.append(inst)
        oldt = {n:[x,y] for n,x,y in S.tap_grid(P0,tn)}
        newt = {n:[x,y] for n,x,y in S.tap_grid(P,tn)}
        details.append(dict(type=tn,instances=insts,keepout_before=before["partition_types"][tn]["clock"]["keepouts_um"],keepout_after=[ko],sram_ft_fallback=fallback,
                            macro_positions={q["physical_master"]:q["origin_um"] for q in c["physical_parts"]},
                            tap_changes=[dict(name=n,before=oldt.get(n),after=newt.get(n)) for n in sorted(oldt.keys()|newt.keys()) if oldt.get(n)!=newt.get(n)]))
        for q in c["physical_parts"]:
            assert q["outline_um"] == old_parts[q["physical_master"]]["outline_um"]
        for k in ("outline_um","ports","pins","buses","ft_slots","internal_stations","hard_cores"):
            assert t.get(k)==before["partition_types"][tn].get(k),(tn,k)
    assert plan["lanes"] == before["lanes"] and plan["latency"] == before["latency"]
    patches=[]
    def diff(a,b,path):
        if a==b:return
        if isinstance(a,dict) and isinstance(b,dict) and a.keys()==b.keys():
            for k in a:diff(a[k],b[k],path+[k])
        elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
            for i,(x,y) in enumerate(zip(a,b)):diff(x,y,path+[i])
        else:patches.append(dict(op="replace",path=path,before=a,after=b))
    diff(before,plan,[])
    return dict(schema="opentallas.serdes_shore_delta.v1",bottom_um=bottom,cycles_added=0,patches=patches,types=details,
                status="GEOMETRY_CANDIDATE_NEEDS_BIND_AND_SUCCESSOR_CLOCK_PROOF")


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument("plan",type=Path);a.add_argument("output",type=Path);a.add_argument("rows",type=Path)
    a.add_argument("--helpers",type=Path,required=True);a.add_argument("--types",required=True)
    a.add_argument("--shore-bottom-um",type=float,required=True)
    x=a.parse_args()
    if x.output.exists() or x.rows.exists():raise SystemExit("refuse overwrite of candidate evidence")
    p=json.loads(x.plan.read_text());r=prepare(p,x.plan,x.types.split(","),x.shore_bottom_um,x.helpers)
    errs=S.validate(p)
    if errs:raise SystemExit(f"schema errors: {errs[:5]}")
    x.output.write_text(json.dumps(p,indent=1)+"\n")
    r["plan_in_sha256"]=hashlib.sha256(x.plan.read_bytes()).hexdigest();r["plan_out_sha256"]=hashlib.sha256(x.output.read_bytes()).hexdigest()
    x.rows.write_text(json.dumps(r,indent=1)+"\n")
    print(json.dumps({"patches":len(r["patches"]),"types":r["types"],"output":str(x.output)}))

if __name__=="__main__":main()
