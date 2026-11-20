#!/usr/bin/env python3
"""S81-LEAF-PLAN 11-14 (FABLE-REVIEW-CONG R-LEAF-1/2/3): leaf face/band/slot rules on a die plan, die-agnostic.

    leaf_rules.py check PLAN --match RE [--tsv OUT.tsv] [--json OUT.json]
    leaf_rules.py bands PLAN SIDECAR OUT_PLAN OUT_SIDECAR REPORT.json --match RE [--per-bit 10] [--max-depth 43.2]

RULES (FABLE-REVIEW-CONG 11-14, sec 2; GRT-proven on t32 band / t68 slot):
  R-LEAF-1 BAND: the clock-landing ring band of a landed input bus lies under its own pin window: its along-face span
           covers >= 80 % of the window span, its near edge is within one street (43.2 um) of the face, and it is not a
           column (depth <= max(along, 43.2)).  Never in a core-core slot, never beside the window.
  R-LEAF-2 FACE CLEAR: over a window of >= 16 pins no hard core is nearer the face than 43.2 um (86.4 when landed).
  R-LEAF-2b (COORD 11-14, t21 / t75 DRT-0255): 86.4 um over any window of >= 512 pins, landed or not.
  R-LEAF-3 SLOT: two facing hard cores abut (< 4.32 um) or keep >= 43.2 um.

`bands` re-sites every single-rect band that breaks R-LEAF-1 to the face strip over its window (window span clamped
to the 17.28-um outline margin, widened symmetrically only when the area needs more than --max-depth, nearest legal
inset first, rows/2.16-um lattice), area = max(current area, --per-bit x bits when that still fits within
--max-depth).  Obstacles: the cland_band_fit planning union (macros + reset clearance, keepouts, other bands at their
current rects, islands, clock-tree sites, ft bit sites, PHY supply, reset relay / start / status groups) plus internal
station registers and clock tap points.  Every copy of the band (landing_contract.bands, collector_local_sources[].band,
sidecar collector bands / local_sources) gets the new rect.  A band with no legal strip is reported NEEDS-CORE-MOVE
with the cores in the strip, never moved elsewhere.  Only the bands' rect_um / max_pin_to_band_hop_um change (EQ).
"""
import argparse, copy, json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import clock_landing_plan as C  # noqa: E402
import cland_band_fit as F  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402

MARGIN, STREET, ABUT, G = 17.28, 43.2, 4.32, 2.16
WIDE_BITS = 512          # R-LEAF-2b: a window this wide keeps 2 x STREET clear whether landed or not


def face_need(landed, bits):
    """R-LEAF-2 / 2b clearance of a >= 16-pin window."""
    return 2 * STREET if (landed or bits >= WIDE_BITS) else STREET
import os as _os_cbc, sys as _sys_cbc
_sys_cbc.path.insert(0, _os_cbc.path.dirname(_os_cbc.path.abspath(__file__)))
import cbc_rules as _CBC  # noqa: E402  OWNER 11-20 #6: generator hop default (300 um), one knob for every die
REACH = _CBC.REACH_UM_PER_HOP - 2.16


def windows(t):
    """(bus, face, lo, hi, bits) of every bus / ft side with a face window."""
    out = []
    for b in t.get("buses", []) or []:
        if "window_um" in b and "face" in b:
            out.append((b["name"], b["face"], float(b["window_um"][0]), float(b["window_um"][1]), int(b.get("width", 1))))
    for s in t.get("ft_slots", []) or []:
        for suf, fk, wk in (("_i", "in_face", "in_window_um"), ("_o", "out_face", "out_window_um")):
            if wk in s and fk in s:
                out.append((s["name"] + suf, s[fk], float(s[wk][0]), float(s[wk][1]), int(s.get("width", 1))))
    return out


def along(f, r):
    return (r[0], r[2]) if f in "NS" else (r[1], r[3])


def face_gap(f, r, W, H):
    return {"S": r[1], "N": H - r[3], "W": r[0], "E": W - r[2]}[f]


def depth_of(f, r):
    return (r[3] - r[1]) if f in "NS" else (r[2] - r[0])


