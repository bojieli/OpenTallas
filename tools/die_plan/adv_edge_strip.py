"""ADV-EDGE-STRIP (VIS-DIE-S81 EDGESTRIP-1, COORD 11-23; an estimator, never a gate).

A wide die pin window needs a core-free strip behind it: the pins land on the face and the bus has to spread along the
face before it can pass the hard cores.  S81 J8 f65f62779bef: 241 types had a >= 256-bit window with a hard core
< 69.12 um from the face across the window span (svc u_c 34.6 um on S/W/E, dsdv u_cap/u_xr 34.6-51.8, leaf u_l 6.5 /
u_m 34.6, col u_c 43.2-51.8); 0 of 47 signed types and 40 of 51 failing types had it.  VIS-S81-COL measured the col
threshold: strip 43-52 um -> GRT overflow 1160-4928, >= 69.12 um converges (h9_r1 69.1, p1/p3 86.4).

For every die port of width >= MIN_BITS, on both partitions (src face and partner face mapped to the type frame through
origin + orient), the strip = distance from the face to the nearest hard core or placed
contents macro whose span along the face overlaps the
window span.  A strip < STRIP_UM is one line per type (worst window first).  The fix is the EDGESTRIP-1 form
(edgestrip_row.py: rigid / band interior shift inside the outline) or a re-shape; window moves do not help when the
core row runs along the whole face.
"""
import time

import adv_port_window_pair as PW

CHECK = "ADV-EDGE-STRIP"
MIN_BITS = 256
STRIP_UM = 69.12
MAX_LINES = 20
OPP = dict(N="S", S="N", E="W", W="E")


def _type_span(p, t, dface, lo, hi):
    """die-frame window [lo, hi] on die face dface of partition p -> (type face, lo, hi) in the type frame."""
    w, h = t["outline_um"]
    o = p.get("orient", "R0")
    tf = PW._type_face(o, dface)
    if dface in "NS":
        base, ext, flip = p["origin_um"][0], w, o in ("MY", "R180")
    else:
        base, ext, flip = p["origin_um"][1], h, o in ("MX", "R180")
    a, b = lo - base, hi - base
    if flip:
        a, b = ext - b, ext - a
    return tf, a, b


def strips(raw, min_bits=MIN_BITS):
    """[(type, part, type_face, lo, hi, bits, port, strip, core)] for every >= min_bits window with a core behind it."""
    parts = {p["name"]: p for p in raw.get("partitions") or []}
    types = raw.get("partition_types") or {}
    out = []
    for pr in raw.get("ports") or []:
        w = int(pr.get("width", 1) or 1)
        if w < min_bits:
            continue
        face, win = pr.get("face"), pr.get("window_um")
        if not face or not win:
            g = PW._side_geom(parts, types, pr, "src") or PW._side_geom(parts, types, pr, "dst")
            if not g:
                continue
            face, win = g[0], g[1]
        s, d = pr["src"].get("part"), pr["dst"].get("part")
        fp = s if s != PW.DIE_PART else d
        sides = [(fp, face)]
        oth = d if fp == s else s
        if oth in parts and oth != fp:
            sides.append((oth, OPP[face]))
        lo, hi = sorted(float(v) for v in win)
        for part, df in sides:
            p = parts.get(part)
            if not p or p.get("type") not in types:
                continue
            t = types[p["type"]]
            tf, a, b = _type_span(p, t, df, lo, hi)
            W, H = t["outline_um"]
            best = None
            for c in (t.get("hard_cores") or []) + [m for m in t.get("contents") or [] if isinstance(m, dict)]:
                if "origin_um" not in c or "outline_um" not in c:   # hard cores and placed contents macros (sram/rom)
                    continue
                x0, y0 = c["origin_um"]
                x1, y1 = x0 + c["outline_um"][0], y0 + c["outline_um"][1]
                s0, s1 = (x0, x1) if tf in "NS" else (y0, y1)
                if min(s1, b) - max(s0, a) <= 0.01:
                    continue
                dist = {"S": y0, "N": H - y1, "W": x0, "E": W - x1}[tf]
                if best is None or dist < best[0]:
                    best = (dist, c.get("inst"))
            if best is not None:
                out.append((p["type"], part, tf, round(a, 2), round(b, 2), w, pr.get("id"), round(best[0], 2), best[1]))
    return out


def findings(raw, plan_path, tree=None, strip_um=STRIP_UM, min_bits=MIN_BITS, **kw):
    t0 = time.time()
    try:
        rows = [r for r in strips(raw, min_bits) if r[7] < strip_um - 1e-6]
        by = {}
        for r in rows:
            by.setdefault(r[0], []).append(r)
        order = sorted(by.items(), key=lambda kv: (min(r[7] for r in kv[1]), -sum(r[5] for r in kv[1])))
        out = []
        for tn, rs in order[:MAX_LINES]:
            rs.sort(key=lambda r: (r[7], -r[5]))
            r = rs[0]
            faces = "".join(sorted({x[2] for x in rs}))
            out.append(f"WARN {CHECK} {tn}: {len(rs)} window(s) >= {min_bits} bits ({sum(x[5] for x in rs)} bits, faces {faces}) "
                       f"with a hard core < {strip_um} um behind; worst {r[6]} {r[5]} bits face {r[2]} [{r[3]},{r[4]}] "
                       f"strip {r[7]} um to {r[8]}; fix: EDGESTRIP-1 form (edgestrip_row.py interior shift) or re-shape")
        out.append(f"WARN {CHECK} summary: {len(by)} type(s), {len(rows)} window side(s) under the {strip_um}-um strip "
                   f"(>= {min_bits} bits) in {time.time() - t0:.1f} s")
        return out
    except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]
