#!/usr/bin/env python3
"""S81-SLICE: spread a kit's pins over FULL faces (coordinator tile checklist item 3, memory tile-review-pin-clustering-1017).

Gives every port of a face a disjoint pin range proportional to its bit width, covering the face from INSET to
length - INSET in the spec's face order, and turns on route.pin_balance.  Port widths come from the top module header
(literal [hi:lo] ranges; parameters resolved from the spec's params or the header defaults).  The outline is taken from
the kit (physical/ref_tile/<name>/floorplan.json) after `ref_tile.py gen`, so run: gen -> pin_spread -> gen.

    python3 tools/s81_slice/pin_spread.py tools/ref_tile/specs_s81slice/<kit>.json [--inset 6.48]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def header_ports(src_files, top, params):
    txt = ""
    for f in src_files:
        t = (ROOT / f).read_text(errors="replace")
        if re.search(r"\bmodule\s+%s\b" % re.escape(top), t):
            txt = t
            break
    m = re.search(r"\bmodule\s+%s\s*(#\s*\((.*?)\))?\s*\((.*?)\);" % re.escape(top), txt, re.S)
    if not m:
        raise SystemExit(f"top {top} not found")
    env = {}
    for k, v in re.findall(r"parameter\s+(?:integer\s+)?(\w+)\s*=\s*([^,\n)]+)", m.group(2) or ""):
        env[k] = v.strip()
    env.update({k: str(v) for k, v in params.items()})

    def ev(x):
        for _ in range(4):
            x = re.sub(r"\b([A-Za-z_]\w*)\b", lambda mm: "(" + env[mm.group(1)] + ")" if mm.group(1) in env else mm.group(1), x)
        return int(eval(x, {}, {}))
    w = {}
    body = re.sub(r"//.*", "", m.group(3))
    for decl in re.split(r",(?=\s*(?:input|output|inout)\b)", body):
        mm = re.match(r"\s*(input|output|inout)\s+(?:wire|reg)?\s*(?:signed\s*)?(\[[^\]]+\])?\s*(.*)", decl, re.S)
        if not mm:
            continue
        width = 1
        if mm.group(2):
            hi, lo = mm.group(2)[1:-1].split(":")
            width = abs(ev(hi) - ev(lo)) + 1
        for n in re.split(r"[,\s]+", mm.group(3).strip()):
            n = re.sub(r"\b(input|output|inout|wire|reg)\b", "", n).strip()
            if re.fullmatch(r"[A-Za-z_]\w*", n):
                w[n] = width
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--inset", type=float, default=6.48)
    a = ap.parse_args()
    sp = json.load(open(a.spec))
    fp = json.load(open(ROOT / "physical/ref_tile" / sp["name"] / "floorplan.json"))
    x0, y0, x1, y1 = fp["die"]
    W, H = x1 - x0, y1 - y0
    widths = header_ports(sp["sources"], sp["top"], sp.get("params", {}))
    clk = {sp["clock_port"], *sp.get("reset_ports", [])}
    rng = {}
    for face, ports in sp["pins"].items():
        L = W if face in ("N", "S") else H
        sig = [p for p in ports if p not in clk]
        tot = sum(widths[p] for p in sig) or 1
        span = L - 2 * a.inset
        mn = 2.16                                   # a port range never shorter than one 2.16-um row pitch
        free = span - mn * len(sig)
        if free < 0:
            raise SystemExit(f"face {face}: {len(sig)} ports do not fit {span:.2f} um at {mn} um each")
        pos = a.inset
        for p in sig:
            seg = mn + free * widths[p] / tot
            rng[p] = [round(pos, 3), round(pos + seg, 3)]
            pos += seg
    sp["pin_ranges"] = rng
    sp.setdefault("route", {})["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M3 M5"}
    json.dump(sp, open(a.spec, "w"), indent=2)
    print(f"PIN_SPREAD {sp['name']} outline {W} x {H}: {len(rng)} ranged ports")


if __name__ == "__main__":
    main()
