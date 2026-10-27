#!/usr/bin/env python3
"""QC-CLK-MESH: ngspice variation sign-off helpers for ONE region mesh deck set (qc_clk_mesh.py --deck-region).
  cells  SRC_CELLS_SP OUT_SP   : BUFx24v = ASAP7 BUFx24_ASAP7_75t_R (extracted, OSDI form) with per-instance
                                 DELVTRAND params dvn / dvp on every n / p device (BSIM-CMG 111 instance variability)
  parse  DECKDIR               : read every sXXX/sim.log .meas, report per sample: tap skew (mesh node at the tap
                                 buffer input, entry after tap buffer + stub) and mesh crossing spread; worst over MC
"""
import json
import re
import sys
from pathlib import Path


def cells(src, out):
    txt = Path(src).read_text().splitlines()
    keep, cur, name = [], None, None
    for ln in txt:
        lo = ln.strip().lower()
        if lo.startswith(".subckt"):
            name = ln.split()[1]
            cur = [ln]
            continue
        if cur is not None:
            cur.append(ln)
            if lo.startswith(".ends"):
                if name == "BUFx24_ASAP7_75t_R" or name.startswith("PM_BUFx24_ASAP7_75t_R%"):
                    keep.append((name, cur))
                cur = None
    o = []
    for nm, bl in keep:
        for i, ln in enumerate(bl):
            if nm == "BUFx24_ASAP7_75t_R":
                if i == 0:
                    ln = ln.replace("BUFx24_ASAP7_75t_R", "BUFx24v") + " dvn=0 dvp=0"
                elif ln[:1] == "N":
                    ln += " DELVTRAND={dvp}" if " pmos" in ln else " DELVTRAND={dvn}"
            o.append(ln)
    Path(out).write_text("\n".join(o) + "\n")
    print("BUFx24v blocks", len(keep), "devices", sum(1 for x in o if x[:1] == "N"))


def parse(d):
    d = Path(d)
    meta = json.loads((d / "meta.json").read_text())
    res = []
    for s in sorted(d.glob("s[0-9][0-9][0-9]")):
        f = s / "sim.log"
        if not f.exists():
            continue
        v = {}
        for m in re.finditer(r"^(t[me]\d+|x\d+_\d+)\s*=\s*([-+0-9.eE]+)", f.read_text(), re.M):
            v[m.group(1)] = float(m.group(2)) * 1e12
        tm = [x for k, x in v.items() if k.startswith("tm")]
        te = [x for k, x in v.items() if k.startswith("te")]
        xc = [x for k, x in v.items() if k.startswith("x")]
        if not tm:
            res.append(dict(sample=s.name, error="no meas"))
            continue
        res.append(dict(sample=s.name, n_tm=len(tm), n_x=len(xc),
                        mesh_at_taps=dict(min=min(tm), max=max(tm), skew=max(tm) - min(tm)),
                        entries=dict(min=min(te), max=max(te), skew=max(te) - min(te)),
                        crossings=dict(min=min(xc), max=max(xc), spread=max(xc) - min(xc)) if xc else None))
    ok = [r for r in res if "error" not in r]
    summ = dict(meta={k: meta[k] for k in meta if k != "taps_parts"}, samples=len(ok), errors=len(res) - len(ok))
    if ok:
        summ["worst_tap_mesh_skew_ps"] = max(r["mesh_at_taps"]["skew"] for r in ok)
        summ["worst_entry_skew_ps"] = max(r["entries"]["skew"] for r in ok)
        summ["worst_crossing_spread_ps"] = max(r["crossings"]["spread"] for r in ok if r["crossings"])
        nom = [r for r in ok if r["sample"] == "s000"]
        summ["nominal"] = nom[0] if nom else None
        # global shift across samples (common to all pairs, not skew)
        summ["entry_mean_range_ps"] = [min(r["entries"]["min"] for r in ok), max(r["entries"]["max"] for r in ok)]
    out = dict(summary=summ, samples=res)
    (d / "mc_result.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    {"cells": lambda: cells(sys.argv[2], sys.argv[3]), "parse": lambda: parse(sys.argv[2])}[sys.argv[1]]()
