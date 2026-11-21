#!/usr/bin/env python3
"""strip_body: the plan form of a STRIP / BODY sub-tile split of one partition type (FAM-S81-SLICE-R4 11-21, COORD; S81
c1x_C t1..t10 split B and lepe_mu_C t1 split B, FAM-S81-LEPE-3 J8 rows).

    python3 -I tools/die_plan/strip_body.py resolve PLAN --type T [--json OUT]    strip region of one type (rects + notches)
    python3 -I tools/die_plan/strip_body.py census  PLAN                          every type that declares strip_body

A type over the OpenROAD cell cap (~400k) whose infrastructure (landings, ft stations, relays, ring CA) sits along the
tile perimeter is split into two kits of the SAME tile: a STRIP kit that holds the perimeter infrastructure and a BODY kit
that holds the hard cores and the soft logic between them.  The strip is not a rectangle: it is a perimeter band of
band_um on the named faces MINUS the bounding box of every hard core (and every declared extra keep-out, e.g. SRAM
macros inside a soft block) grown by halo_um.  The region is a RULE resolved against the bound plan's core origins, so a
plan event that moves or rotates a core moves the notches with it (no hand-copied numbers).

Plan key (partition_types.<T>.strip_body, schema.py):
  band_um        number, or {"S"|"W"|"N"|"E": number}   band depth per face (type frame R0)
  faces          ["S","W","N","E"] subset (default all four)
  halo_um        keep-out grown around each cutout (default 5)
  cutouts        {"hard_cores": true (default) | false | [inst, ..], "extra_um": [[x0, y0, x1, y1], ..], "note"}
  strip / body   {"suffix": "__strip" / "__body", "members": [glob, ..] (fnmatch on the instance path), "note"}
                 body.members empty / absent = everything that is not strip
  crossing       {"cycles": 0, "registered": "both_sides" | "strip_side" | "body_side", "note"}
  trigger, note  free text (why the split exists, e.g. "nontap > 400k at place")

What this module does: schema-level validation (check "strip_body" in G0, WARN only, never a gate: R-MINIMAL) and the
geometry: strip rectangles, per-face notches in the form the J7/J8 rows use ({from, to, depth} along each face), area.
What it does not do (yet): emit the two kits.  The split event itself (bind / gen of __strip and __body) consumes
resolve(); until it exists the key is carried by the plan and checked, and kits of the type build unsplit.
"""
import argparse
import fnmatch
import json
import sys
from pathlib import Path

FACES = ("S", "W", "N", "E")
EPS = 1e-6
ROT = ("R90", "R270", "MXR90", "MYR90")


def core_box(h):
    """hard core bbox in the type frame: origin_um is the lower-left of the placed extent, outline_um the R0 size
    (swapped for a quarter-turn orientation)"""
    w, hh = h["outline_um"]
    if h.get("orient", "R0") in ROT:
        w, hh = hh, w
    x0, y0 = h["origin_um"]
    return (float(x0), float(y0), float(x0) + w, float(y0) + hh)


def band_depths(sb):
    b = sb.get("band_um", 0)
    faces = sb.get("faces") or list(FACES)
    if isinstance(b, dict):
        return {f: float(b.get(f, 0.0)) if f in faces else 0.0 for f in FACES}
    return {f: (float(b) if f in faces else 0.0) for f in FACES}


def cutouts(t, sb):
    """[(name, (x0, y0, x1, y1))] keep-outs grown by halo_um"""
    c = sb.get("cutouts") or {}
    halo = float(sb.get("halo_um", 5.0))
    sel = c.get("hard_cores", True)
    out = []
    for h in t.get("hard_cores") or []:
        if "origin_um" not in h or "outline_um" not in h:
            continue
        if sel is True or (isinstance(sel, list) and h.get("inst") in sel):
            x0, y0, x1, y1 = core_box(h)
            out.append((h.get("inst", "?"), (x0 - halo, y0 - halo, x1 + halo, y1 + halo)))
    for i, r in enumerate(c.get("extra_um") or []):
        x0, y0, x1, y1 = (float(v) for v in r)
        out.append(("extra[%d]" % i, (min(x0, x1) - halo, min(y0, y1) - halo, max(x0, x1) + halo, max(y0, y1) + halo)))
    return out


