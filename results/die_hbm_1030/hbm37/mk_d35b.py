#!/usr/bin/env python3
"""DIE-HBM-37: pin-only plan event d35b = d35a + collar_idx256r signed-view pins (COORD RULINGS 2026-10-30 12:03 (1) (A)).

ot_hbm_static_cfg_collar_idx256r (root u_col_idx, 88.992 square, outline/origin unchanged) adopts the 3 pins of the SIGNED
view (hbm-cores-kits-27/collar_s30wl 6_final.def, 6_final.odb sha 93bc75ef):
  * clk    : (88.872, 44.424) face C  -> (43.224, 43.2) M5 face C  (already the plan centre entry, clock_entries u_col_idx
             xy 43.2,43.2 island 38.88-47.52, merged clk+clk_in)
  * clk_in : (0.096, 52.584) W M4    -> (44.664, 43.2) M5 face C  (inside the same island)
  * c_done : the plan already selects c_done__W (pin_select {c_done: c_done__W}, W M4 0.096,52.968) = the view's c_done ->
             c_done takes that position, the N-face c_done (60.696,88.896) and the c_done__W alias are dropped, pin_select removed.
The view's 4 island feedthrough ports (mp_isl0_ck_i/o, mp_isl0_rst_i/o, ft_ports.json) are recorded in a die-owned FT
sidecar (schema opentallas.core_die_owned_ft.v1, as QC vmr) -- not in the core signal pin table.
usage: mk_d35b.py BASE OUT DEF"""
import hashlib, json, re, subprocess, sys
from pathlib import Path

base, out, dv = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
MOD = "ot_hbm_static_cfg_collar_idx256r"
OLD = "cores/ot_hbm_static_cfg_collar_idx256r__86.4x86.4__r5__c20g_88.992x88.992__c20i.json"
NEW = "cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__d35b.json"
SIDE = "cores/ot_hbm_static_cfg_collar_idx256r__88.992x88.992__d35b_die_owned_ft.json"
W = H = 88.992
if out.exists():
    sys.exit(f"{out} exists (refuse to overwrite)")

# --- view pins from the signed DEF
t = dv.read_text()
u = float(re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", t).group(1))
sec = re.search(r"^\s*PINS\s+\d+\s*;(.*?)^\s*END\s+PINS", t, re.S | re.M).group(1)
view = {}
for st in sec.split(";"):
    st = st.strip()
    if not st.startswith("-"):
        continue
    n = st[1:].split()[0].replace("\\", "")
    d = re.search(r"DIRECTION\s+(\S+)", st)
    ly = re.search(r"LAYER\s+(\S+)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", st)
    pl = re.search(r"(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", st)
    if ly and pl:
        x, y = int(pl.group(1)) / u, int(pl.group(2)) / u
        r = [int(ly.group(i)) / u for i in (2, 3, 4, 5)]
        view[n] = dict(layer=ly.group(1), x=x, y=y, dir=d.group(1) if d else None,
                       rect=[round(x + r[0], 4), round(y + r[1], 4), round(x + r[2], 4), round(y + r[3], 4)])

subprocess.check_call(["cp", "-al", str(base), str(out)])


def wnew(rel, obj):
    p = out / rel
    if p.exists() or p.is_symlink():
        p.unlink()
    p.write_text(json.dumps(obj, indent=1) + "\n")


pins = json.load(open(base / OLD))
newp = []
for q in pins:
    q = dict(q)
    b = q["bus"]
    if b == "c_done" and q["face"] == "N":
        continue                       # dropped: plan used c_done__W (pin_select), view has only the W pin
    if b == "c_done__W":
        q["bus"] = "c_done"
        assert abs(q["x"] - view["c_done"]["x"]) < 1e-6 and abs(q["y"] - view["c_done"]["y"]) < 1e-6, q
    elif b in ("clk", "clk_in"):
        v = view[b]
        q.pop("track_note", None)
        q.update(layer=v["layer"], x=round(v["x"], 3), y=round(v["y"], 3), face="C",
                 note="d35b: signed collar_s30wl view position (plan centre clock entry island 38.88-47.52)")
    newp.append(q)
assert len(newp) == len(pins) - 1
wnew(NEW, newp)

ftp = ["mp_isl0_ck_i", "mp_isl0_ck_o", "mp_isl0_rst_i", "mp_isl0_rst_o"]
plan = json.load(open(base / "die_plan.json"))
n = 0
for tn, ty in plan["partition_types"].items():
    for h in ty.get("hard_cores", []):
        if h.get("module") == MOD:
            assert h["pins_file"] == OLD, h["pins_file"]
            h["pins_file"] = NEW
            h.pop("pin_select", None)
            h["note"] = h.get("note", "") + " | DIE-HBM-37 d35b: pins = signed collar_s30wl view (clk/clk_in centre, c_done W); die-owned FT sidecar cores/..__d35b_die_owned_ft.json"
            n += 1
assert n == 1, n
wnew("die_plan.json", plan)
sha = lambda p: hashlib.sha256((out / p).read_bytes()).hexdigest()
side = {
    "schema": "opentallas.core_die_owned_ft.v1",
    "module": MOD,
    "plan": "die_plan.json (HBM d35b)",
    "plan_sha256": sha("die_plan.json"),
    "plan_core_pins": NEW,
    "plan_core_pins_sha256": sha(NEW),
    "outline_um": [W, H],
    "core_signal_pins": len(newp),
    "die_owned_ft_pins": [dict(name=p, direction=view[p]["dir"], layer=view[p]["layer"], rect_um=view[p]["rect"]) for p in ftp],
    "ft_declaration": {"source": "hbm-cores-kits-27/collar_s30wl ft_ports.json (opentallas.ft_ports.v1, sha 74732fab)",
                       "arcs": [{"source": "mp_isl0_ck_i", "sink": "mp_isl0_ck_o", "kind": "clock", "cells": ["mp_isl0_ck0"]},
                                {"source": "mp_isl0_rst_i", "sink": "mp_isl0_rst_o", "kind": "reset", "cells": ["mp_isl0_rst0"]}],
                       "note": "in-core clock/reset island feedthrough of the centre entry; die-owned, not core signal pins"},
    "signed_view": {"def": str(dv), "odb_sha256_prefix": "93bc75ef"},
}
wnew(SIDE, side)
print(json.dumps({"pins_file": NEW, "pins": len(newp), "pins_sha256": sha(NEW), "sidecar": SIDE, "sidecar_sha256": sha(SIDE),
                  "die_plan_sha256": sha("die_plan.json")}, indent=1))
