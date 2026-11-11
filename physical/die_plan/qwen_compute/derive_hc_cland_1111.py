#!/usr/bin/env python3
"""DIE-QC-97 HC-CLAND 11-11: re-runnable derivation of the hc1/hc2 landing-ring form from the CURRENT plan geometry.

Use it after any core / band move (e.g. VIS-TRIAGE-QC's clean-slate placement round).  It reads the plan as it is now
and never hard-codes a rect.  Running it twice gives the same output: the second run is byte-identical.

1. Ring-flop strip rows: budgets.cland_strip_rows_types[base] = ROWS for each base in BASES (sle_hc1 slw_hc1 sle_hc2
   slw_hc2).  gen_phys._cland_strip_rows then exports OT_CLAND_STRIP_ROWS=3 for every type of those bases.  A base
   already set to ROWS is left alone; a base set to another value -> SystemExit (merge by hand).
2. b_hw_i face home, for each type of those bases.  A b_hw_i band "off home" has its face-crossing demand above its
   strip cap, or more than half its bits outside the band's span along the face.  Such a band is re-sited with the same
   size on its own face:
   - Candidates are the face-parallel offsets on the 2.16-um grid, from the 17.28-um margin.  They are ranked by
     crossing demand, then inset from the face, then distance from the window-centred offset.
   - The first candidate is taken that is clear of every planning obstacle (cland_band_fit.obstacles: macros/cores +
     clearance, keepouts, die islands, reserved clock sites, ft station sites, PHY supply, START/status groups) and
     within the 402.84-um pin reach.
   - Other ring bands may be in the way, if each one can be re-sited.  Each displaced band keeps its size and its own
     face, and takes the legal rect with the least Manhattan shift from its old rect (2.16-um grid).  Legal means:
     clear of the obstacles, 2.16 um from every other band, in reach, and within its own strip crossing cap.
   - Collector reset-relay sites are not obstacles unless budgets.cland_avoid_reset_types names the type (the compose
     rule; the old bands overlap them too).
   - Each moved band gets rect_um, max_pin_to_band_hop_um, resized_from_um (its old rect) and a resize note.  Every
     other field, band and type stays byte-identical.
   - No legal home -> SystemExit (no partial plan).
On the 11-11 lineage (aace4c2668fc / 886a8ffae774) this reproduces HC1-STRIP exactly.  Four hc1 types get
b_hw_i [108.528,17.28,380.496,62.64] -> [17.28,17.28,289.248,62.64] and rs_n1 [17.28,17.28,69.12,106.368] ->
[17.28,64.8,69.12,153.888].  All hc2 b_hw_i bands are already home.
3. --widen (HC-WIDEN, opt-in): runs before step 2.
   - Each type's b_hw_i window takes the free length at the end of its face, to the 17.28-um margin.  Delta is in
     0.192-um steps, the M5/M7 track lcm.  hc2 S [4.32,276.288] -> [4.32,499.776]; hc1 -> [4.32,409.344].
   - Every window after it on that face shifts by the same delta, keeping gaps and order.
   - Each moved window's seam-partner window (the sle_ctl N face) is mapped through the placement frames.  All parts
     of a partner type must agree, and the partner's old window must equal the seam image of the old one; else
     SystemExit.
   - The landing face pins (fclk_/cland_fstart_ in/out) shift by the window-centre delta.  The collector sources move
     to the new window centre.
   - --sidecar IN OUT copies the moved collector-source xy into the sidecar, because strict bind reads them there.
   - Step 2 then treats each widened b_hw_i as off home.  Besides the old shape it tries equal-area bands that are
     longer and shallower (depth >= 1/3), ranked by: crossing within half the strip cap, then nearest the face, then
     deepest.
   GRT-only probes on the 11-09 kits (adj 0.25, MEASURED): hc2 clcc5e3e61 5235 -> 0; hc1 cl7d360508 22032 -> 0
   (widen + rows 4 + logic lift; see the HC-CLAND report for the per-arm table).
    derive_hc_cland_1111.py PLAN.json OUT.json [--rows 3] [--bases sle_hc1,slw_hc1,sle_hc2,slw_hc2] [--widen]
        [--sidecar SIDECAR_IN SIDECAR_OUT]
       -> prints {keys, moved, widen, sha256_in, sha256_out[, sidecar_*]}; OUT keeps PLAN's JSON style
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))

ROWS = 3
BASES = ("sle_hc1", "slw_hc1", "sle_hc2", "slw_hc2")
BUS = "b_hw_i"
G = 2.16
MARGIN = 17.28
REACH = 405 - 2.16
MAX_INSET_STEPS = 20
MAX_SHIFT_STEPS = 120
OFF_WINDOW = 0.5
NOTE = "DIE-QC-97 HC-CLAND 11-11: derived face home (b_hw_i over its own pins; displaced bands least-shift, same face)"


def _ov(a, o, pad=0.0):
    return (min(a[2], o[2] + pad) > max(a[0], o[0] - pad) + 1e-6 and
            min(a[3], o[3] + pad) > max(a[1], o[1] - pad) + 1e-6)


def _r(v):
    return round(v, 6)


class TypeCtx:
    def __init__(self, raw, plan_obj, tn):
        import clock_landing_plan as C
        import cland_band_fit as F
        self.C, self.F = C, F
        self.raw, self.P, self.tn = raw, plan_obj, tn
        self.t = raw["partition_types"][tn]
        self.lc = self.t["clock"]["landing_contract"]
        self.w, self.h = self.t["outline_um"]
        tree = self.lc.get("collector_tree")
        avoid = C._reset_sites_for_type(raw, tn, tree, self.lc.get("base_type"))
        self.skip = set() if avoid else {tuple(r) for r in C.reset_site_rects(tree)}

    def movable(self, k):
        b = self.lc["bands"][k]
        return (k != BUS and not k.startswith("monitor_") and b.get("rect_um") and not b.get("hard_core")
                and not any(x in b for x in ("rects_um", "ff_rect_um", "freg_rect_um", "native_role_banks"))
                and self.C._has_type_geom(self.t, k))

    def fixed_obstacles(self, bands):
        """planning obstacles except ring bands and (compose rule) reset-relay sites"""
        lc = copy.deepcopy(self.lc)
        lc["bands"] = {}
        return [o for o in self.F.obstacles(self.t, self.tn, self.P, None, lc, None) if tuple(o) not in self.skip]

    def legal(self, bus, rect, fixed, others):
        if rect[0] < MARGIN - 1e-6 or rect[1] < MARGIN - 1e-6 or rect[2] > self.w - MARGIN + 1e-6 or \
                rect[3] > self.h - MARGIN + 1e-6:
            return None
        px, py = self.C._bus_xy(self.t, bus)
        hop = max(abs(x - px) + abs(y - py) for x in (rect[0], rect[2]) for y in (rect[1], rect[3]))
        if hop > REACH + 1e-6:
            return None
        dm, cap = self.C.face_crossing(self.t, bus, rect, int(self.lc["bands"][bus]["width"]))
        if dm > cap + 1e-6:
            return None
        if any(_ov(rect, o) for o in fixed) or any(_ov(rect, o, G - 1e-3) for o in others):
            return None
        return _r(hop)

    def off_home(self):
        b = self.lc["bands"].get(BUS)
        if not b or not b.get("rect_um") or not self.C._has_type_geom(self.t, BUS):
            return False
        dm, cap = self.C.face_crossing(self.t, BUS, b["rect_um"], int(b["width"]))
        return dm > cap + 1e-6 or dm > OFF_WINDOW * int(b["width"])

    def home_candidates(self):
        b = self.lc["bands"][BUS]
        r = b["rect_um"]
        geo = self.C._bus_geom(self.t, BUS)
        f, (lo, hi) = geo["face"], geo["window_um"]
        along = self.h if f in "EW" else self.w
        L = (r[3] - r[1]) if f in "EW" else (r[2] - r[0])
        D = (r[2] - r[0]) if f in "EW" else (r[3] - r[1])
        shapes = [(L, D)]
        # a window wider than the band (HC-WIDEN): also equal-area bands that are longer and shallower, up to the
        # window span inside the margin, depth down to a third of the old one (2.16-um grid)
        span = min(hi, along - MARGIN) - max(lo, MARGIN)
        if span > L + 1e-6:
            area = L * D
            for k in range(int(round(D / G)), 0, -1):
                d = k * G
                if d < D / 3 - 1e-6:
                    break
                ln = math.ceil(area / d / G - 1e-6) * G
                if ln > min(math.ceil(span / G - 1e-6) * G, along - 2 * MARGIN) + 1e-6:
                    continue
                shapes.append((_r(ln), _r(d)))
        out = []
        for L, D in shapes:
            ideal = min(max(MARGIN, (lo + hi - L) / 2), along - MARGIN - L)
            n = int((along - 2 * MARGIN - L) / G + 1e-6)
            for k in range(n + 1):
                s = MARGIN + k * G
                for j in range(MAX_INSET_STEPS + 1):
                    i = MARGIN + j * G
                    rect = ([i, s, i + D, s + L] if f == "W" else [self.w - i - D, s, self.w - i, s + L] if f == "E" else
                            [s, i, s + L, i + D] if f == "S" else [s, self.h - i - D, s + L, self.h - i])
                    rect = [_r(v) for v in rect]
                    dm, cap = self.C.face_crossing(self.t, BUS, rect, int(b["width"]))
                    # one shape: crossing, inset, centring (unchanged rank).  Several (widened window): crossing
                    # within half the strip cap, then nearest the face, then the deepest band (the ring keeps rows).
                    key = ((round(dm, 3), j, abs(s - ideal)) if len(shapes) == 1 else
                           (dm > cap / 2 + 1e-6, j, -D, round(dm, 3), abs(s - ideal)))
                    out.append((key, rect))
        out.sort(key=lambda c: c[0])
        return [c[1] for c in out]

    def resite(self, k, fixed, others):
        r = self.lc["bands"][k]["rect_um"]
        best = None
        for dx in range(-MAX_SHIFT_STEPS, MAX_SHIFT_STEPS + 1):
            for dy in range(-MAX_SHIFT_STEPS, MAX_SHIFT_STEPS + 1):
                cost = abs(dx) + abs(dy)
                if best is not None and cost >= best[0]:
                    continue
                rect = [_r(r[0] + dx * G), _r(r[1] + dy * G), _r(r[2] + dx * G), _r(r[3] + dy * G)]
                hop = self.legal(k, rect, fixed, others)
                if hop is not None and (best is None or (cost, rect) < best[:2]):
                    best = (cost, rect, hop)
        return best

    def derive(self):
        bands = self.lc["bands"]
        fixed = self.fixed_obstacles(bands)
        for rect in self.home_candidates():
            in_way = sorted(k for k, o in bands.items() if k != BUS and o.get("rect_um") and _ov(rect, o["rect_um"], G - 1e-3))
            if any(not self.movable(k) for k in in_way):
                continue
            stay = [o["rect_um"] for k, o in bands.items() if k != BUS and k not in in_way and o.get("rect_um")]
            stay += [rr for k, o in bands.items() if k != BUS and o.get("rects_um") for rr in o["rects_um"]]
            hop = self.legal(BUS, rect, fixed, stay)
            if hop is None:
                continue
            new = {BUS: (rect, hop)}
            placed = stay + [rect]
            ok = True
            for k in sorted(in_way, key=lambda k: (-int(bands[k].get("width") or 0), k)):
                got = self.resite(k, fixed, placed)
                if got is None:
                    ok = False
                    break
                new[k] = (got[1], got[2])
                placed.append(got[1])
            if ok:
                return new
        raise SystemExit(f"HC-CLAND: {self.tn}: no legal face home for {BUS} {bands[BUS]['rect_um']}")


WG = 0.192        # window / pin shifts in multiples of 0.192 um = lcm of the M5 (0.048) and M7 (0.064) track pitch


def _face_items(t, f):
    """[(name as ports use it, holder dict, window key)] of every bus / ft-slot side on type face f with a window"""
    out = [(b["name"], b, "window_um") for b in t.get("buses", []) if b.get("face") == f and b.get("window_um")]
    for s in t.get("ft_slots", []):
        for suffix, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
            if s.get(fk) == f and s.get(wk):
                out.append((s["name"] + suffix, s, wk))
    return sorted(out, key=lambda it: it[1][it[2]][0])


def _shift_lc(t, f, name, d_mid, new_mid=None, old_mid=None):
    """move the landing-contract face pins / collector sources of bus `name` on face f along the face by d_mid"""
    ax = 0 if f in "NS" else 1
    lc = (t.get("clock") or {}).get("landing_contract") or {}
    n = 0
    for p in lc.get("pins", []) or []:
        nm = p.get("name", "")
        if any(nm == pre + name for pre in ("fclk_in_", "fclk_out_", "cland_fstart_in_", "cland_fstart_out_")):
            p["xy_um"][ax] = _r(p["xy_um"][ax] + d_mid)
            n += 1
    for s in lc.get("collector_local_sources", []) or []:
        if s.get("name") != name:
            continue
        for k in ("xy_um", "pin_xy_um"):
            if s.get(k):
                exact = old_mid is not None and abs(s[k][ax] - old_mid) < 1e-6
                s[k][ax] = _r(new_mid if exact else s[k][ax] + d_mid)
        for q in s.get("status_pins_xy_um", []) or []:
            q[ax] = _r(q[ax] + d_mid)
        n += 1
    return n


def widen(raw, types, bus=BUS):
    """HC-WIDEN: give `bus` the free length at the end of its face.  Every window after it on that face shifts by the
    same delta, gaps and order kept.  The seam partner side of every moved window is mapped through the placement
    frames; all parts of a partner type must agree, else SystemExit.  The face pins and collector sources follow."""
    import schema as S
    P = S.Plan(copy.deepcopy(raw))
    moved = {}                                   # (type, bus name) -> (old window, new window, face)
    for tn in types:
        t = raw["partition_types"][tn]
        b = next((x for x in t.get("buses", []) if x["name"] == bus and x.get("window_um")), None)
        if b is None:
            continue
        f = b["face"]
        along = t["outline_um"][0 if f in "NS" else 1]
        items = _face_items(t, f)
        lo0, hi0 = b["window_um"]
        delta = math.floor(((along - MARGIN) - max(h[w][1] for _, h, w in items)) / WG + 1e-6) * WG
        if delta < G:
            continue
        for name, h, wk in items:
            lo, hi = h[wk]
            if name == bus:
                new = [lo, _r(hi + delta)]
            elif lo >= hi0 - 1e-6:
                new = [_r(lo + delta), _r(hi + delta)]
            else:
                continue
            moved[(tn, name)] = (list(h[wk]), new, f)
    for (tn, name), (old, new, f) in moved.items():
        t = raw["partition_types"][tn]
        h, wk = next((h, wk) for nm, h, wk in _face_items(t, f) if nm == name)
        h[wk] = list(new)
        om, nm_ = (old[0] + old[1]) / 2, (new[0] + new[1]) / 2
        _shift_lc(t, f, name, round((nm_ - om) / WG) * WG, nm_, om)
    partner = {}                                 # (partner type, bus) -> (old mapped, new mapped, face)
    for pr in raw.get("ports", []):
        for side, other in (("src", "dst"), ("dst", "src")):
            pn = pr[side]["part"]
            if pn not in P.parts or (P.parts[pn]["type"], pr[side]["bus"]) not in moved:
                continue
            tn = P.parts[pn]["type"]
            old, new, f = moved[(tn, pr[side]["bus"])]
            qpn, qbus = pr[other]["part"], pr[other]["bus"]
            if qpn not in P.parts:
                raise SystemExit(f"HC-WIDEN: {pn}.{pr[side]['bus']} faces {qpn}, not a partition")
            qt = P.parts[qpn]["type"]
            if (qt, qbus) in moved:
                continue
            w, hgt = raw["partition_types"][tn]["outline_um"]
            edge = {"S": 0.0, "N": hgt, "W": 0.0, "E": w}[f]
            qf = P.type_face(qpn, S.OPP[P.die_face(pn, f)])
            ax = 0 if qf in "NS" else 1

            def mp(win):
                pts = [(v, edge) if f in "NS" else (edge, v) for v in win]
                return sorted(_r(P.to_type(qpn, P.to_die(pn, q))[ax]) for q in pts)
            got = (mp(old), mp(new), qf)
            if (qt, qbus) in partner and any(abs(a - b) > 1e-4 for a, b in zip(partner[(qt, qbus)][1], got[1])):
                raise SystemExit(f"HC-WIDEN: partner {qt}.{qbus} gets two different windows "
                                 f"{partner[(qt, qbus)][1]} / {got[1]} (parts disagree)")
            partner[(qt, qbus)] = got
    for (qt, qbus), (old, new, qf) in partner.items():
        t = raw["partition_types"][qt]
        hit = [(h, wk) for nm, h, wk in _face_items(t, qf) if nm == qbus]
        for h, wk in hit:
            if any(abs(a - b) > 1e-3 for a, b in zip(h[wk], old)):
                raise SystemExit(f"HC-WIDEN: partner {qt}.{qbus} window {h[wk]} != seam image {old}")
            h[wk] = list(new)
        om, nm_ = (old[0] + old[1]) / 2, (new[0] + new[1]) / 2
        _shift_lc(t, qf, qbus, round((nm_ - om) / WG) * WG, nm_, om)
    # every widened window must stay clear of the other windows of its face (both sides)
    for tn in {k[0] for k in moved} | {k[0] for k in partner}:
        t = raw["partition_types"][tn]
        for f in "NSEW":
            ws = sorted(h[wk] for _, h, wk in _face_items(t, f))
            for a, b in zip(ws, ws[1:]):
                if b[0] < a[1] - 1e-6:
                    raise SystemExit(f"HC-WIDEN: {tn} face {f} windows overlap {a} / {b}")
    return {"windows": {f"{tn}.{n}": [o, nw] for (tn, n), (o, nw, _) in sorted(moved.items())},
            "partners": {f"{qt}.{qb}": [o, nw] for (qt, qb), (o, nw, _) in sorted(partner.items())}}


def sync_sidecar(raw, side, rep):
    """collector local_sources xy of every moved bus -> the plan's values (strict bind reads them from the sidecar)"""
    st = (side.get("collector") or {}).get("types") or {}
    n = 0
    for key in list(rep["windows"]) + list(rep["partners"]):
        tn, bus = key.split(".", 1)
        if tn not in st:
            continue
        plan_src = {s["name"]: s for s in raw["partition_types"][tn]["clock"]["landing_contract"].get(
            "collector_local_sources", []) or []}
        for s in st[tn].get("local_sources", []) or []:
            if s.get("name") == bus and bus in plan_src:
                for k in ("xy_um", "pin_xy_um", "status_pins_xy_um"):
                    if k in s and k in plan_src[bus] and s[k] != plan_src[bus][k]:
                        s[k] = copy.deepcopy(plan_src[bus][k])
                        n += 1
    return n


