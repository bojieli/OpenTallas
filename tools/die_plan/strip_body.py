#!/usr/bin/env python3
"""strip_body: the plan form of a STRIP / BODY sub-tile split of one partition type (FAM-S81-SLICE-R4 11-21, COORD; S81
c1x_C t1..t10 split B and lepe_mu_C t1 split B, FAM-S81-LEPE-3 J8 rows).

    python3 -I tools/die_plan/strip_body.py resolve PLAN --type T [--json OUT]    strip region of one type (rects + notches)
    python3 -I tools/die_plan/strip_body.py census  PLAN                          every type that declares strip_body
    python3 -I tools/die_plan/strip_body.py spec    PLAN --type T --base B --out S  the type_split SPEC of the split

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
  cutouts        {"hard_cores": true (default) | false | [inst, ..], "contents": true (default: every content row
                 with origin_um + outline_um, i.e. plan-sited SRAM / ROM macros) | false,
                 "extra_um": [[x0, y0, x1, y1], ..], "note"}
  strip / body   {"suffix": "__strip" / "__body", "members": [glob, ..] (fnmatch on the instance path), "note"}
                 strip.members_by_face {"S": [glob, ..], ..}: plan CONTENTS that go to that face's strip piece (soft
                 face logic, e.g. KV hub astk_ES*); every other content stays in the body
                 body.members empty / absent = everything that is not strip
  crossing       {"cycles": 0, "registered": "both_sides" | "strip_side" | "body_side", "note"}
  split_axis     "y" (S + N strips) | "x" (W + E strips) | "auto" (default: the axis with the larger strip area)
  lattice_um     cut lattice (default: the plan grid_um, 8.64)
  trigger, note  free text (why the split exists, e.g. "nontap > 400k at place")

What this module does: schema-level validation (check "strip_body" in G0, WARN only, never a gate: R-MINIMAL) and the
geometry: strip rectangles, per-face notches in the form the J7/J8 rows use ({from, to, depth} along each face), area.

BUILD FORM (FLOW-STRIPBODY-1121): a kit is one rectangular OpenROAD block and die partitions tile the die, so a notched
strip cannot be its own kit.  The buildable form is a type_split event (tools/die_plan/type_split.py, the svc path) along
ONE axis: the faces of that axis (S + N for split_axis "y", W + E for "x") each become a STRIP piece, a full-length
rectangle as deep as the band allows WITHOUT crossing a cutout (band depth clipped to the nearest cutout incl. halo,
snapped down to the plan lattice), and the middle piece is the BODY (it keeps the type / partition names, region
origin and START pins: type_split's keep piece).  type_split moves the face infrastructure by geometry (buses by port
window face, ft slots / internal stations by leg, landings with their bus), so the strip members are what lands in the
strip rectangle; the faces of the other axis stay in the body.  `spec` writes that type_split SPEC:

    python3 -I tools/die_plan/strip_body.py spec PLAN --type T [--type T2 ..] --base BASE.json --out SPEC.json
        BASE: the type_split SPEC fields the plan does not carry (plan, plan_dir, sidecar, asbuilt, census, event, ..);
        written: family, axis, cuts_um, parts (strip suffix + face, body ""), keep, contents (every content -> body).
        Family members must resolve to the same cuts (type_split R-CAP-3.4), else one event per cut set.
"""
import argparse
import fnmatch
import json
import math
import re
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
    if c.get("contents", True):
        # plan-sited macros of soft contents (SRAM / ROM content rows with origin_um + outline_um, e.g. S81 xg u_mem)
        for h in t.get("contents") or []:
            if isinstance(h, dict) and "origin_um" in h and "outline_um" in h:
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


