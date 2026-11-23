"""ADV-PATH-SEAT (PRECHECK-R2, COORD 11-22 22:4x; an estimator, never a gate).

Two plan-geometry estimates of a register-to-register path that one 833-ps cycle cannot cover, read from partition_types
only (type frame, um; hard_cores[] + placed contents[] macros are the blockages, halo_um added):

  SEAT-DETOUR  a planned station hop (ft_slots: in pin -> regs_um[0..] -> out pin; internal_stations bus:<b> rows: bus pin
               <-> regs_um chain, core rows: consecutive regs_um) whose straight Manhattan span is short but whose shortest
               rectilinear path around the macros (cbc_rules.detour_um, exact on the Hanan grid) is longer than the reach
               (cbc_rules.REACH_GATE_UM, 405 um), at least DETOUR_MIN_UM longer than the span and >= DETOUR_RATIO x it.
               Fix: re-seat the register on the pin's side of the macro (or add a station on the detour), at plan time.
  STAGE-DEPTH  estimated cells on the path = logic + repeaters, repeaters = path / REPEATER_UM (ASAP7 repair_design pitch,
               calibrated on the two 11-22 PLACE-SETUP-STOP paths: lepw_mus_C t1 2,249.5 um / 22 buffers = 102 um, leaf
               t15 1,885 um / 14 = 135 um), flagged over STAGE_MAX (20) cells.  Paths: (i) every station hop above (logic
               0), (ii) a bus pass-through: an in bus and an out bus of the same width (>= PASS_MIN_BITS) on OPPOSITE faces
               with no internal_stations row and no ft slot on either (a ring stop / pass datapath registered at both
               pins), logic PASS_LOGIC cells.  Real positive: S81 dsdv_slice_lepw_mus_C__t1 (kit wave 18a2688b741 @1,
               J7 a6771d121e95 geometry) iw[5] -> roe_d[8] (ot_s81sl_rstopt: iw = ri_w input flops at lepk_i0 W, roe_d =
               ro_e at xring_o0 E): span 2,249.5 um, 28 stages = 2 flops + 4 logic (AND3 NAND2 XNOR2 OAI22) + 22
               repeaters, -649.5 ps post-place.  The 28 is NOT synth logic depth (4 levels; depth_scan / synth reports
               would not see it): it is repeaters on a pin-to-pin span, so plan geometry is the static input.
               Fix: a register stage mid-way (XMID-style input stage + stop-centre flops, or internal_stations on the bus)
               so every hop is <= 405 um, or put the two windows on one face / closer.

Not reproduced (11-22): S81 ot_s81sl_leaf__t15 @2 ft0_i[16] -> u_ft_ft0_o_0/q[16] (span 5.2 um, path 1,885 um, 16 stages).
The plan seat is clear: pin (9.82, 1226.88), FIRM face flop (8.64, 1221.75), no macro or band in the W column; the
3_detailed_place.rpt path is port -> 7 BUFx12f -> port buffer input465 -> 7 BUFx16f (u_ft_ft0_o_0/wire*) -> flop, a
round trip of 2 x ~942 um = down to the latitude of the ft0 station-3 seat (y 285): a kit placement-order effect, not a plan
seat behind a macro.  This module stays quiet on that type (test_adv_path_seat asserts it).
"""
import time

CHECK = "ADV-PATH-SEAT"
REACH_UM = 405.0              # cbc_rules.REACH_GATE_UM (registered hop, 12.1e)
DETOUR_MIN_UM = 200.0         # detour - span
DETOUR_RATIO = 2.0            # detour / span (J7 a6771d121e95: 1.5x -> 455 hops, 2x -> 196, 2.5x -> 74)
REPEATER_UM = 110.0           # um per repair repeater (102 / 135 um on the two 11-22 positives)
STAGE_MAX = 20                # cells on one 833-ps path
PASS_LOGIC = 4                # logic cells on a pass-through (lepw_mus_C rstopt e_nx: 4)
PASS_MIN_BITS = 32
MAX_LINES = 20
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def _cbc(tree=None):
    """tools/die_plan/cbc_rules (sibling; else the tree's)."""
    import os
    import sys
    for d in [None, os.path.dirname(os.path.abspath(__file__))] + ([os.path.join(str(tree), "tools", "die_plan")] if tree else []):
        if d is not None:
            if not os.path.isfile(os.path.join(d, "cbc_rules.py")):
                continue
            sys.path.insert(0, d)
        try:
            import cbc_rules as C
            return C
        except Exception:
            continue
        finally:
            if d is not None and sys.path and sys.path[0] == d:
                sys.path.pop(0)
    return None