def band_rects(b):
    return [list(r) for r in (b.get("rects_um") or ([b["rect_um"]] if b.get("rect_um") else []))]


def l1_ok(f, lo, hi, rects, W, H):
    """(ok, cover fraction, face gap, depth, along)"""
    span = max(hi - lo, 1e-6)
    cov = []
    for r in rects:
        a0, a1 = along(f, r); cov.append((max(a0, lo), min(a1, hi)))
    cov = sorted(c for c in cov if c[1] > c[0])
    tot, cur = 0.0, None
    for a, b in cov:
        if cur is None or a > cur[1]:
            if cur: tot += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    if cur: tot += cur[1] - cur[0]
    gap = min(face_gap(f, r, W, H) for r in rects)
    dep = max(depth_of(f, r) for r in rects)
    al = sum(along(f, r)[1] - along(f, r)[0] for r in rects)
    ok = tot >= 0.8 * span - 1e-6 and gap <= MARGIN + STREET + 1e-6 and dep <= max(al, STREET) + 1e-6
    return ok, tot / span, gap, dep, al


def check_type(tn, t, minpins=16):
    W, H = map(float, t["outline_um"])
    lc = ((t.get("clock") or {}).get("landing_contract") or {})
    bands = lc.get("bands") or {}
    mac = {k: list(v) for k, v in placement_boxes(t).items()}
    rows = []
    for bus, f, lo, hi, bits in windows(t):
        landed = bus in bands and bool(band_rects(bands[bus]))
        if landed:
            ok, cov, gap, dep, al = l1_ok(f, lo, hi, band_rects(bands[bus]), W, H)
            if not ok:
                rows.append((tn, "L1", bus, f, "band %s cover %.0f%% face %.1f depth %.1f along %.1f (window %.1f..%.1f)"
                             % (band_rects(bands[bus]), 100 * cov, gap, dep, al, lo, hi)))
        if bits >= minpins:
            need = face_need(landed, bits)
            for n, r in mac.items():
                a0, a1 = along(f, r)
                if min(a1, hi) - max(a0, lo) <= 0: continue
                g = face_gap(f, r, W, H)
                if g < need - 1e-6:
                    rows.append((tn, "L2", bus, f, "core %s gap %.1f < %.1f over the %d-bit window %.1f..%.1f"
                                 % (n, g, need, bits, lo, hi)))
    names = sorted(mac)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = mac[a], mac[b]
            ox = min(A[2], B[2]) - max(A[0], B[0]); oy = min(A[3], B[3]) - max(A[1], B[1])
            for gap, ovl in ((-ox, oy), (-oy, ox)):
                if ovl > 0 and ABUT - 1e-6 <= gap < STREET - 1e-6:
                    rows.append((tn, "L3", a + "|" + b, "-", "slot %.2f um over %.0f um" % (gap, ovl)))
    return rows


def extra_obstacles(t):
    obs = []
    for st in t.get("internal_stations", []) or []:
        obs += [[x - G, y - G, x + G, y + G] for x, y in st.get("regs_um", []) or []]
    ck = t.get("clock") or {}
    pts = [tp.get("xy") for tp in (ck.get("added_taps") or []) + (ck.get("taps") or []) if tp.get("xy")]
    obs += [[x - .01, y - .01, x + .01, y + .01] for x, y in pts]
    return obs


def hit(box, obs):
    # 0.02-um tolerance: a core box carries its track offset (0.012 um) over the 2.16-um band lattice
    return [o for o in obs if min(box[2], o[2]) > max(box[0], o[0]) + 0.02 and min(box[3], o[3]) > max(box[1], o[1]) + 0.02]


def mkbox(f, s0, s1, inset, d, W, H):
    return ([inset, s0, inset + d, s1] if f == "W" else [W - inset - d, s0, W - inset, s1] if f == "E" else
            [s0, inset, s1, inset + d] if f == "S" else [s0, H - inset - d, s1, H - inset])


SMALL_UM2 = 25.0   # reset relay / collector site boxes (4.32 x 4.32) and tap points: the band is notched around them


