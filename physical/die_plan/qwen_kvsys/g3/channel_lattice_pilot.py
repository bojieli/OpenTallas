#!/usr/bin/env python3
"""KV-PLAN 10-25: channel-lattice G2 pilot (diagnostic, plan NOT changed).

Structural diagnosis of the centroid G2 FAILs (PV v6 421k / HGI v6 1.28M overflow): every face pin is spread
uniformly from the face origin, i.e. ~70 % of the pins of a hg/hgi/pv face sit in front of a hard core whose
obstruction reaches M7 (signals <= M7).  Those pins can only escape along the 17.28-um strip between the face and
the core row, and the per-slot centroid station sites stack every bit of a slot on one point.

This pilot builds G2 partition probes (tools/die_plan/g2.part_probe, unchanged probe body) with three structural
changes, one at a time, to measure what each buys before the plan is regenerated:
  --pins channel   face pins only in channel mouths (face intervals not covered by a hard core +- --clear um),
                   a straight-through ft bit gets the SAME along-face coordinate on its in and out face (it runs
                   straight down one channel); pin order along the face is kept
  --centre         hard-core lattice centred in the tile (equal margins), so a flipped neighbour has the same
                   channel lattice (MX/MY/R180 instances of hg/hgi keep their channels aligned at the abutment)
  --per-bit        drop the slot centroid sites (regs_um): every bit's stations sit on its own route at
                   <= 405 um (point_at along the bit's route), i.e. per-bit sites in the channel
  --obs-max M7     core obstruction height (KV-405-1: hard cores are hardened to M7)
usage: channel_lattice_pilot.py PLAN TYPE OUTDIR [--pins orig|channel] [--centre] [--per-bit] [--obs-max M7]
"""
import argparse
import copy
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(R / "tools/die_plan"))
import g2  # noqa: E402
import gen_phys  # noqa: E402
import schema as S  # noqa: E402


def free_intervals(spans, L, clear, edge):
    """complement of the core spans (+-clear) inside [edge, L-edge]."""
    sp = sorted((a - clear, b + clear) for a, b in spans)
    out, cur = [], edge
    for a, b in sp:
        if a > cur:
            out.append((cur, min(a, L - edge)))
        cur = max(cur, b)
    if cur < L - edge:
        out.append((cur, L - edge))
    return [(a, b) for a, b in out if b - a > 1.0]


def sites(iv, n):
    """n coordinates spread uniformly (by length) over the intervals."""
    tot = sum(b - a for a, b in iv)
    res = []
    for j in range(n):
        t = (j + 0.5) * tot / n
        for a, b in iv:
            if t <= b - a:
                res.append(a + t)
                break
            t -= b - a
    return res