def _xy(p):
    try:
        if isinstance(p[0], bool) or isinstance(p[1], bool):
            return None
        return float(p[0]), float(p[1])
    except (TypeError, ValueError, IndexError, KeyError):
        return None


def blockages(t):
    """[(name, x0, y0, x1, y1)] hard cores + placed contents macros (an entry with a lef; a soft content slot such as
    serdes u_phy blocks only through its physical_parts[]), grown by halo_um."""
    out = []

    def add(name, c):
        o, s = _xy(c.get("origin_um") or ()), _xy(c.get("outline_um") or ())
        if not o or not s or s[0] <= 0 or s[1] <= 0:
            return
        try:
            h = float(c.get("halo_um") or 0.0)
        except (TypeError, ValueError):
            h = 0.0
        out.append((name, o[0] - h, o[1] - h, o[0] + s[0] + h, o[1] + s[1] + h))

    for c in t.get("hard_cores") or []:
        if isinstance(c, dict):
            add(str(c.get("inst", "?")), c)
    for c in t.get("contents") or []:
        if not isinstance(c, dict):
            continue
        parts = [q for q in c.get("physical_parts") or [] if isinstance(q, dict)]
        if parts:
            for q in parts:
                add(str(q.get("physical_inst") or c.get("inst", "?")), q)
        elif c.get("lef"):
            add(str(c.get("inst", "?")), c)
    return out


def frame(outline, eps=0.009):
    """four blockers just outside the outline (detour_um grows rects by 0.01 um, so the grown frame overlaps a core grown off the edge: no 0.001-um slit; an edge pin walks 0.001 um in), so no
    path leaves the partition round a core that touches its edge."""
    try:
        W, H = float(outline[0]), float(outline[1])
    except (TypeError, ValueError, IndexError):
        return []
    m = 1000.0
    return [(-m, -m, -eps, H + m), (W + eps, -m, W + m, H + m), (-eps, -m, W + eps, -eps), (-eps, H + eps, W + eps, H + m)]


def pin_xy(face, win, outline):
    """centre of a face window (type frame)."""
    try:
        c = (float(win[0]) + float(win[1])) / 2.0
        W, H = float(outline[0]), float(outline[1])
    except (TypeError, ValueError, IndexError):
        return None
    return {"N": (c, H), "S": (c, 0.0), "W": (0.0, c), "E": (W, c)}.get(str(face))