def home(f, lo, hi, area, W, H, obs, px, py, maxdep):
    """Face strip over [lo,hi] (clamped to the margin, 2.16 lattice): nearest legal inset first, then the narrowest
    span (window, widened symmetrically in 4.32 steps) whose depth area/span (2.16 lattice, 8.64..maxdep) is clear.
    Small fixed sites (reset relay boxes, <= SMALL_UM2) inside the strip are notched out (multi-rect band: the strip
    split along the face at each site, pieces >= 4.32 um kept, depth sized for the area that is left).
    Returns (rects nearest-pin first, None) or (None, first blocking obstacles)."""
    ext = W if f in "NS" else H
    big = [o for o in obs if F.area(o) > SMALL_UM2]
    small = [o for o in obs if F.area(o) <= SMALL_UM2]
    w0 = max(MARGIN, G * math.floor(lo / G + 1e-9)); w1 = min(ext - MARGIN, G * math.ceil(hi / G - 1e-9))
    if w1 - w0 < 8.64:
        c = (w0 + w1) / 2; w0, w1 = max(MARGIN, c - 4.32), min(ext - MARGIN, c + 4.32)
    best_hit = None
    for k in range(int(STREET / G) + 1):
        inset = MARGIN + G * k
        for j in range(0, 80):
            L = (w1 - w0) + 4.32 * j
            if L > ext - 2 * MARGIN + 1e-6: break
            cands = ([w0] if not j else [(w0 + w1 - L) / 2, w1 - L, w0]) + [w0 + G * m for m in (1, -1, 2, -2, 3, -3, 4, -4)]
            for c0 in cands:
              s0 = max(MARGIN, c0); s1 = min(ext - MARGIN, s0 + L); s0 = max(MARGIN, s1 - L)
              s0 = max(MARGIN, G * math.floor(s0 / G + 1e-9)); s1 = min(ext - MARGIN, G * math.ceil(s1 / G - 1e-9))
              for extra in range(0, 4):
                  d0 = G * math.ceil(max(8.64, area / (s1 - s0)) / G - 1e-9) + G * extra
                  if d0 > maxdep + 1e-6: break
                  box = [round(v, 6) for v in mkbox(f, s0, s1, inset, d0, W, H)]
                  if box[0] < MARGIN - 1e-6 or box[1] < MARGIN - 1e-6 or box[2] > W - MARGIN + 1e-6 or box[3] > H - MARGIN + 1e-6:
                      break
                  if F.hop(box, (px, py)) > REACH: break
                  h = hit(box, big)
                  if h:
                      if best_hit is None and j == 0: best_hit = h
                      break
                  hs = hit(box, small)
                  if not hs: return [box], None
                  cuts = sorted((along(f, o)[0] - 1e-3, along(f, o)[1] + 1e-3) for o in hs)
                  pieces, cur = [], s0
                  for c0, c1 in cuts:
                      c0 = G * math.floor(c0 / G + 1e-9); c1 = G * math.ceil(c1 / G - 1e-9)
                      if c0 - cur >= 4.32 - 1e-6: pieces.append((cur, c0))
                      cur = max(cur, c1)
                  if s1 - cur >= 4.32 - 1e-6: pieces.append((cur, s1))
                  rects = [[round(v, 6) for v in mkbox(f, a0, a1, inset, d0, W, H)] for a0, a1 in pieces]
                  if rects and not any(hit(r, obs) for r in rects) and sum(F.area(r) for r in rects) >= area - 1e-6:
                      return sorted(rects, key=lambda r: F.hop(r, (px, py))), None
    return None, best_hit


def band_obstacles(t, tn, sd, lc, bus):
    """cland_band_fit planning union, macros WITHOUT the reset halo (the kit cuts band rows at the macro edge;
    FABLE-REVIEW-CONG t32 E1 band abutting ve_m placed and routed GRT 0), plus station registers and clock taps."""
    import reset_tree as RT
    halo = [list(r) for r in placement_boxes(t, halo=RT.CLEAR_UM).values()]
    obs = [o for o in F.obstacles(t, tn, None, sd, lc, bus) if o not in halo]
    return obs + [list(r) for r in placement_boxes(t).values()] + extra_obstacles(t)


