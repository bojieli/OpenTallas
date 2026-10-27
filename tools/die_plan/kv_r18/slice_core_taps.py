#!/usr/bin/env python3
"""CLOCK-KV-R18 task 4: partition clock trees END at the KV core slice entries (12.8a, plan 1814a2d8, KV-CORE-SLICE-1).

For every hard core of every partition type, the partition tree gets one leaf tap (plan clock.taps[], kind 'core',
name '<inst>.<pin>') placed exactly on the core's NATIVE clock pin, which must be the single die-clock pin of the core
view within --tol of the slice entry (entries.json; absent -> core centre on the 4.32 lattice, master_plan.core_entry).
No pin is invented and no entry is moved: a core whose view has no such pin (head eighths: per-tile face clk pins, out
of the slice; PHY cores: ck_phy domain, not the die clock) gets NO tap and is listed with the reason, so master_plan
clock_entry still FAILs it honestly.  clock.core_taps is NOT set to 'early', so the die clock taps (die_clock.plan_taps)
are unchanged: no die routing change.  insertion_ps = the plan common core latency (12.3 250 TT), no early offset.
usage: slice_core_taps.py PLAN.json ENTRIES.json OUT_PLAN.json OUT_REPORT.json [--tol 0.5]"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

DIE_CLK = re.compile(r"^(ck|clk|[A-Za-z0-9_]*__clk|s\d+__clk)(\[\w+\])?$")
NOT_DIE = re.compile(r"ck_phy|phy_clk|clk_phy")


def snap(v, g=4.32):
    return round(round(v / g) * g, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("entries"); ap.add_argument("out_plan"); ap.add_argument("out_report")
    ap.add_argument("--tol", type=float, default=0.5)
    ap.add_argument("--phy-landed", action="store_true", help="CLOCK-KV-R19: PHY-domain cores get a kind 'landed' "
                    "forwarded-clock entry tap on their native PHY clock pin (RULING CLOCK-KV-R18)")
    a = ap.parse_args()
    src = Path(a.plan)
    raw = src.read_bytes()
    P = json.loads(raw)
    E = json.loads(Path(a.entries).read_text())
    common = float(P["clock"]["insertion_ps"])
    rep = dict(lane="CLOCK-KV-R18", plan=str(src), plan_sha256=hashlib.sha256(raw).hexdigest(), tol_um=a.tol,
               rule=__doc__, tapped=[], untapped=[], types={})
    for tn, t in P["partition_types"].items():
        hcs = t.get("hard_cores") or []
        if not hcs:
            continue
        ck = t.setdefault("clock", {})
        old = [tp for tp in ck.get("taps", []) or [] if tp.get("kind") == "core"]
        if old:
            raise SystemExit(f"{tn}: already has {len(old)} core taps (refusing to overwrite)")
        new = []
        for h in hcs:
            pins = list(h.get("pins") or [])
            if h.get("pins_file"):
                d = json.loads((src.parent / h["pins_file"]).read_text())
                pins += d.get("pins", []) if isinstance(d, dict) else d
            w, hh = h["outline_um"]
            e = (E.get(h["module"]) or {}).get("xy") or [snap(w / 2), snap(hh / 2)]
            cand = []
            for p in pins:
                nm = p.get("name", "")
                if not DIE_CLK.match(nm) or NOT_DIE.search(nm):
                    continue
                xy = p.get("xy") or [p.get("x"), p.get("y")]
                d = abs(xy[0] - e[0]) + abs(xy[1] - e[1])
                cand.append((d, nm, xy))
            near = sorted(c for c in cand if c[0] <= a.tol)
            row = dict(type=tn, inst=h["inst"], module=h["module"], entry_um=e, clock_pins=len(cand))
            phyp = [p for p in pins if NOT_DIE.search(p.get("name", ""))]
            if not near and not cand and phyp and a.phy_landed:
                # CLOCK-KV-R19 (RULING CLOCK-KV-R18): a PHY-domain core is NOT a die-clock sink.  Its clock entry is a
                # LANDED crossing with a forwarded clock: the plan tap sits on the native PHY clock pin, kind 'landed',
                # clock_domain = that pin; the die clock tree does not tap it (die_clock.plan_taps reads kind 'core'
                # only) and the data crossing into the die clock is the landed CDC (qkd_hr_cdc_*).
                if len(phyp) != 1:
                    raise SystemExit(f"{h['inst']}: {len(phyp)} PHY clock pins, expected exactly one")
                p0 = phyp[0]
                xy = p0.get("xy") or [p0.get("x"), p0.get("y")]
                ox, oy = h["origin_um"]
                tx, ty = (h.get("track_offset_um") or [0.0, 0.0])
                o = h.get("orient", "R0")
                x, y = {"R0": (xy[0], xy[1]), "MX": (xy[0], hh - xy[1]), "MY": (w - xy[0], xy[1]),
                        "R180": (w - xy[0], hh - xy[1])}[o]
                new.append(dict(name=f"{h['inst']}.{p0['name']}", kind="landed", clock_domain=p0["name"],
                                forwarded=True, xy=[round(ox + tx + x, 4), round(oy + ty + y, 4)],
                                budget_owner=h["module"],
                                note="CLOCK-KV-R19: landed crossing, PHY forwarded clock on the native pin; "
                                     "not a die-clock sink (no die tap, no die latency)"))
                rep.setdefault("landed", []).append(dict(row, pin=p0["name"], reason="PHY domain: landed crossing, "
                                                         "forwarded clock"))
                continue
            if not near:
                phy = [p.get("name") for p in pins if NOT_DIE.search(p.get("name", ""))]
                row["reason"] = ("PHY clock domain only (" + ",".join(phy[:2]) + "), no die clock pin" if phy and not cand
                                 else f"no die clock pin within {a.tol} um of the slice entry "
                                      f"({len(cand)} clock pins, nearest {min(c[0] for c in cand):.2f} um)" if cand
                                 else "no clock pin in the core view")
                rep["untapped"].append(row)
                continue
            d, nm, xy = near[0]
            ox, oy = h["origin_um"]
            tx, ty = (h.get("track_offset_um") or [0.0, 0.0])
            o = h.get("orient", "R0")
            x, y = {"R0": (xy[0], xy[1]), "MX": (xy[0], hh - xy[1]), "MY": (w - xy[0], xy[1]),
                    "R180": (w - xy[0], hh - xy[1])}[o]
            tap = dict(name=f"{h['inst']}.{nm}", kind="core", xy=[round(ox + tx + x, 4), round(oy + ty + y, 4)],
                       insertion_ps=common, budget_owner=h["module"],
                       note=f"CLOCK-KV-R18: partition tree leaf at the 12.8a slice entry = native pin {nm}")
            if len(near) > 1:
                tap["note"] += f"; {len(near) - 1} more clock pin(s) of this core in the same entry island " \
                               f"({', '.join(c[1] for c in near[1:])}, <= {near[-1][0]:.3f} um)"
            new.append(tap)
            rep["tapped"].append(dict(row, pin=nm, pin_to_entry_um=round(d, 4), extra_pins=[c[1] for c in near[1:]]))
        if new:
            ck["taps"] = list(ck.get("taps", []) or []) + new
        rep["types"][tn] = dict(cores=len(hcs), taps=len(new))
    out = json.dumps(P, indent=1)
    Path(a.out_plan).write_text(out)
    rep["out_plan_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    rep["summary"] = dict(cores=len(rep["tapped"]) + len(rep["untapped"]) + len(rep.get("landed", [])),
                          tapped=len(rep["tapped"]), landed=len(rep.get("landed", [])), untapped=len(rep["untapped"]))
    Path(a.out_report).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep["summary"]), rep["out_plan_sha256"][:8])


if __name__ == "__main__":
    sys.exit(main())
