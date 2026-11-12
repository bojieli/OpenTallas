"""VL2QC-SC (VISLAYOUT2-QC sub-lane, 11-12): sl_sc family re-floor, positions only (core-shape freeze).

Round 2 measured the sl_sc M3 V shortage as ft wiring (route_supply ablation, s25 tools, edge_outline: skip=ft takes
p99 1.14-1.53 -> 0.72-0.80; skip=ring/glue/station/core leave it >1).  Cause: the planner's ft station chains
zig-zag in y (x_fw_fe_p2 W y842 -> 536 -> 613 -> 865; x_stm_fe 1005 -> 847 -> 985 -> 1018 ...), ~9.5k b of E<->W ft
each making two long V jogs through the open glue and the W-face landing-ring column, while every E<->W window pair
is already aligned (in-pin y ~= out-window y).

Form: every ft slot of the 9 types re-sited with tools/die_plan/ft_corridor.py (straight bundles over the leaf core
on the free M6/M7, register columns in the glue, stations count unchanged = same RTL / schedule, windows/pins/cores
unchanged).  The one W->N slot x_fw_ctl_p1 (L path whose corner column x~478 crosses the core for 514 um > reach)
gets a 4-corner path: W pin row -> column X (W of the core) -> row YTOP (above the core, below the N rings) ->
out-window column -> N face.  Optional core move (--core-dx) shifts u_core W on the 8.64 lattice.

usage: make_sc2.py SRC_TOOLS_DIR BASE.json OUT.json LEDGER.json [--x 319.68] [--ytop 1209.6] [--core-dx 0]"""
import argparse, copy, hashlib, json, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("tools"); ap.add_argument("base"); ap.add_argument("out"); ap.add_argument("ledger")
ap.add_argument("--x", type=float, default=319.68); ap.add_argument("--ytop", type=float, default=1209.6)
ap.add_argument("--core-dx", type=float, default=0.0)
ap.add_argument("--ewjog", type=float, default=None, help="jog x of every E<->W Z slot (over the leaf core: the short V jog legs ride M7 over the core instead of crossing the W-glue N-S bundles)")
ap.add_argument("--band", action="append", default=[], help="slot=lo,hi: corridor band (also for Z slots: the slot is dropped from the jog-lane packing and runs compressed in [lo,hi])")
ap.add_argument("--nsjog", action="append", default=[], help="slot=y: jog y of an N<->S Z slot")
ap.add_argument("--types", default="sle_sc_v1__cl115da35f,sle_sc_v1__cl7479a5ec,sle_sc_v2,sle_sc_v3,slw_sc_v1__cl63e5a7a2,"
                "slw_sc_v1__cl64543eaf__cl4590432d,slw_sc_v1__cl64543eaf__cl5e017c6f,slw_sc_v2,slw_sc_v3")
a = ap.parse_args()
sys.path.insert(0, str(Path(a.tools) / "tools/die_plan")); sys.path.insert(0, a.tools); sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import ft_corridor_sc as FC
S = FC.S
_orig = FC.build_path


def build_path(fin, fout, ca, cb, w, h, jog=None):
    if isinstance(jog, tuple) and S.OPP[fin] != fout:
        X, Y = jog
        ca, cb = np.asarray(ca, float), np.asarray(cb, float)
        assert fin == "W" and fout == "N", (fin, fout)
        return [ca, np.array([X, ca[1]]), np.array([X, Y]), np.array([cb[0], Y]), cb]
    return _orig(fin, fout, ca, cb, w, h, jog)


FC.build_path = build_path
BANDED = {kv.split("=")[0] for kv in a.band}
_jl = FC.jog_lanes


def jog_lanes(ty, pins, w, h, fixed=None):
    r = _jl(ty, pins, w, h, fixed)
    return {k: v for k, v in r.items() if k not in BANDED}


FC.jog_lanes = jog_lanes
raw = open(a.base, "rb").read()
p = json.loads(raw)
types = a.types.split(",")
G = 8.64
core_edits = []
if a.core_dx:
    for tn in types:
        c = p["partition_types"][tn]["hard_cores"][0]
        x0, y0 = c["origin_um"]; nx = round(x0 - a.core_dx, 4)
        assert abs(nx / G - round(nx / G)) < 1e-6
        c["origin_um"] = [nx, y0]; core_edits.append(dict(type=tn, inst=c["inst"], was=[x0, y0], now=[nx, y0]))
jogs = {f"{tn}/x_fw_ctl_p1": (a.x, a.ytop) for tn in types}
for tn in types:
    for f in p["partition_types"][tn]["ft_slots"]:
        if a.ewjog is not None and {f["in_face"], f["out_face"]} == {"E", "W"}:
            jogs[f"{tn}/{f['name']}"] = a.ewjog
    for kv in a.nsjog:
        k, v = kv.split("=")
        jogs[f"{tn}/{k}"] = float(v)
failed = []
model = S.Plan(p) if False else None
bands = {}
for tn in types:
    for kv in a.band:
        k, v = kv.split("=")
        bands[f"{tn}/{k}"] = tuple(float(x) for x in v.split(","))
led = FC.place(p, types, jogs=jogs, bands=bands, failed=failed)
out = json.dumps(p, indent=1)
open(a.out, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()
json.dump(dict(base_sha256=hashlib.sha256(raw).hexdigest(), plan_sha256=sha, x=a.x, ytop=a.ytop, core_dx=a.core_dx, ewjog=a.ewjog, nsjog=a.nsjog, band=a.band,
               core_edits=core_edits, failed=failed, ft=led), open(a.ledger, "w"), indent=1)
print("FAILED", failed); print("sha256", sha[:12])