def _bands(W, H, d):
    r = []
    if d["S"] > 0:
        r.append((0.0, 0.0, W, min(d["S"], H)))
    if d["N"] > 0:
        r.append((0.0, max(H - d["N"], 0.0), W, H))
    if d["W"] > 0:
        r.append((0.0, 0.0, min(d["W"], W), H))
    if d["E"] > 0:
        r.append((max(W - d["E"], 0.0), 0.0, W, H))
    return r


def _inside(x, y, r):
    return r[0] - EPS <= x <= r[2] + EPS and r[1] - EPS <= y <= r[3] + EPS


def strip_rects(W, H, d, cuts):
    """the strip as disjoint rectangles: grid cells (breakpoints of every band and cutout) inside a band and outside every
    cutout, merged along x per row, then rows of equal x-extent merged along y"""
    bands = _bands(W, H, d)
    xs = sorted({0.0, W} | {min(max(v, 0.0), W) for r in bands + [c for _, c in cuts] for v in (r[0], r[2])})
    ys = sorted({0.0, H} | {min(max(v, 0.0), H) for r in bands + [c for _, c in cuts] for v in (r[1], r[3])})
    rows = []
    for j in range(len(ys) - 1):
        y0, y1 = ys[j], ys[j + 1]
        if y1 - y0 <= EPS:
            continue
        ym = 0.5 * (y0 + y1)
        runs, cur = [], None
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i + 1]
            if x1 - x0 <= EPS:
                continue
            xm = 0.5 * (x0 + x1)
            on = any(_inside(xm, ym, b) for b in bands) and not any(
                c[0] < xm < c[2] and c[1] < ym < c[3] for _, c in cuts)
            if on and cur is not None and abs(cur[1] - x0) <= EPS:
                cur[1] = x1
            elif on:
                cur = [x0, x1]
                runs.append(cur)
            else:
                cur = None
        rows.append((y0, y1, [tuple(r) for r in runs]))
    out, open_ = [], {}
    for y0, y1, runs in rows:
        nxt = {}
        for r in runs:
            if r in open_ and abs(open_[r][3] - y0) <= EPS:
                b = open_.pop(r)
                nxt[r] = (b[0], b[1], b[2], y1)
            else:
                nxt[r] = (r[0], y0, r[1], y1)
        out += list(open_.values())
        open_ = nxt
    out += list(open_.values())
    return sorted((round(a, 4), round(b, 4), round(c, 4), round(e, 4)) for a, b, c, e in out)


def notches(W, H, d, cuts):
    """per face, the band depth along the face: [{from, to, depth}] (depth = distance from the face to the nearest
    cutout that reaches into the band over that interval, else the band depth); intervals of equal depth merged"""
    res = {}
    for f in FACES:
        D = d[f]
        if D <= 0:
            continue
        L = W if f in ("S", "N") else H
        pts = {0.0, L}
        dist = []
        for _, (x0, y0, x1, y1) in cuts:
            a, b = (x0, x1) if f in ("S", "N") else (y0, y1)
            near = {"S": y0, "N": H - y1, "W": x0, "E": W - x1}[f]
            if near < D - EPS and b > 0 and a < L:
                lo, hi = max(a, 0.0), min(b, L)
                pts |= {lo, hi}
                dist.append((lo, hi, max(near, 0.0)))
        pts = sorted(pts)
        segs = []
        for i in range(len(pts) - 1):
            lo, hi = pts[i], pts[i + 1]
            if hi - lo <= EPS:
                continue
            m = 0.5 * (lo + hi)
            dep = min([D] + [z for a, b, z in dist if a < m < b])
            if segs and abs(segs[-1]["depth"] - dep) <= EPS and abs(segs[-1]["to"] - lo) <= EPS:
                segs[-1]["to"] = round(hi, 4)
            else:
                segs.append(dict(to=round(hi, 4), depth=round(dep, 4), **{"from": round(lo, 4)}))
        res[f] = segs
    return res