def run_bands(raw, side, match, per_bit=10.0, maxdep=STREET, densify=False):
    out = copy.deepcopy(raw); sd = copy.deepcopy(side) if side else None
    rep = dict(moved=[], needs_core_move=[], skipped=[], kept=[])
    for tn in sorted(out["partition_types"]):
        if not re.search(match, tn): continue
        t = out["partition_types"][tn]
        lc = ((t.get("clock") or {}).get("landing_contract") or {})
        bands = lc.get("bands") or {}
        if not bands: continue
        W, H = map(float, t["outline_um"])
        win = {w[0]: w for w in windows(t)}
        mac = {k: list(v) for k, v in placement_boxes(t).items()}
        todo = []
        for bus, b in bands.items():
            if bus not in win or not band_rects(b): continue
            _, f, lo, hi, bits = win[bus]
            ok, cov, gap, dep, al = l1_ok(f, lo, hi, band_rects(b), W, H)
            # --densify (R-LEAF-1b, TYPE-SLICET30 t8): a band under its window but below per_bit um2/bit is re-sited too
            if ok and not (densify and per_bit * bits > sum(F.area(r) for r in band_rects(b)) + 1e-6): continue
            if b.get("rects_um") or b.get("hard_core") or any(k in b for k in ("ff_rect_um", "freg_rect_um", "native_role_banks")):
                rep["skipped"].append(dict(type=tn, bus=bus, why="multi-rect / hard band", rects=band_rects(b))); continue
            todo.append(bus)
        # widest first; a band not yet moved keeps its rect as an obstacle (second pass retries the failures)
        pending = sorted(todo, key=lambda k: (-int(bands[k].get("width", 0)), k))
        done_keep = set()
        for _pass in range(2):
            left = []
            for bus in pending:
                b = bands[bus]; r0 = list(b["rect_um"]); _, f, lo, hi, bits = win[bus]
                obs = band_obstacles(t, tn, sd, lc, bus)
                px, py = C._bus_xy(t, bus)
                a0 = F.area(r0)
                box = why = None
                # other landed windows' own face strips are soft obstacles: a band widens into them only if
                # nothing else fits (each band keeps the room under its own window first)
                soft = []
                for ob, (_, f2, lo2, hi2, _b2) in win.items():
                    if ob != bus and f2 == f and _b2 >= 16 and ob not in done_keep:
                        a_lo, a_hi = max(lo2, MARGIN), min(hi2, (W if f in "NS" else H) - MARGIN)
                        if a_hi > a_lo: soft.append(mkbox(f, a_lo, a_hi, MARGIN, STREET, W, H))
                tries = [(per_bit * bits, obs + soft)] if per_bit * bits > a0 else []
                if densify: tries += [(per_bit * bits, obs)] if per_bit * bits > a0 else []
                else: tries += [(a0, obs + soft), (a0, obs)]
                for area, ob_ in tries:
                    box, why = home(f, lo, hi, area, W, H, ob_, px, py, maxdep)
                    if box: break
                if not box:
                    left.append((bus, why)); continue
                rects = box; box = rects[0]
                nb = dict(b); nb["rect_um"] = box; nb.pop("rects_um", None)
                if len(rects) > 1: nb["rects_um"] = rects
                nb["max_pin_to_band_hop_um"] = round(max(F.hop(r, (px, py)) for r in rects), 3)
                nb["resited_from_um"] = r0
                nb["resite"] = "S81-LEAF-PLAN B4L R-LEAF-1%s: band under its own pin window (FABLE-REVIEW-CONG 11-14)" % ("b density" if l1_ok(f, lo, hi, [r0], W, H)[0] else "")
                bands[bus] = nb
                for src in lc.get("collector_local_sources", []) or []:
                    if src.get("name") == bus and isinstance(src.get("band"), dict) and src["band"].get("rect_um") == r0:
                        src["band"] = copy.deepcopy(nb)
                if sd is not None:
                    ct = (((sd.get("collector") or {}).get("types") or {}).get(tn) or {})
                    if isinstance((ct.get("bands") or {}).get(bus), dict) and ct["bands"][bus].get("rect_um") == r0:
                        ct["bands"][bus] = copy.deepcopy(nb)
                    for src in ct.get("local_sources", []) or []:
                        if src.get("name") == bus and isinstance(src.get("band"), dict) and src["band"].get("rect_um") == r0:
                            src["band"] = copy.deepcopy(nb)
                na = sum(F.area(r) for r in rects)
                rep["moved"].append(dict(type=tn, bus=bus, face=f, window=[lo, hi], bits=bits, old_rect_um=r0, new_rect_um=box,
                                         new_rects_um=rects if len(rects) > 1 else None,
                                         old_area=round(a0, 1), new_area=round(na, 1),
                                         um2_per_bit=round(na / max(bits, 1), 2), hop_um=nb["max_pin_to_band_hop_um"]))
            if not left: break
            pending = [b for b, _ in left]
        for bus, why in (left if todo else []):
            cores = sorted({n for n, m in mac.items() for o in (why or []) if F.ov(o, m) or o == m})
            rep["needs_core_move"].append(dict(type=tn, bus=bus, rect=bands[bus]["rect_um"], window=list(win[bus][2:4]),
                                               face=win[bus][1], blocking=[list(map(lambda v: round(v, 2), o)) for o in (why or [])][:6],
                                               cores=cores))
    return out, sd, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sp = ap.add_subparsers(dest="cmd", required=True)
    c = sp.add_parser("check"); c.add_argument("plan"); c.add_argument("--match", default=r"leaf__")
    c.add_argument("--tsv"); c.add_argument("--json")
    b = sp.add_parser("bands"); [b.add_argument(k) for k in ("plan", "sidecar", "out_plan", "out_sidecar", "report")]
    b.add_argument("--match", default=r"leaf__"); b.add_argument("--per-bit", type=float, default=0.0)
    b.add_argument("--max-depth", type=float, default=STREET)
    b.add_argument("--densify", action="store_true", help="also re-site R-LEAF-1-legal bands below --per-bit um2/bit")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    if a.cmd == "check":
        rows = []
        for tn in sorted(raw["partition_types"]):
            if re.search(a.match, tn): rows += check_type(tn, raw["partition_types"][tn])
        cnt = {}
        for r in rows: cnt.setdefault(r[1], set()).add(r[0]);
        print("types", len({tn for tn in raw["partition_types"] if re.search(a.match, tn)}),
              " ".join("%s: %d items in %d types" % (k, sum(1 for r in rows if r[1] == k), len(v)) for k, v in sorted(cnt.items())))
        if a.tsv: Path(a.tsv).write_text("type\trule\tbus\tface\tdetail\n" + "".join("\t".join(r) + "\n" for r in rows))
        if a.json: Path(a.json).write_text(json.dumps(rows, indent=0))
        return 0
    side = json.loads(Path(a.sidecar).read_text()) if a.sidecar not in ("-", "none", "") else None
    out, sd, rep = run_bands(raw, side, a.match, a.per_bit, a.max_depth, a.densify)
    Path(a.out_plan).write_text(json.dumps(out, indent=1) + "\n")
    if sd is not None: Path(a.out_sidecar).write_text(json.dumps(sd, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print("moved %d needs-core-move %d skipped %d" % (len(rep["moved"]), len(rep["needs_core_move"]), len(rep["skipped"])))
    for m in rep["moved"]:
        print("MOVED", m["type"], m["bus"], m["old_rect_um"], "->", m["new_rects_um"] or m["new_rect_um"], "um2/bit", m["um2_per_bit"], "hop", m["hop_um"])
    for m in rep["needs_core_move"]:
        print("NEEDS-CORE-MOVE", m["type"], m["bus"], m["face"], m["window"], m["cores"], m["blocking"][:2])
    for m in rep["skipped"]:
        print("SKIP", m["type"], m["bus"], m["why"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
