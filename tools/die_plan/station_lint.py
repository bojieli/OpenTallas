#!/usr/bin/env python3
"""PLAN-ROUTE-1 11-11 (COORD S7 class, DIE-KV-97 kv3_phy phyrev): STATION-DIRECTION LINT for plan station chains.

kit_istations puts station k of an internal_station at regs_um[k] counted from the LAUNCH (driver) end, and ft slot
station k at regs_um[k] from the in face.  A chain written sink -> driver therefore lands its stations in reverse and the
routed chain zig-zags (KV-TYPES-5 o_phy_Q: from_um on the east face while the launch is the core, 870 um last hop,
TT -238 ps).  Checks, per type:

  internal_stations on a face bus (conn bus:<name>, plan bus dir + face): the stages in the order kit_istations sites
    them (in bus: regs_um as written, stage 0 next to the face register; out bus: regs_um as written from the leaf,
    reversed when launch is 'face bus ...', KW-FIX-27) must follow the data flow: in = distance from the bus face grows,
    out = it shrinks.  Stage 0 on the wrong end -> INVERTED; a step back by more than tol (max(10 um, 5% of the
    span)) -> NONMONOTONE.  core<->core chains are ordered by RTL link class in kit_istations and are not judged here.
  ft_slots: regs_um[0] must be the in-face end (distance from the in face grows along regs_um).

usage: station_lint.py PLAN.json[.gz] [PLAN ...] [--tsv OUT.tsv] [--types a,b]   (ADVISORY, exit 0)"""
import argparse
import gzip
import json
import re
import sys

EDGE_TOL = 2.0


def _open(p):
    return gzip.open(p, "rt") if str(p).endswith(".gz") else open(p)


def _pt(v):
    try:
        return (float(v[0]), float(v[1]))
    except (TypeError, ValueError, IndexError):
        return None


def on_edge(p, W, H, tol=EDGE_TOL):
    return min(p[0], p[1], W - p[0], H - p[1]) <= tol


def _l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _rect_dist(p, r):
    x0, y0, x1, y1 = r
    return max(x0 - p[0], 0, p[0] - x1) + max(y0 - p[1], 0, p[1] - y1)


def _core_of(text, rects):
    """the hard-core inst named by a launch / capture text (longest inst that occurs as a token prefix)."""
    s = str(text)
    s = s[5:] if s.startswith("core:") else s
    best = None
    for inst in rects:
        if s == inst or s.startswith(inst + ".") or s.startswith(inst + " "):
            if best is None or len(inst) > len(best):
                best = inst
    return best


def _is_face(text, buses):
    s = str(text).lower()
    if "face" in s:
        return True
    m = re.match(r"^(?:bus[: ])?([A-Za-z_][\w$]*)", str(text))
    return bool(m and m.group(1) in buses and buses[m.group(1)].get("face"))


def monotone(seq, tol_frac=0.05, tol_min=10.0):
    a, z = seq[0], seq[-1]
    span = _l1(a, z)
    tol = max(tol_min, tol_frac * span)
    da = [_l1(a, p) for p in seq]
    dz = [_l1(p, z) for p in seq]
    back = max([da[i] - da[i + 1] for i in range(len(seq) - 1)] + [dz[i + 1] - dz[i] for i in range(len(seq) - 1)] + [0])
    path = sum(_l1(seq[i], seq[i + 1]) for i in range(len(seq) - 1))
    return back <= tol, round(back, 1), round(path / span, 2) if span > 0 else None


def _face_dist(face, W, H):
    return {"W": lambda p: p[0], "E": lambda p: W - p[0], "S": lambda p: p[1], "N": lambda p: H - p[1]}.get(face)


def _edge_face(e, W, H, tol=EDGE_TOL):
    """the bus face when the plan bus has none: the outline edge that exactly one chain end (from_um / to_um) sits on."""
    hits = set()
    for k in ("from_um", "to_um"):
        p = _pt(e.get(k))
        if p is None:
            continue
        for f, dv in (("W", p[0]), ("E", W - p[0]), ("S", p[1]), ("N", H - p[1])):
            if dv <= tol:
                hits.add(f)
    return hits.pop() if len(hits) == 1 else None


def kit_order(e, b):
    """regs_um in the order kit_istations sites the stages (stage 0 first): in bus = from the face register inward;
    out bus = from the leaf toward the face, reversed when the entry is launched at the face (KW-FIX-27)."""
    regs = [p for p in (_pt(r) for r in e.get("regs_um") or []) if p]
    if b.get("dir") == "out" and str(e.get("launch", "")).startswith("face bus"):
        regs = regs[::-1]
    return regs