def resolve(t, tn=""):
    """{strip_rects, notches, strip_area_um2, cutouts, outline_um} of one type's strip_body (ValueError if malformed)"""
    sb = t.get("strip_body")
    if not sb:
        raise ValueError(f"type {tn}: no strip_body")
    W, H = (float(v) for v in t["outline_um"])
    d = band_depths(sb)
    if not any(v > 0 for v in d.values()):
        raise ValueError(f"type {tn}: strip_body band_um is 0 on every face")
    for f, g, lim in (("S", "N", H), ("W", "E", W)):
        if d[f] + d[g] >= lim - EPS:
            raise ValueError(f"type {tn}: strip_body bands {f} {d[f]} + {g} {d[g]} um leave no body (outline {W} x {H})")
    cuts = cutouts(t, sb)
    rects = strip_rects(W, H, d, cuts)
    area = sum((c - a) * (e - b) for a, b, c, e in rects)
    return dict(type=tn, outline_um=[W, H], band_um=d, halo_um=float(sb.get("halo_um", 5.0)),
                cutouts=[dict(name=n, rect_um=[round(v, 4) for v in r]) for n, r in cuts],
                strip_rects=[list(r) for r in rects], strip_area_um2=round(area, 2),
                strip_frac=round(area / (W * H), 4) if W * H else 0.0, notches=notches(W, H, d, cuts))


def member_errors(t, sb, tn=""):
    """strip / body member globs: non-empty strip list; a hard core never belongs to the strip (cores stay in the body)"""
    errs = []
    st = (sb.get("strip") or {}).get("members") or []
    bd = (sb.get("body") or {}).get("members") or []
    if not st:
        errs.append(f"type {tn}: strip_body.strip.members is empty (the strip kit would hold nothing)")
    for h in t.get("hard_cores") or []:
        i = h.get("inst", "")
        if any(fnmatch.fnmatchcase(i, g) for g in st):
            errs.append(f"type {tn}: hard core {i} matches strip member glob (hard cores stay in the body)")
    both = sorted(set(st) & set(bd))
    if both:
        errs.append(f"type {tn}: globs in both strip and body members: {both}")
    sfx = {(sb.get("strip") or {}).get("suffix", "__strip"), (sb.get("body") or {}).get("suffix", "__body")}
    if len(sfx) != 2:
        errs.append(f"type {tn}: strip and body suffix are equal")
    return errs


def check_plan(P, R, max_msgs=40):
    """G0 entry (check.py run): every type with strip_body resolves (WARN on a failure, check "strip_body"; never an
    ERROR: the split is not built by this module and a plan carrying the rows must still pass G0)"""
    raw = P.raw if hasattr(P, "raw") else P
    n, bad = 0, 0
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict) or not t.get("strip_body"):
            continue
        n += 1
        msgs = member_errors(t, t["strip_body"], tn)
        try:
            r = resolve(t, tn)
            if r["strip_area_um2"] <= 0:
                msgs.append(f"type {tn}: strip region is empty after the cutouts")
        except (ValueError, KeyError, TypeError) as ex:
            msgs.append(str(ex))
        for m in msgs:
            bad += 1
            if bad <= max_msgs:
                R.warn("strip_body", m, type=tn)
    return dict(types=n, warnings=bad)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("resolve")
    a.add_argument("plan")
    a.add_argument("--type", required=True)
    a.add_argument("--json")
    c = sp.add_parser("census")
    c.add_argument("plan")
    args = ap.parse_args(argv)
    raw = json.loads(Path(args.plan).read_text())
    pt = raw.get("partition_types") or {}
    if args.cmd == "resolve":
        if args.type not in pt:
            print(f"no type {args.type}", file=sys.stderr)
            return 2
        r = resolve(pt[args.type], args.type)
        r["member_errors"] = member_errors(pt[args.type], pt[args.type]["strip_body"], args.type)
        txt = json.dumps(r, indent=1)
        if args.json:
            Path(args.json).write_text(txt + "\n")
        print(f"STRIP_BODY {args.type}: {len(r['strip_rects'])} rects, area {r['strip_area_um2']} um2 "
              f"({r['strip_frac']:.1%}), cutouts {len(r['cutouts'])}, member errors {len(r['member_errors'])}")
        for f, segs in r["notches"].items():
            print(f"  {f}: " + " ".join(f"[{s['from']}-{s['to']} d{s['depth']}]" for s in segs))
        return 1 if r["member_errors"] else 0
    rows = [tn for tn, t in sorted(pt.items()) if isinstance(t, dict) and t.get("strip_body")]
    for tn in rows:
        try:
            r = resolve(pt[tn], tn)
            print(f"{tn}\tarea {r['strip_area_um2']}\trects {len(r['strip_rects'])}")
        except (ValueError, KeyError, TypeError) as ex:
            print(f"{tn}\tERROR {ex}")
    print(f"STRIP_BODY types {len(rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