# DIE-QC-97 11-11 (lead ruling, two strikes): the strip-row / face-home form is NOT applied to the fw_v1 family.
# slw_fw_v1__cl51d45468 probes: rows 3 + logic lift -> GRT-0183 (maze router boxed in); rows 2 -> 568 overflow
# (kit 130).  Its 130 is a cland-ring jam at the N-face x_ctl_i band edge, routed to the cland ring form.  These types
# keep their base landing band and strip rows, whatever --bases says.
EXCLUDE_RE = re.compile(r"^(sle|slw)_fw_v1(__|$)")


def apply(raw, rows=ROWS, bases=BASES, widen_face=False):
    bad = [b for b in bases if EXCLUDE_RE.match(b)]
    if bad:
        raise SystemExit(f"HC-CLAND: {bad} are excluded from this form (fw_v1 two strikes)")
    types = sorted(t for t in raw.get("partition_types", {}) if t.split("__")[0] in bases and not EXCLUDE_RE.match(t))
    if not types:
        raise SystemExit(f"HC-CLAND: plan has no type of {bases}")
    bud = raw.setdefault("budgets", {})
    per = bud.get("cland_strip_rows_types")
    per = {} if per is None else per
    clash = {k: per[k] for k in list(bases) + types if k in per and per[k] != rows}
    if clash:
        raise SystemExit(f"HC-CLAND: cland_strip_rows_types already sets {clash} (merge by hand)")
    wrep = widen(raw, types) if widen_face else {"windows": {}, "partners": {}}
    import schema as S
    plan_obj = S.Plan(raw) if (raw.get("die") or {}).get("pg", {}).get("domains") and raw.get("partitions") else None
    moved = {}
    for tn in types:
        if not (raw["partition_types"][tn].get("clock") or {}).get("landing_contract"):
            continue
        ctx = TypeCtx(raw, plan_obj, tn)
        if not ctx.off_home() and f"{tn}.{BUS}" not in wrep["windows"]:
            continue
        new = ctx.derive()
        for k, (rect, hop) in sorted(new.items()):
            b = ctx.lc["bands"][k]
            moved.setdefault(tn, {})[k] = dict(old=list(b["rect_um"]), new=rect, hop_um=hop)
            b["resized_from_um"] = list(b["rect_um"])
            b["rect_um"] = rect
            b["max_pin_to_band_hop_um"] = hop
            b["resize"] = NOTE
    for b in bases:
        per[b] = rows
    bud["cland_strip_rows_types"] = per
    return raw, moved, wrep


