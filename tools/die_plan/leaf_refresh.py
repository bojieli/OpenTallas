#!/usr/bin/env python3
"""leaf_refresh.py -- the post-core_place refresh chain for leaf / kv_leaf types (FP-CONVERGE-S81, Fable review of leaf TEMPLATE v1).

core_place moves hard cores and re-sites stations / ft, but items that hang off a core stay at the OLD core position: core clock taps
(clock.taps kind core), relay_sites, collector_tree core_resets (pin_um / xy), and items a move leaves inside a core or outside the
outline (relay_sites, reach_fix_sinks, collector_tree.root / outs, collector_local_sources pins).  This tool, run on core_place's output
plan against the plan core_place started from:

  leaf_refresh.py run BASE_PLAN NEW_PLAN OUT --types a,b [--report R.json]
      (a) shift every item owned by a translated core (same orient) by the core's origin delta: core taps, core_resets pin_um / xy,
          relay_sites that sat within 30 um of that core in BASE;
      (b) legalise what is still inside a core (+1 um halo) or outside the outline (8 um inset): move to the nearest free 4.32 lattice
          point (hub_repack.Raster), keeping the depth (only xy changes);
      (c) report per type before / after: taps_stale (core taps farther than 1 um from base tap + delta), items in core, items outside.
  After it, run reset_anchor.py record --repick over the touched types (see `anchor_cmd`) and PRE ANCHORDRY must read clean.
A core whose orient changed (flip) is NOT translated: its items are legalised only and counted as `flipped`.
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
G = 4.32
INSET = 8.0
HALO = 1.0
OWN_UM = 30.0


def core_rects(t):
    out = {}
    for h in t.get("hard_cores") or []:
        o, d = h.get("origin_um"), h.get("outline_um")
        if not o or not d:
            continue
        w, hh = (d[1], d[0]) if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90") else d
        out[h["inst"]] = (o[0], o[1], o[0] + w, o[1] + hh, h.get("orient", "R0"))
    return out


def deltas(base_t, new_t):
    """{inst: (dx, dy) | None}: origin delta of a moved core, None when its orient changed; unmoved cores absent"""
    b, n = core_rects(base_t), core_rects(new_t)
    out = {}
    for k, v in n.items():
        if k not in b:
            continue
        if v[4] != b[k][4]:
            out[k] = None
        elif abs(v[0] - b[k][0]) > 1e-6 or abs(v[1] - b[k][1]) > 1e-6:
            out[k] = (round(v[0] - b[k][0], 4), round(v[1] - b[k][1], 4))
    return out


def inside(r, p, halo=0.0):
    return r[0] - halo < p[0] < r[2] + halo and r[1] - halo < p[1] < r[3] + halo


def owner_core(rects, p, tol=OWN_UM):
    """instance whose rect (grown by tol) holds p, nearest by rect distance"""
    best = None
    for k, r in rects.items():
        dx = max(r[0] - p[0], 0, p[0] - r[2])
        dy = max(r[1] - p[1], 0, p[1] - r[3])
        d = max(dx, dy)
        if d <= tol and (best is None or d < best[0]):
            best = (d, k)
    return best[1] if best else None


class Legal:
    def __init__(self, t):
        import hub_repack as HR
        W, H = t["outline_um"]
        self.W, self.H = W, H
        self.rects = [r[:4] for r in core_rects(t).values()]
        self.R = HR.Raster(W, H, self.rects, halo=HALO)

    def ok(self, p):
        return (INSET <= p[0] <= self.W - INSET and INSET <= p[1] <= self.H - INSET
                and not any(inside(r, p, HALO) for r in self.rects))

    def nearest(self, p, rmax=120):
        if self.ok(p):
            return (round(p[0], 3), round(p[1], 3))
        i0, j0 = int(round(p[0] / G)), int(round(p[1] / G))
        best = None
        for d in range(1, rmax + 1):
            for di in range(-d, d + 1):
                for dj in (-(d - abs(di)), d - abs(di)):
                    q = (round((i0 + di) * G, 3), round((j0 + dj) * G, 3))
                    if self.ok(q) and (best is None or abs(q[0] - p[0]) + abs(q[1] - p[1]) < best[0]):
                        best = (abs(q[0] - p[0]) + abs(q[1] - p[1]), q)
            if best:
                return best[1]
        return None


def _pts(t):
    """[(label, getter, setter)] of every xy item the refresh handles on a type"""
    out = []
    ck = t.get("clock") or {}
    for i, tp in enumerate(ck.get("taps") or []):
        if tp.get("kind") == "core" and tp.get("xy"):
            out.append((("core_tap", tp.get("name")), tp, "xy"))
    for k in (t.get("relay_sites") or {}):
        out.append((("relay_site", k), t["relay_sites"], k))
    lc = ck.get("landing_contract") or {}
    ct = lc.get("collector_tree") or {}
    for i, r in enumerate(ct.get("core_resets") or []):
        for f in ("pin_um", "xy"):
            if r.get(f):
                out.append((("core_reset", r.get("inst"), f), r, f))
    if ct.get("root"):
        out.append((("collector_root",), ct, "root"))
    for i, o in enumerate(ct.get("outs") or []):
        out.append((("collector_out", i), ct["outs"], i))
    for i, s in enumerate(ck.get("reach_fix_sinks") or []):
        out.append((("reach_fix_sink", i), ck["reach_fix_sinks"], i))
    return out


def _get(c, k):
    return c[k]


def stats(t, rects, legal):
    n = dict(in_core=0, outside=0, items=0)
    for lab, c, k in _pts(t):
        p = c[k]
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        n["items"] += 1
        if lab[0] == "core_tap":
            continue
        if any(inside(r[:4], p, 0.0) for r in rects.values()) and lab[0] not in ("core_reset",):
            n["in_core"] += 1
        if not (0 <= p[0] <= legal.W and 0 <= p[1] <= legal.H):
            n["outside"] += 1
    return n


def rect_dist(r, p):
    return max(r[0] - p[0], 0, p[0] - r[2], r[1] - p[1], 0, p[1] - r[3])


def stale_findings(base_t, new_t, own=OWN_UM):
    """FP-CONVERGE-S81 (Fable, grown t10: u_vsw.clk 195 um and g_ln[12].clk 504 um from their core, rst_n[16] 448 um from
    g_ln[12]): items that must sit at their owner core but are > own um from it -> [str].  Core taps: the core named in the
    tap name.  Relay sites: the core that held the relay in BASE (owner_core) - once the core moved, the relay must follow."""
    brects, nrects = core_rects(base_t), core_rects(new_t)
    bad = []
    base_items = {lab: c[k] for lab, c, k in _pts(base_t)}
    for lab, c, k in _pts(new_t):
        p = c[k]
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        inst = None
        if lab[0] == "core_tap":
            inst = str(lab[1]).rsplit(".", 1)[0]
        elif lab[0] == "relay_site":
            b = base_items.get(lab)
            inst = owner_core(brects, b) if b else None
        if not inst or inst not in nrects:
            continue
        d = rect_dist(nrects[inst], p)
        if d > own:
            bad.append("STALE %s %s %.1f um from %s (> %.0f)" % (lab[0], lab[1], d, inst, own))
    return bad


def refresh_type(base_t, new_t):
    """mutates new_t; -> report dict"""
    rep = dict(shifted=0, legalised=0, flipped=0, unplaced=0)
    dl = deltas(base_t, new_t)
    brects, nrects = core_rects(base_t), core_rects(new_t)
    legal = Legal(new_t)
    rep["before"] = stats(new_t, nrects, legal)
    base_items = {lab: copy.deepcopy(c[k]) for lab, c, k in _pts(base_t)}
    # (a) translate
    for lab, c, k in _pts(new_t):
        p = c[k]
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        inst = None
        if lab[0] == "core_tap":
            inst = str(lab[1]).rsplit(".", 1)[0]
        elif lab[0] == "core_reset":
            inst = lab[1]
        elif lab[0] == "relay_site":
            b = base_items.get(lab)
            inst = owner_core(brects, b) if b else None
        if inst is None or inst not in dl:
            continue
        if dl[inst] is None:
            rep["flipped"] += 1
            continue
        q = list(p)
        # items still at the BASE position ride with the core; an item core_place already moved is left alone
        b = base_items.get(lab)
        if b is not None and abs(p[0] - b[0]) < 1e-6 and abs(p[1] - b[1]) < 1e-6:
            q[0] = round(p[0] + dl[inst][0], 3)
            q[1] = round(p[1] + dl[inst][1], 3)
            c[k] = q if isinstance(p, list) else tuple(q)
            rep["shifted"] += 1
    # (b) legalise (never core taps: they sit at the core's clock pin, inside the macro rect by construction; core_reset points are pins)
    for lab, c, k in _pts(new_t):
        if lab[0] in ("core_tap", "core_reset"):
            continue
        p = c[k]
        if not isinstance(p, (list, tuple)) or len(p) < 2 or legal.ok(p):
            continue
        q = legal.nearest(p)
        if q is None:
            rep["unplaced"] += 1
            continue
        c[k] = [q[0], q[1]] + list(p[2:])
        rep["legalised"] += 1
    rep["after"] = stats(new_t, nrects, legal)
    rep["stale"] = stale_findings(base_t, new_t)
    return rep


def run(base_raw, new_raw, types):
    out = copy.deepcopy(new_raw)
    rep = {}
    for tn in types:
        rep[tn] = refresh_type(base_raw["partition_types"][tn], out["partition_types"][tn])
    return out, rep


def anchor_cmd(plan, out, types):
    return ["python3", "-I", "tools/die_plan/reset_anchor.py", "record", plan, out, "--types", ",".join(types), "--repick"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("base")
    ap.add_argument("new")
    ap.add_argument("out")
    ap.add_argument("--types", required=True)
    ap.add_argument("--report")
    ap.add_argument("--allow-stale", action="store_true", help="report STALE items (core tap / relay seat > 30 um from its owner core) without failing")
    a = ap.parse_args(argv)
    base = json.loads(Path(a.base).read_text())
    new = json.loads(Path(a.new).read_text())
    types = [t for t in a.types.split(",") if t]
    out, rep = run(base, new, types)
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    for tn, r in rep.items():
        print(f"{tn}: shifted {r['shifted']} legalised {r['legalised']} flipped {r['flipped']} unplaced {r['unplaced']} "
              f"in_core {r['before']['in_core']}->{r['after']['in_core']} outside {r['before']['outside']}->{r['after']['outside']}")
    stale = [(tn, x) for tn, r in rep.items() for x in r.get("stale", [])]
    for tn, x in stale:
        print(f"{tn}: {x}")
    print("NEXT: " + " ".join(anchor_cmd(a.out, a.out.replace(".json", "_r.json"), types)))
    return 1 if stale and not a.allow_stale else 0


if __name__ == "__main__":
    sys.exit(main())
