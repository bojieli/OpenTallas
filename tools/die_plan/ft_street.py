#!/usr/bin/env python3
"""S81-LEAF-PLAN B5 (TL-LEAFT34, COORD 11-14): re-route an N<->S ft slot's register chain up a vertical street.

    ft_street_leafplan.py PLAN_IN PLAN_OUT TYPE SLOT:X [SLOT:X ...] [--reach 360]

Every register of SLOT keeps its count (ft latency unchanged); the end registers stay on their face rows (y kept)
and move inside their own pin window toward X; the inner registers are spread evenly in y on x = X (4.32 lattice).
Each bit-site group moves rigidly with its register.  Fails (exit 2) when a register or group box would touch a core
(+4.32 halo) or another group, or a hop exceeds --reach."""
import argparse, json, sys
from pathlib import Path

G, HALO = 4.32, 4.32


def snap(v):
    return round(round(v / G) * G, 4)


def ext(h):
    o = h["origin_um"]; d = h["outline_um"]; r = h.get("orient", "R0")
    w, hh = (d[1], d[0]) if r in ("R90", "R270", "MXR90", "MYR90") else d
    return (o[0], o[1], o[0] + w, o[1] + hh)


def gpts(s):
    return [list(p[:2]) for p in s] if s and isinstance(s[0], list) else ([list(s[:2])] if s else [])


def bbox(ps):
    return (min(p[0] for p in ps), min(p[1] for p in ps), max(p[0] for p in ps), max(p[1] for p in ps))


def hit(b, r, pad):
    return b[0] < r[2] + pad and b[2] > r[0] - pad and b[1] < r[3] + pad and b[3] > r[1] - pad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("type"); ap.add_argument("slots", nargs="+")
    ap.add_argument("--reach", type=float, default=360.0)
    a = ap.parse_args()
    P = json.loads(Path(a.plan_in).read_text()); t = P["partition_types"][a.type]
    W, H = t["outline_um"]
    cores = [ext(h) for h in t["hard_cores"]]
    by = {f["name"]: f for f in t["ft_slots"]}
    todo = dict((s.split(":")[0], float(s.split(":")[1])) for s in a.slots)
    other = [bbox(gpts(g)) for f in t["ft_slots"] if f["name"] not in todo for g in f.get("bit_sites_um") or [] if g]
    placed = []
    bad = []
    for name, X in todo.items():
        f = by[name]
        assert f["in_face"] in "NS" and f["out_face"] in "NS", name
        regs = [list(r[:2]) for r in f["regs_um"]]
        n = len(regs)
        groups = [gpts(g) for g in f.get("bit_sites_um") or []]
        own = {}
        for gi, ps in enumerate(groups):
            c = (sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps))
            own[gi] = min(range(n), key=lambda j: abs(regs[j][0] - c[0]) + abs(regs[j][1] - c[1]))
        lo, hi = regs[0][1], regs[-1][1]
        new = []
        for j in range(n):
            if j in (0, n - 1):
                win = f["in_window_um"] if j == 0 else f["out_window_um"]
                x = min(max(X, win[0] + 2 * G), win[1] - 2 * G)
                new.append([round(x, 4), regs[j][1]])
            else:
                new.append([snap(X), snap(lo + (hi - lo) * j / (n - 1))])
        cw, ch = (f.get("bit_site_cell_um") or [0, 0])[:2]
        newg = [None] * len(groups)
        for gi, ps in enumerate(groups):
            j = own[gi]; dx, dy = new[j][0] - regs[j][0], new[j][1] - regs[j][1]
            newg[gi] = [[round(p[0] + dx, 4), round(p[1] + dy, 4)] for p in ps]
            b = bbox(newg[gi]); b = (b[0] - cw / 2, b[1] - ch / 2, b[2] + cw / 2, b[3] + ch / 2)
            if b[0] < 0 or b[1] < -1e-6 or b[2] > W or b[3] > H + 1e-6:
                bad.append("%s group %d outside" % (name, gi))
            for k, r in enumerate(cores):
                if hit(b, r, HALO - 1e-6):
                    bad.append("%s group %d on core %s" % (name, gi, t["hard_cores"][k]["inst"]))
            for ob in other + placed:
                if hit(b, ob, 0.5):
                    bad.append("%s group %d on another ft group" % (name, gi))
            placed.append(b)
        for p, q in zip(new, new[1:]):
            if abs(p[0] - q[0]) + abs(p[1] - q[1]) > a.reach + 1e-6:
                bad.append("%s hop %.1f > reach" % (name, abs(p[0] - q[0]) + abs(p[1] - q[1])))
        f["regs_um"] = [nw + list(o[2:]) for nw, o in zip(new, f["regs_um"])]
        bs = f.get("bit_sites_um") or []
        for gi in range(len(bs)):
            if bs[gi] and isinstance(bs[gi][0], list):
                bs[gi] = [g + list(o[2:]) for g, o in zip(newg[gi], bs[gi])]
        f["note"] = (f.get("note", "") + " | B5 ft-street x=%.2f (TL-LEAFT34): %d regs, count kept" % (X, n)).lstrip(" |")
        print(name, "regs", [tuple(r) for r in new])
    if bad:
        print("FAIL", *sorted(set(bad)), sep="\n  "); sys.exit(2)
    Path(a.plan_out).write_text(json.dumps(P, indent=1))
    print("OK", a.type, list(todo))


if __name__ == "__main__":
    main()