def _dump(src, obj):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p, indent=1) + "\n"):
        if f(json.loads(src)).encode() == src:
            return f(obj).encode()
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--rows", type=int, default=ROWS)
    p.add_argument("--bases", default=",".join(BASES))
    p.add_argument("--widen", action="store_true", help="HC-WIDEN: b_hw_i takes the free end of its face (both seam sides)")
    p.add_argument("--sidecar", nargs=2, metavar=("SIDECAR_IN", "SIDECAR_OUT"),
                   help="copy the moved collector source xy into the sidecar (strict bind reads them there)")
    a = p.parse_args()
    src = Path(a.input).read_bytes()
    bases = tuple(x for x in a.bases.split(",") if x)
    raw, moved, wrep = apply(json.loads(src), a.rows, bases, a.widen)
    out = _dump(src, raw)
    Path(a.output).write_bytes(out)
    res = {"keys": {b: a.rows for b in bases}, "moved": moved, "widen": wrep,
           "sha256_in": hashlib.sha256(src).hexdigest(), "sha256_out": hashlib.sha256(out).hexdigest()}
    if a.sidecar:
        sb = Path(a.sidecar[0]).read_bytes()
        side = json.loads(sb)
        res["sidecar_changed"] = sync_sidecar(raw, side, wrep)
        so = _dump(sb, side)
        Path(a.sidecar[1]).write_bytes(so)
        res["sidecar_sha256_in"] = hashlib.sha256(sb).hexdigest()
        res["sidecar_sha256_out"] = hashlib.sha256(so).hexdigest()
    print(json.dumps(res))


if __name__ == "__main__":
    main()