def chains(t):
    """[(label, [(point name, (x, y))...], div)] of planned register chains of one type; div = hops the kit splits a
    siteless ft slot into (stations without regs_um: the kit sites them, evenly along the pin-to-pin path), else 1."""
    out = []
    ol = t.get("outline_um") or (0, 0)
    for sl in t.get("ft_slots") or []:
        if not isinstance(sl, dict):
            continue
        pts = []
        pi = pin_xy(sl.get("in_face"), sl.get("in_window_um") or (), ol)
        if pi:
            pts.append(("pin_in", pi))
        for j, p in enumerate(sl.get("regs_um") or []):
            q = _xy(p)
            if q:
                pts.append((f"regs_um[{j}]", q))
        po = pin_xy(sl.get("out_face"), sl.get("out_window_um") or sl.get("in_window_um") or (), ol)
        if po:
            pts.append(("pin_out", po))
        try:
            ns = int(sl.get("stations") or 0)
        except (TypeError, ValueError):
            ns = 0
        siteless = not any(n.startswith("regs") for n, _ in pts)
        out.append((f"ft_slots[{sl.get('name')}]", pts, ns + 1 if siteless else 1))
    buses = {b.get("name"): b for b in t.get("buses") or [] if isinstance(b, dict)}
    for st in t.get("internal_stations") or []:
        if not isinstance(st, dict):
            continue
        conn = str(st.get("conn", ""))
        pts = [(f"regs_um[{j}]", q) for j, q in enumerate(_xy(p) for p in st.get("regs_um") or []) if q]
        if conn.startswith("bus:"):
            b = buses.get(conn[4:])
            pp = pin_xy(b.get("face"), b.get("window_um") or (), ol) if b else None
            if pp:
                pts = [("pin", pp)] + pts if b.get("dir") == "in" else pts + [("pin", pp)]
        out.append((f"internal_stations[{conn}]", pts, 1))
    return out


