#!/usr/bin/env python3
"""DS85 CLKDIE-S81 (DO_NOT_COUNT): parse one type's type_clk.tcl output (arr_<C>.txt) into per-ring / per-fclk_out
insertion delays.

Decoding (type_clk.tcl): clock port i launches its source RISE at OFF*i and its FALL at OFF*i+HALF, as data from a
virtual clock, so a pin arrival a decodes to port i = floor(a / OFF) and source edge rise if (a mod OFF) < HALF.  The
source-RISE-derived insertion of a pin is a - OFF*i, taken from whichever of the pin's rise / fall arrivals decodes
to a rise edge (an inverting clock path shows the source rise on the pin's fall arrival).

Output JSON: {corner: {rings: {bus: {write: {port, n, min, max, mean}, read: {...}, other: [...]}},
                       fclk_out: {bus: {port, late, early}}}}
"""
import json
import re
import statistics
import sys
from pathlib import Path

INF = float("inf")


def decode(a, off, half, ports):
    if a is None or a != a or abs(a) > 1e12:
        return None
    i = int(a // off)
    r = a - i * off
    if i < 1 or i > len(ports):
        return None
    return ports[i - 1], ("rise" if r < half else "fall"), (r if r < half else r - half)


def parse(path):
    off = half = None
    ports, regs, outs, top, corner = [], [], [], None, None
    for ln in Path(path).read_text().splitlines():
        x = ln.split()
        if not x:
            continue
        if x[0] == "#":
            m = re.search(r"corner (\S+) top (\S+) off (\S+) half (\S+)", ln)
            corner, top, off, half = m.group(1), m.group(2), float(m.group(3)), float(m.group(4))
        elif x[0] == "P":
            ports.append(re.sub(r"\[0\]$", "", x[2]))   # OpenROAD read_db names a 1-bit bus port "<p>[0]"
        elif x[0] == "R":
            regs.append((x[1], x[2], *[float(v) for v in x[3:7]]))
        elif x[0] == "O":
            outs.append((x[1], *[float(v) for v in x[2:6]]))
    return dict(corner=corner, top=top, off=off, half=half, ports=ports, regs=regs, outs=outs)


def rise_ins(rmax, fmax, off, half, ports):
    """(port, insertion of the source rise) from a pin's rise/fall max arrivals"""
    for a in (rmax, fmax):
        d = decode(a, off, half, ports)
        if d and d[1] == "rise":
            return d[0], d[2]
    return None


def stats(v):
    return dict(n=len(v), min=round(min(v), 2), max=round(max(v), 2), mean=round(statistics.fmean(v), 2)) if v else None


def summarise(path):
    p = parse(path)
    off, half, ports = p["off"], p["half"], p["ports"]
    rings = {}
    undecoded = 0
    for cell, nm, rmax, rmin, fmax, fmin in p["regs"]:
        m = re.search(r"(?:^|[./])u_cland_([A-Za-z0-9_]+?)/", nm)
        if not m:
            continue
        bus = m.group(1)
        r = rise_ins(rmax, fmax, off, half, ports)
        if r is None:
            undecoded += 1
            continue
        port, ins = r
        g = rings.setdefault(bus, {})
        g.setdefault(port, []).append(ins)
    out = {}
    for bus, g in rings.items():
        wport = f"fclk_in_{bus}"
        w = g.get(wport, [])
        rd = [v for k, v in g.items() if k != wport for v in v]
        out[bus] = dict(write=dict(port=wport, **(stats(w) or {"n": 0})),
                        read=dict(ports=sorted(k for k in g if k != wport), **(stats(rd) or {"n": 0})),
                        read_by_port={k: stats(v) for k, v in g.items() if k != wport})
    fo = {}
    for nm, rmax, smin_r, fmax, smin_f in p["outs"]:
        bus = re.sub(r"\[0\]$", "", nm)
        r = rise_ins(rmax, fmax, off, half, ports)
        fo[bus] = None if r is None else dict(port=r[0], ins=round(r[1], 2))
    return dict(corner=p["corner"], top=p["top"], ports=ports, rings=out, fclk_out=fo, undecoded_regs=undecoded)


if __name__ == "__main__":
    d = Path(sys.argv[1])
    res = {}
    for c in ("TT", "FF"):
        f = d / f"arr_{c}.txt"
        if f.is_file() and "DS85_DONE" in (d / f"sta_{c}.log").read_text():
            res[c] = summarise(f)
    (d / "type_clk.json").write_text(json.dumps(res, indent=1) + "\n")
    print(d.name, {c: (len(v["rings"]), len(v["fclk_out"]), v["undecoded_regs"]) for c, v in res.items()})