def face_clip(W, H, d, cuts, face):
    """the depth of a full-length rectangle on `face` that stays inside the band and crosses no cutout"""
    D = d[face]
    if D <= 0:
        return 0.0
    for _, (x0, y0, x1, y1) in cuts:
        near, far = {"S": (y0, y1), "N": (H - y1, H - y0), "W": (x0, x1), "E": (W - x1, W - x0)}[face]
        a, b = (x0, x1) if face in ("S", "N") else (y0, y1)
        L = W if face in ("S", "N") else H
        if b <= EPS or a >= L - EPS or far <= EPS:
            continue                     # cutout off the face extent or wholly outside the tile on this side
        if near < D:
            D = near
    return max(D, 0.0)


def split_axis_plan(t, tn="", lattice=8.64):
    """{axis, cuts_um, faces: {face: depth}, parts, keep, area: {x, y}} of the one-axis split of a strip_body type"""
    sb = t.get("strip_body")
    if not sb:
        raise ValueError(f"type {tn}: no strip_body")
    if t.get("hard"):
        raise ValueError(f"type {tn}: a hard type is not split")
    W, H = (float(v) for v in t["outline_um"])
    d = band_depths(sb)
    cuts = cutouts(t, sb)
    lat = float(sb.get("lattice_um", lattice))
    dep = {}
    for f in FACES:
        c = face_clip(W, H, d, cuts, f)
        dep[f] = math.floor(c / lat + 1e-6) * lat
    area = {"y": (dep["S"] + dep["N"]) * W, "x": (dep["W"] + dep["E"]) * H}
    ax = sb.get("split_axis", "auto")
    if ax == "auto":
        ax = "y" if area["y"] >= area["x"] else "x"
    lo, hi = ("S", "N") if ax == "y" else ("W", "E")
    L = H if ax == "y" else W
    if abs(L / lat - round(L / lat)) > 1e-6:
        raise ValueError(f"type {tn}: outline {L} along {ax} is not on the {lat:g}-um lattice")
    if dep[lo] <= 0 and dep[hi] <= 0:
        raise ValueError(f"type {tn}: no {lo}/{hi} strip fits: band clipped by cutouts to "
                         f"{face_clip(W, H, d, cuts, lo):.2f} / {face_clip(W, H, d, cuts, hi):.2f} um (< lattice {lat:g})")
    ssfx = (sb.get("strip") or {}).get("suffix", "__strip")
    cuts_um, parts = [], []
    if dep[lo] > 0:
        cuts_um.append(round(dep[lo], 6))
        parts.append({"suffix": ssfx + "_" + lo})
    keep = len(parts)
    parts.append({"suffix": ""})
    if dep[hi] > 0:
        cuts_um.append(round(L - dep[hi], 6))
        parts.append({"suffix": ssfx + "_" + hi})
    if len(cuts_um) == 2 and cuts_um[1] - cuts_um[0] < lat - EPS:
        raise ValueError(f"type {tn}: strips {lo} {dep[lo]} + {hi} {dep[hi]} leave no body")
    other = [f for f in (("W", "E") if ax == "y" else ("S", "N")) if d[f] > 0]
    return dict(type=tn, axis=ax, cuts_um=cuts_um, parts=parts, keep=keep, lattice_um=lat,
                strip_depth_um={f: round(v, 4) for f, v in dep.items() if f in (lo, hi)},
                band_clip_um={f: round(face_clip(W, H, d, cuts, f), 4) for f in FACES if d[f] > 0},
                faces_in_body=other, area_um2={k: round(v, 2) for k, v in area.items()})