def _straight(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hop_path(C, a, b, rects):
    """(straight, path) ; path = shortest rectilinear path outside the rects searched up to a cap (lower bound = cap)."""
    s = _straight(a, b)
    if not rects:
        return s, s
    cap = max(4.0 * s, s + 2.0 * REACH_UM)
    d = C.detour_um(a, b, rects, cap=cap)
    return s, (cap if d == float("inf") else d)


def pass_pairs(t):
    """[(in bus, out bus, a, b)] same-width data buses on opposite faces with no station row / ft slot."""
    ol = t.get("outline_um") or (0, 0)
    staged = {str(st.get("conn", ""))[4:] for st in t.get("internal_stations") or [] if isinstance(st, dict)
              and str(st.get("conn", "")).startswith("bus:")}
    ins, outs = [], []
    for b in t.get("buses") or []:
        if not isinstance(b, dict) or b.get("name") in staged or (b.get("kind") not in (None, "data")):
            continue
        try:
            w = int(b.get("width") or 0)
        except (TypeError, ValueError):
            continue
        if w < PASS_MIN_BITS:
            continue
        p = pin_xy(b.get("face"), b.get("window_um") or (), ol)
        if p:
            (ins if b.get("dir") == "in" else outs if b.get("dir") == "out" else []).append((b["name"], w, b.get("face"), p))
    out = []
    for ni, wi, fi, pi in ins:
        for no, wo, fo, po in outs:
            if wi == wo and OPP.get(fi) == fo:
                out.append((ni, no, pi, po))
    return out


def _f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def findings(raw, plan_path, tree=None, **kw):
    """WARN ADV-PATH-SEAT lines (capped) + one summary line; never raises."""
    try:
        t0 = time.time()
        C = _cbc(tree)
        if C is None or not hasattr(C, "detour_um"):
            return [f"WARN {CHECK} not checked: cbc_rules.detour_um not importable"]
        reach = float(getattr(C, "REACH_GATE_UM", REACH_UM))
        types = raw.get("partition_types") if isinstance(raw, dict) else None
        if not types:
            return [f"WARN {CHECK} not checked: plan has no partition_types"]
        used = {p.get("type") for p in raw.get("partitions") or [] if isinstance(p, dict)}
        det, stg, npass_seen = {}, {}, 0
        nhops = 0
        for tn, t in types.items():
            if not isinstance(t, dict) or t.get("hard") is True or (used and tn not in used):
                continue
            rects = [r[1:] for r in blockages(t)]
            rects = rects + frame(t.get("outline_um")) if rects else rects
            memo = {}
            for label, pts, div in chains(t):
                for (na, a), (nb, b) in zip(pts, pts[1:]):
                    nhops += 1
                    k = (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
                    if k not in memo:
                        memo[k] = hop_path(C, a, b, rects)
                    s, d = memo[k]
                    g = k                            # one hop shared by several rows / types is one finding
                    if div > 1:                      # kit-sited stations: only the per-hop length is known
                        s, d = s / div, d / div
                        na, nb = f"{na} (1/{div}: {div - 1} kit-sited stations)", nb
                    elif d > reach and d - s >= DETOUR_MIN_UM and d >= DETOUR_RATIO * max(s, 1e-6):
                        r = det.setdefault(g, [d - s, label, na, a, nb, b, s, d, [], 0])
                        r[9] += 1
                        if tn not in r[8]:
                            r[8].append(tn)
                    n = -(-d // REPEATER_UM)
                    if n > STAGE_MAX:
                        what = f"{label} {na} -> {nb}" + (" (no station: pin to pin)" if div == 1 and na.startswith("pin") and nb.startswith("pin") else "")
                        r = stg.setdefault(g, [n, what, s, d, 0, []])
                        if tn not in r[5]:
                            r[5].append(tn)
            for ni, no, a, b in pass_pairs(t):
                npass_seen += 1
                s, d = hop_path(C, a, b, rects)
                n = PASS_LOGIC + -(-d // REPEATER_UM)
                if n > STAGE_MAX:
                    g = ("pass", ni, no, round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
                    stg.setdefault(g, [n, f"bus pass-through {ni} -> {no}", s, d, PASS_LOGIC, []])[5].append(tn)

        def _types(v):
            return v[0] + (f" (+{len(v) - 1} type(s) with the same hop: {', '.join(v[1:4])}{' ...' if len(v) > 4 else ''})" if len(v) > 1 else "")
        det = sorted(det.values(), key=lambda r: (-r[0], r[8][0]))
        stg = sorted(stg.values(), key=lambda r: (-r[0], r[5][0]))
        dl, sl = [], []
        for _, label, na, a, nb, b, s, d, tns, nrow in det:
            more = f" (+{nrow - len(tns)} more row(s) on this hop)" if nrow > len(tns) else ""
            dl.append(f"WARN {CHECK} {_types(tns)}: SEAT-DETOUR {label}{more} {na} ({_f(a[0])},{_f(a[1])}) -> {nb} ({_f(b[0])},{_f(b[1])}): "
                      f"span {_f(s)} um but the path round the macros is {_f(d)} um (> reach {reach:g}, {d / max(s, 1e-6):.1f}x); "
                      f"fix: re-seat the register on the pin's side of the macro or add a station on the detour")
        for n, what, s, d, lg, tns in stg:
            sl.append(f"WARN {CHECK} {_types(tns)}: STAGE-DEPTH {what}: path {_f(d)} um (span {_f(s)}) ~ {int(n)} cells "
                      f"({lg} logic + {int(n) - lg} repeaters at {REPEATER_UM:g} um) > {STAGE_MAX} in one 833-ps cycle; "
                      f"fix: a register stage every <= {reach:g} um (internal_stations / mid-way input stage) or nearer windows")
        cap = int(kw.get("max_lines") or MAX_LINES)
        nd = min(len(dl), max(cap // 2, cap - len(sl)))
        out = dl[:nd] + sl[:cap - nd]
        if dl or sl:
            out.append(f"WARN {CHECK} summary: {sum(r[9] for r in det)} SEAT-DETOUR station hop(s) ({len(det)} distinct, {len({t for r in det for t in r[8]})} types), "
                       f"{len(stg)} STAGE-DEPTH path(s) ({len({t for r in stg for t in r[5]})} types) over {nhops} planned hops + "
                       f"{npass_seen} bus pass-through pairs in {time.time() - t0:.1f} s"
                       f"{' (first ' + str(len(out)) + ' listed)' if len(dl) + len(sl) > len(out) else ''}")
        return out
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import json
    import sys
    args = [a for a in sys.argv[1:] if a != "--all"]
    t0 = time.time()
    raw = json.load(open(args[0]))
    t1 = time.time()
    for ln in findings(raw, args[0], args[1] if len(args) > 1 else None, max_lines=100000 if "--all" in sys.argv else None):
        print(ln)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.2f} s")