def lint_type(tn, t):
    """station chains whose kit stage order runs against the data flow (INVERTED) or doubles back (NONMONOTONE)."""
    out = []
    W, H = map(float, t.get("outline_um") or (0, 0))
    if not W or not H:
        return out
    buses = {b["name"]: b for b in t.get("buses") or [] if b.get("name")}
    for i, e in enumerate(t.get("internal_stations") or []):
        conn = str(e.get("conn", ""))
        b = buses.get(conn[4:]) if conn.startswith("bus:") else None
        if not b or b.get("dir") not in ("in", "out"):
            continue                        # core<->core chains: kit_istations orders them by RTL link class
        face = b.get("face") if b.get("face") in ("N", "S", "E", "W") else _edge_face(e, W, H)
        eff = kit_order(e, b)
        if len(eff) < 2 or face is None:
            continue
        b = dict(b, face=face)
        d = _face_dist(face, W, H)
        fp, tp = _pt(e.get("from_um")), _pt(e.get("to_um"))
        ends = [q for q in (fp, tp) if q]
        on = [q for q in ends if on_edge(q, W, H)]
        if len(ends) == 2 and len(on) == 1:
            # progress along face end -> leaf end (robust when the chain runs along the face), scaled to um
            F = on[0]
            C = tp if F is fp else fp
            vx, vy = C[0] - F[0], C[1] - F[1]
            n = (vx * vx + vy * vy) ** 0.5 or 1.0
            d = (lambda F, vx, vy, n: lambda q: ((q[0] - F[0]) * vx + (q[1] - F[1]) * vy) / n)(F, vx, vy, n)
        ds = [d(p) for p in eff]
        span = max(ds) - min(ds)
        tol = max(10.0, 0.05 * span)
        # INVERTED needs stage 0 to sit past the last stage by a quarter of the face<->leaf length (or of the stage
        # span when the ends are unknown): two stages a few um apart are placement noise, not a reversed chain
        L = _l1(fp, tp) if fp and tp else span
        tol_inv = max(10.0, 0.25 * L)
        # data flow: in bus face -> leaf (distance from the face grows), out bus leaf -> face (distance shrinks)
        sgn = 1 if b["dir"] == "in" else -1
        why, kind = [], None
        if sgn * (ds[-1] - ds[0]) < -tol_inv:
            kind = "INVERTED"
            why.append(f"{b['dir']} bus on face {b['face']}: kit stage 0 is {ds[0]:.0f} um from the face end, the last "
                       f"stage {ds[-1]:.0f} um, so the stages run {'leaf -> face' if sgn > 0 else 'face -> leaf'} "
                       f"against the data flow (launch '{e.get('launch')}')")
        back = max([sgn * (ds[k] - ds[k + 1]) for k in range(len(ds) - 1)] + [0])
        if kind is None and back > tol:
            kind = "NONMONOTONE"
            why.append(f"stages step back {back:.0f} um toward the {'face' if sgn > 0 else 'leaf'} "
                       f"(distances from face {b['face']}: {[round(x) for x in ds]})")
        if kind:
            out.append(dict(type=tn, kind=kind, chain="internal_station", name=conn, index=i,
                            launch=e.get("launch", ""), capture=e.get("capture", ""), from_um=e.get("from_um"),
                            to_um=e.get("to_um"), regs=len(eff), why="; ".join(why)))
    for f in t.get("ft_slots") or []:
        regs = [p for p in (_pt(r) for r in f.get("regs_um") or []) if p]
        d = _face_dist(f.get("in_face"), W, H)
        if len(regs) < 2 or d is None:
            continue
        ds = [d(p) for p in regs]
        tol = max(10.0, 0.05 * (max(ds) - min(ds)))
        why, kind = [], None
        if ds[0] > ds[-1] + tol:
            kind = "INVERTED"
            why.append(f"ft regs_um[0] is {ds[0]:.0f} um from the in face {f.get('in_face')}, regs_um[-1] "
                       f"{ds[-1]:.0f} um: written out -> in")
        back = max([ds[k] - ds[k + 1] for k in range(len(ds) - 1)] + [0])
        if kind is None and back > tol:
            kind = "NONMONOTONE"
            why.append(f"ft stations step back {back:.0f} um toward the in face (distances {[round(x) for x in ds]})")
        if kind:
            out.append(dict(type=tn, kind=kind, chain="ft_slot", name=str(f.get("name")), index=None,
                            launch=f"face {f.get('in_face')}", capture=f"face {f.get('out_face')}",
                            from_um=list(regs[0]), to_um=list(regs[-1]), regs=len(regs), why="; ".join(why)))
    return out


def lint_plan(P, types=None):
    T = P.get("partition_types", {})
    res = []
    for tn in T:
        if types and tn not in types:
            continue
        res += lint_type(tn, T[tn])
    return res


HDR = ["plan", "type", "kind", "chain", "name", "index", "launch", "capture", "from_um", "to_um", "regs", "why"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plans", nargs="+")
    ap.add_argument("--tsv")
    ap.add_argument("--types")
    a = ap.parse_args(argv)
    lines = ["\t".join(HDR)]
    for p in a.plans:
        res = lint_plan(json.load(_open(p)), set(a.types.split(",")) if a.types else None)
        for r in res:
            lines.append("\t".join(str(r[k]) if k != "plan" else p for k in HDR))
        kinds = {}
        for r in res:
            kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
        print(f"# {p}: {len(res)} chains flagged {kinds} in {len({r['type'] for r in res})} types (ADVISORY)",
              file=sys.stderr)
    if a.tsv:
        open(a.tsv, "w").write("\n".join(lines) + "\n")
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