def split_spec(raw, types, base=None):
    """type_split SPEC (dict) of the strip / body split of `types` (one family: same cuts) on plan `raw`"""
    pt = raw.get("partition_types") or {}
    grid = float(raw.get("grid_um", 8.64))
    plans = []
    for tn in types:
        if tn not in pt:
            raise ValueError(f"no type {tn}")
        plans.append(split_axis_plan(pt[tn], tn, grid))
    key = {(p["axis"], tuple(p["cuts_um"]), tuple(x["suffix"] for x in p["parts"])) for p in plans}
    if len(key) != 1:
        raise ValueError("family members resolve to different cuts (one split event per cut set): "
                         + "; ".join(f"{p['type']} {p['axis']} {p['cuts_um']}" for p in plans))
    p0 = plans[0]
    sp = dict(base or {})
    sp.update(family=list(types), axis=p0["axis"], cuts_um=p0["cuts_um"], parts=p0["parts"], keep=p0["keep"])
    sp.setdefault("event", "STRIP-BODY")
    sp.setdefault("band_reshape", True)      # landing bands deeper than a thin strip piece widen along the cut
    sp.setdefault("carry_short_fixed", True)  # base lanes below their station rows carry the cut delta
    sp.setdefault("strapless_pieces", True)   # a strip piece without count-aligned crossings has no count straps
    sp.setdefault("whole_map_to_keep", True)  # the as-built tile instance maps to the body (keep piece) whole
    # clock keys type_split re-derives per piece (the svc split precedent, OPUS-FIX-S81-SVC-R6 spec_x_epoch)
    sp.setdefault("drop_clock_keys", ["band_fixed_um", "band_tap_windows_um", "insertion_target_override",
                                      "tap_clear_um", "tap_pair_affinity", "tap_reserved_um"])
    sp.setdefault("clip_windows", True)      # W/E (x: S/N) windows across a strip cut stay with their majority piece
    contents = dict(sp.get("contents") or {})
    piece_of_face = {x["suffix"].rsplit("_", 1)[-1]: i for i, x in enumerate(p0["parts"]) if x["suffix"]}
    for tn in types:
        t = pt[tn]
        sb = t["strip_body"]
        st = (sb.get("strip") or {}).get("members") or []
        mbf = (sb.get("strip") or {}).get("members_by_face") or {}
        rules = []
        for f, globs in sorted(mbf.items()):
            if f not in piece_of_face:
                raise ValueError(f"type {tn}: strip.members_by_face {f} is not a strip face of the {p0['axis']} split")
            rules += [[fnmatch.translate(g).replace("\\Z", "").replace("(?s:", "(?:"), piece_of_face[f]] for g in globs]
        ruled = [re.compile(rx) for rx, _ in rules]
        bad = [c["inst"] for c in t.get("contents") or [] if any(fnmatch.fnmatchcase(c["inst"], g) for g in st)
               and not any(r.fullmatch(c["inst"]) for r in ruled)]
        if bad:
            raise ValueError(f"type {tn}: contents {bad[:5]} match strip member globs: plan contents stay in the body "
                             "unless strip.members_by_face names their face (the strip pieces take face "
                             "infrastructure by geometry)")
        contents.setdefault(tn, rules + [[".*", p0["keep"]]])
    sp["contents"] = contents
    sp["strip_body"] = {p["type"]: {k: p[k] for k in ("strip_depth_um", "band_clip_um", "faces_in_body", "area_um2")}
                        for p in plans}
    return sp


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
    s = sp.add_parser("spec")
    s.add_argument("plan")
    s.add_argument("--type", action="append", required=True)
    s.add_argument("--base", help="type_split SPEC fields the plan does not carry (plan, sidecar, asbuilt, census, ..)")
    s.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    raw = json.loads(Path(args.plan).read_text())
    pt = raw.get("partition_types") or {}
    if args.cmd == "spec":
        base = json.loads(Path(args.base).read_text()) if args.base else {}
        base.setdefault("plan", str(Path(args.plan).resolve()))
        try:
            sp = split_spec(raw, args.type, base)
        except (ValueError, KeyError, TypeError) as ex:
            print(f"strip_body spec: FAIL {ex}", file=sys.stderr)
            return 2
        Path(args.out).write_text(json.dumps(sp, indent=1) + "\n")
        for tn, r in sp["strip_body"].items():
            print(f"STRIP_BODY_SPLIT {tn}: axis {sp['axis']} cuts {sp['cuts_um']} parts "
                  f"{[x['suffix'] or '(body)' for x in sp['parts']]} strip depth {r['strip_depth_um']} "
                  f"band clip {r['band_clip_um']} faces left in body {r['faces_in_body']}")
        return 0
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
