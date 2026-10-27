#!/usr/bin/env python3
"""HBM-MU-QUAD-5 delta B2 (COORD 04:04 RULING HBM-EP-ROUTE-1 (a), GEOM-19 04:16 (2a)+(3)): hfd_ep_static re-pin.
 - sd_rx/sd_tx (1024) + the S part of rx_pin_flit (426) leave the S face (they sat over the lower SRAM pair, M2-M4
   blocked, M5 ceiling -> GRT overflow 64,245) and go to the E face beside the 44-um E std-cell strip, joining
   tx_frame + the E part of rx_pin_flit; spread evenly over the free E tracks (face use <= 0.6).
 - the centre clock pin goes onto the M5 track: (125.304, 185.76) inside the plan entry island (DRT-0421 fix).
 Mirrored instances (MY partitions) see E as die-W; core_faces is re-run afterwards (fix_g0c A4).
 Usage: fix_ep.py IN OUT"""
import json, sys, re, shutil, hashlib
from pathlib import Path
PITCH, OFF, INSET, END, TRK = 0.048, 0.024, 0.019, 8.64, 0.6
src, out = Path(sys.argv[1]), Path(sys.argv[2])
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out, symlinks=True)
raw = json.loads((out / "die_plan.json").read_text())
files = sorted({h["pins_file"] for t in raw["partition_types"].values() for h in t.get("hard_cores", []) if h["module"] == "hfd_ep_static"})
rep = {}
CLK = (125.304, 185.76)
for f in files:
    ps = json.loads((out / f).read_text()); w, h = 250.56, 375.84
    lf = lambda p: min([(p["x"], "W"), (w - p["x"], "E"), (p["y"], "S"), (h - p["y"], "N")])[1]  # noqa: E731
    mv = [p for p in ps if lf(p) == "S" and re.sub(r"\[\d+\]$", "", p["name"]) in ("sd_rx", "sd_tx", "rx_pin_flit")]
    for p in ps:
        if p["name"] == "clk":
            p.update(layer="M5", x=CLK[0], y=CLK[1])
    r = dict(moved=len(mv))
    if mv:
        onE = [p for p in ps if lf(p) == "E" and p not in mv]
        cap = int(TRK * int((h - 2 * END) / PITCH))
        assert len(onE) + len(mv) <= cap, (f, len(onE), len(mv), cap)
        # re-spread the whole E face (old E pins + moved) evenly, keeping bus order: tx_frame, rx_pin_flit, sd_tx, sd_rx
        order = {"tx_frame": 0, "rx_pin_flit": 1, "sd_tx": 2, "sd_rx": 3}

        def key(p):
            b = re.sub(r"\[\d+\]$", "", p["name"]); m = re.search(r"\[(\d+)\]$", p["name"])
            return (order.get(b, 9), b, int(m.group(1)) if m else -1)
        allE = sorted(onE + mv, key=key)
        lo, hi = END, h - END; n = len(allE)
        used = set()
        for i, p in enumerate(allE):
            k = round((lo + (i + .5) * (hi - lo) / n - OFF) / PITCH)
            while k in used:
                k += 1
            used.add(k)
            p.update(layer="M4", x=round(w - INSET, 6), y=round(OFF + k * PITCH, 6))
        r.update(E_pins=n, E_cap=cap, E_use=round(n / int((h - 2 * END) / PITCH), 3))
    r["S_left"] = sum(1 for p in ps if lf(p) == "S")
    (out / f).write_text(json.dumps(ps) + "\n"); rep[f] = r
for t in raw["partition_types"].values():
    for hc in t.get("hard_cores", []):
        if hc["module"] == "hfd_ep_static":
            hc["note"] = hc.get("note", "") + " | QUAD-5 B2: SerDes sd_tx/sd_rx + rx_pin_flit off the S face (SRAM column) onto E; clk M5 (125.304,185.76) on track"
(out / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
print(json.dumps(rep)); print("sha", hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest()[:12])