def remap(t, pins, clear):
    w, h = t["outline_um"]
    cores = [c for c in t.get("hard_cores", []) if "origin_um" in c]
    # along-face spans: E/W faces use y spans, N/S faces x spans (faces see every core row/column: conservative)
    ys = [(c["origin_um"][1], c["origin_um"][1] + c["outline_um"][1]) for c in cores]
    xs = [(c["origin_um"][0], c["origin_um"][0] + c["outline_um"][0]) for c in cores]
    edge = gen_phys.CORE_MARGIN_UM + 1.0
    ivs = {"E": free_intervals(ys, h, clear, edge), "W": free_intervals(ys, h, clear, edge),
           "N": free_intervals(xs, w, clear, edge), "S": free_intervals(xs, w, clear, edge)}
    slots = {s["name"]: s for s in t.get("ft_slots", [])}
    by = {}
    for p in pins:
        by.setdefault(p[5], []).append(p)
    new = {}
    for axis, (fa, fb) in (("EW", ("E", "W")), ("NS", ("N", "S"))):
        # items: ('thru', key) occupy a site on both faces; singles occupy one face
        thru, single = {}, {fa: [], fb: []}
        for f in (fa, fb):
            for p in by.get(f, []):
                bus, bit = p[0], p[1]
                sn = bus[:-2] if bus[-2:] in ("_i", "_o") else None
                s = slots.get(sn)
                if s and {s["in_face"], s["out_face"]} == {fa, fb}:
                    thru.setdefault((sn, bit), []).append(p)
                else:
                    single[f].append(p)
        ca = lambda p: p[4] if axis == "EW" else p[3]  # noqa: E731
        items = sorted(thru.items(), key=lambda kv: sum(ca(p) for p in kv[1]) / len(kv[1]))
        n = max(len(items) + len(single[fa]), len(items) + len(single[fb]))
        st = sites(ivs[fa], n) if n else []
        used = set()
        nt = len(items)
        for k, (key, ps) in enumerate(items):
            idx = min(n - 1, int(round((k + 0.5) * n / max(nt, 1) - 0.5)))
            while idx in used:
                idx = (idx + 1) % n
            used.add(idx)
            for p in ps:
                new[(p[0], p[1])] = st[idx]
        free = [i for i in range(n) if i not in used]
        for f in (fa, fb):
            for p, i in zip(sorted(single[f], key=ca), free):
                new[(p[0], p[1])] = st[i]
    out = []
    for p in pins:
        bus, bit, ln, x, y, f = p
        c = new.get((bus, bit))
        if c is None:
            out.append(p)
        elif f in "EW":
            out.append((bus, bit, ln, x, round(c, 4), f))
        else:
            out.append((bus, bit, ln, round(c, 4), y, f))
    return out, ivs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("type")
    ap.add_argument("out")
    ap.add_argument("--pins", choices=("orig", "channel"), default="orig")
    ap.add_argument("--centre", action="store_true")
    ap.add_argument("--per-bit", action="store_true")
    ap.add_argument("--obs-max", default="M7")
    ap.add_argument("--clear", type=float, default=4.0)
    ap.add_argument("--adjust", type=float, default=0.5)
    ap.add_argument("--mem", type=int, default=24)
    a = ap.parse_args()
    raw = S.load(a.plan)
    P = S.Plan(raw, Path(a.plan).resolve())
    t = P.types[a.type]
    orig_pins = gen_phys.type_pins(P, a.type)
    t2 = copy.deepcopy(t)
    if a.centre:
        cs = [c for c in t2["hard_cores"] if "origin_um" in c]
        w, h = t2["outline_um"]
        x0 = min(c["origin_um"][0] for c in cs)
        x1 = max(c["origin_um"][0] + c["outline_um"][0] for c in cs)
        y0 = min(c["origin_um"][1] for c in cs)
        y1 = max(c["origin_um"][1] + c["outline_um"][1] for c in cs)
        dx = round(((w - x1) - x0) / 2 / 0.54) * 0.54
        dy = 0.0   # rows keep the hg row lattice (17.28 + 319.68 k): symmetric under MX already
        for c in t2["hard_cores"]:
            c["origin_um"] = [c["origin_um"][0] + dx, c["origin_um"][1] + dy]
        for c in t2.get("contents", []):
            if "origin_um" in c and any(c["inst"] == k["inst"] for k in cs):
                c["origin_um"] = [c["origin_um"][0] + dx, c["origin_um"][1] + dy]
    for c in t2.get("hard_cores", []):
        c["obs_max"] = a.obs_max
    for c in t2.get("contents", []):
        if "outline_um" in c:
            c["obs_max"] = a.obs_max
    if a.per_bit:
        for s in t2.get("ft_slots", []):
            for k in ("regs_um", "bit_sites_um", "bit_site_cell_um"):
                s.pop(k, None)
    pins, ivs = (remap(t2, orig_pins, a.clear) if a.pins == "channel" else (orig_pins, None))
    P.types[a.type] = t2
    gen_phys.type_pins = lambda P_, tn: pins if tn == a.type else orig_pins  # noqa: E731
    out = g2.part_probe(P, a.type, a.out, a.adjust, a.mem)
    meta = json.loads((out / "probe.json").read_text())
    meta.update(pilot=dict(pins=a.pins, centre=a.centre, per_bit=a.per_bit, obs_max=a.obs_max, clear=a.clear,
                           mouths=ivs, cores=[(c["inst"], c["origin_um"]) for c in t2.get("hard_cores", [])]))
    (out / "probe.json").write_text(json.dumps(meta, indent=1) + "\n")
    print(out, len(pins), "pins")


if __name__ == "__main__":
    main()
