#!/usr/bin/env python3
"""HBM die-FT band delta (lane DIE-FT-HBM, COORD DIE GRT RULINGS 2026-10-25 11:29): a plan->plan generator step.

    python3 physical/die_plan/hbm_arch/die_ft_band.py --src PLAN_DIR --out PLAN_DIR2 \
        --row 4510.08 [--row 6065.28 ...] [--fixed root NW_hub NE_hub NW_io NE_io] [--types q_b100 ...]

Per abutted row of partitions (same origin y + height):
  1. lane chains: consecutive E/W seam ports of one lane joined by a straight E->W / W->E ft slot of a row partition
     form ONE chain that gets ONE die-y window on every seam it crosses (aligned across neighbours, no jog);
  2. placement on the seams: chains anchored by a --fixed partition keep that partition's window; the other ft
     chains (and ft turn ports) are packed from the row top down (the core-free top of the b1xx blocks) widest first,
     every remaining (terminating bus) port from the row bottom up; window lengths unchanged (same pin density);
  3. die_ft_bands on every --types type: dir EW, span = the type-frame y range of its E/W ft pins, layers M4+M6,
     die_share 1.0 ("M4/M6 belong to the die there"); die_trial models a band with GRT region adjustments;
  4. ft stations of the straight E/W slots move onto the chain's window centre line (x unchanged).
Writes PLAN_DIR2/die_plan.json (+ copies the sidecars) and die_ft_band_report.json.  No hand edits.

v2 (GEOM-REVIEW 12:18 FAIL on B2p_r1_band):
  - moved chains get windows at --pins-per-um (12) on M4+M6 (alternating tracks), the type gets face_pins_per_um
    {E,W} = 12 (G0 per-type face budget); chains are packed into core-free row intervals first;
  - EW bands are sized by TRACK NEED per chain window: half-height max(window/2, bits/(2*cap)), cap = usable M6
    (+ M4 only where the strip is core-free across the type) tracks/um x --use (0.55); overlapping strips merge;
  - NS stripes are M7 only (no M5 claim), each ft N/S slot gets a stripe of bits/(M7 usable tracks/um x use) width
    centred on its vertical-run stations (else its window), clipped to the type;
  - straight E/W slots are re-stationed on the window line; a station that would land on a hard core (grown by --halo)
    moves to the nearest free point along x within the hop budget, else keeps its planned site; a jog
    > --knee-max um gets its station at the knee;
  - audits in the report: station-on-hard-core (every ft station of every type), free std-cell area around each station
    vs bits x --site-um2, Manhattan reach of every lane (G0 lane geometry, jogs included).
"""
import argparse
import re
import copy
import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402

SNAP = 0.192          # lcm of the M4 (0.048) and M6 (0.064) pitches; row origins are on the 8.64 lattice
GAP = 0.48            # between two windows on one face (as the plan packer)
MARGIN = 8.64         # from the row corners


def snap(v, mode="near"):
    import math
    f = {"near": round, "down": math.floor, "up": math.ceil}[mode]
    return round(f(v / SNAP - (1e-6 if mode == "up" else -1e-6 if mode == "down" else 0)) * SNAP, 3)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--row", type=float, action="append", required=True, help="row origin y (die um)")
    ap.add_argument("--fixed", nargs="*", default=["root"], help="partitions whose seam windows stay (root = ROOTPACK lane)")
    ap.add_argument("--types", default=r"^q_b[01]\d\d$|^q_su30$",
                    help="regex of the types that get die_ft_bands (default: the ruling's b0xx/b1xx blocks + su30)")
    ap.add_argument("--layers", nargs="*", default=["M4", "M6"])
    ap.add_argument("--keep-turns", action=argparse.BooleanOptionalAction, default=True,
                    help="ports of turn slots keep their windows (anchors), default on")
    ap.add_argument("--v-layers", nargs="*", default=["M7"])
    ap.add_argument("--die-share", type=float, default=1.0)
    ap.add_argument("--pins-per-um", type=float, default=12.0)
    ap.add_argument("--use", type=float, default=0.55)
    ap.add_argument("--knee-max", type=float, default=50.0)
    ap.add_argument("--halo", type=float, default=2.0)
    ap.add_argument("--site-um2", type=float, default=0.5, help="std-cell area per station bit (flop + share of fill)")
    a = ap.parse_args(argv)
    src, out = Path(a.src), Path(a.out)
    raw = json.loads((src / "die_plan.json").read_text())
    P = S.Plan(copy.deepcopy(raw), src / "die_plan.json")
    T = raw["partition_types"]
    parts = {p["name"]: p for p in raw["partitions"]}
    ports = {p["id"]: p for p in raw["ports"]}
    rep = dict(src=str(src), rows=[], moved=0, shrunk=0, anchored=[], unaligned=[], bands={}, audit={})

    def rect(n):
        p = parts[n]
        w, h = T[p["type"]]["outline_um"]
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        return p["origin_um"][0], p["origin_um"][1], p["origin_um"][0] + w, p["origin_um"][1] + h

    def slot_of(part, bus):
        t = T[parts[part]["type"]]
        for s in t.get("ft_slots", []) or []:
            if bus in (s["name"] + "_i", s["name"] + "_o"):
                return s
        return None

    def tcores(tn, grow=0.0):
        """type-frame hard-core rects (core orient applied), grown by `grow`."""
        out = []
        for c in T[tn].get("hard_cores") or []:
            x, y = c["origin_um"]
            cw, ch = c["outline_um"]
            if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
                cw, ch = ch, cw
            out.append((x - grow, y - grow, x + cw + grow, y + ch + grow))
        return out

    def free_y_type(tn, grow):
        h = T[tn]["outline_um"][1]
        iv = sorted((r[1], r[3]) for r in tcores(tn, grow))
        fr, cur = [], 0.0
        for lo_, hi_ in iv:
            if lo_ > cur:
                fr.append((cur, lo_))
            cur = max(cur, hi_)
        if cur < h:
            fr.append((cur, h))
        return [(max(0.0, p), min(h, q)) for p, q in fr if q - p > 1.0]

    def free_y(n):
        """die-y intervals of partition n free of hard cores across its full width (MX/R180 flip y)."""
        p = parts[n]
        h = T[p["type"]]["outline_um"][1]
        oy = p["origin_um"][1]
        fl = p.get("orient", "R0") in ("MX", "R180")
        return [(oy + (h - q if fl else q0), oy + (h - q0 if fl else q)) for q0, q in free_y_type(p["type"], a.halo)]

    new_win = {}
    for y0 in a.row:
        row = sorted([n for n in parts if abs(parts[n]["origin_um"][1] - y0) < 1e-3], key=lambda n: parts[n]["origin_um"][0])
        h = T[parts[row[0]]["type"]]["outline_um"][1]
        y1 = y0 + h
        members = set(row)
        for n in parts:     # spanning anchors (root): face overlaps the row
            x0_, ya, x1_, yb = rect(n)
            if n not in members and n in a.fixed and ya <= y0 + 1e-3 and yb >= y1 - 1e-3:
                members.add(n)
        seam_ports = {}
        for pid, pr in ports.items():
            if pr.get("face") not in ("E", "W"):
                continue
            s_, d_ = pr["src"]["part"], pr["dst"]["part"]
            if s_ in members and d_ in members and s_ != S.DIE_PART:
                xs = rect(s_)[2] if pr["face"] == "E" else rect(s_)[0]
                lo, hi = sorted(pr["window_um"])
                if lo >= y0 - 1e-3 and hi <= y1 + 1e-3:
                    seam_ports[pid] = round(xs, 3)
        # chains along lanes
        nxt = {}
        for lid, ln in P.lanes.items():
            ps = ln["ports"]
            for pa, pb in zip(ps, ps[1:]):
                if pa in seam_ports and pb in seam_ports:
                    part = ports[pa]["dst"]["part"]
                    if part in a.fixed:
                        continue
                    s = slot_of(part, ports[pa]["dst"]["bus"])
                    if s and s["in_face"] in "EW" and s["out_face"] in "EW" and s["in_face"] != s["out_face"]:
                        nxt[pa] = pb
        prev = {v: k for k, v in nxt.items()}
        chains = []
        for pid in seam_ports:
            if pid in prev:
                continue
            c = [pid]
            while c[-1] in nxt:
                c.append(nxt[c[-1]])
            chains.append(c)
        occ = defaultdict(list)       # seam x -> [(lo, hi)]

        def is_ft(c):
            for pid in c:
                for side in ("src", "dst"):
                    e = ports[pid][side]
                    if e["part"] in parts and e["part"] not in a.fixed and slot_of(e["part"], e["bus"]):
                        return True
            return False

        def length(c):
            return max(abs(ports[p]["window_um"][1] - ports[p]["window_um"][0]) for p in c)

        def newlen(c):
            """v2: window length of the chain at --pins-per-um on its pin layers (pin_track_max kept)."""
            pr = ports[c[0]]
            return snap(S.window_for(0.0, S.port_pins_count(pr), pr["layers"], per_um=a.pins_per_um), "up")

        def chain_free(c):
            """die-y intervals free of hard cores across the full width of every row partition the chain touches."""
            iv = [(y0, y1)]
            for p in c:
                for side in ("src", "dst"):
                    n = ports[p][side]["part"]
                    if n in parts and n not in a.fixed:
                        fr = free_y(n)
                        iv = [(max(a_, c_), min(b_, d_)) for a_, b_ in iv for c_, d_ in fr
                              if min(b_, d_) - max(a_, c_) > 1.0]
            return iv

        def free(c, lo, hi):
            for p in c:
                for a_, b_ in occ[seam_ports[p]]:
                    if lo < b_ + GAP - 1e-6 and a_ < hi + GAP - 1e-6:
                        return False
            return True

        def put(c, lo, hi):
            for p in c:
                occ[seam_ports[p]].append((lo, hi))
                new_win[p] = [lo, hi]

        anchored, ftc, rest = [], [], []
        def turn_end(p):
            """port feeding / fed by a turn slot (E/W <-> N/S) of a row partition: its window stays, so the turn's
            stations (sited for that corner) keep their hop lengths."""
            for side in ("src", "dst"):
                e = ports[p][side]
                if e["part"] in parts and e["part"] not in a.fixed:
                    s = slot_of(e["part"], e["bus"])
                    if s and (s["in_face"] in "EW") != (s["out_face"] in "EW"):
                        return True
            return False

        for c in chains:
            fx = [p for p in c if ports[p]["src"]["part"] in a.fixed or ports[p]["dst"]["part"] in a.fixed
                  or (a.keep_turns and turn_end(p))]
            (anchored if fx else ftc if is_ft(c) else rest).append((c, fx))
        fx_all = {p for _, fx in anchored for p in fx}
        # multi-anchor chains stay exactly as planned (their windows were G0-clean); register them first so that
        # single-anchor chains never land on them (10-25: 20 abutment + 12 face-density ERR when they did)
        single = []
        for c, fx in anchored:
            ws = {tuple(sorted(ports[p]["window_um"])) for p in fx}
            if len(ws) > 1:
                rep["unaligned"].append(dict(chain=c, why="anchored ports with different windows (chain kept as planned)",
                                             windows=sorted(ws)))
                for p in c:
                    occ[seam_ports[p]].append(tuple(sorted(ports[p]["window_um"])))
                rep["anchored"].append(dict(chain=c, window=None))
            else:
                single.append((c, sorted(ws)[0]))
        for c, fx in anchored:        # every anchor window is taken before any single-anchor chain moves
            for p in fx:
                occ[seam_ports[p]].append(tuple(sorted(ports[p]["window_um"])))
        for c, (lo, hi) in single:
            if free([p for p in c if p not in fx_all], lo, hi):
                put(c, lo, hi)
            else:
                rep["unaligned"].append(dict(chain=c, why="anchor window taken by a kept chain (chain kept as planned)",
                                             window=[lo, hi]))
                for p in c:
                    occ[seam_ports[p]].append(tuple(sorted(ports[p]["window_um"])))
            rep["anchored"].append(dict(chain=c, window=[lo, hi]))
        # v2: anchored ft chains keep their window CENTRE (turn stations / fixed-partition sites unchanged) but shrink
        # to --pins-per-um; a port on a --fixed partition (root, hubs: not re-pinned here) keeps its full window
        for c, fx in anchored:
            if not is_ft(c):
                continue
            L = newlen(c)
            for p in c:
                if ports[p]["src"]["part"] in a.fixed or ports[p]["dst"]["part"] in a.fixed:
                    continue
                lo_, hi_ = sorted(new_win.get(p, ports[p]["window_um"]))
                if hi_ - lo_ > L + 1e-6:
                    cen = (lo_ + hi_) / 2
                    nlo = snap(cen - L / 2, "down")
                    new_win[p] = [nlo, snap(nlo + L, "up")]
                    rep["shrunk"] += 1
        def place(c, top_down):
            L = newlen(c) if top_down else length(c)
            cands = []
            for p in c:
                for a_, b_ in occ[seam_ports[p]]:
                    cands += [a_ - GAP, b_ + GAP]
            fr = chain_free(c) if top_down else []
            for a_, b_ in fr:
                cands += [b_ - 1.0, a_ + 1.0 + L]
            if top_down:
                vs = sorted({snap(v, "down") for v in cands + [y1 - MARGIN] if v - L >= y0 + MARGIN - 1e-6}, reverse=True)
                spans = [(snap(v - L, "down"), v) for v in vs]
            else:
                vs = sorted({snap(v, "up") for v in cands + [y0 + MARGIN] if v + L <= y1 - MARGIN + 1e-6})
                spans = [(v, snap(v + L, "up")) for v in vs]
            infree = [sp for sp in spans if any(a_ - 1e-6 <= sp[0] and sp[1] <= b_ + 1e-6 for a_, b_ in fr)]
            for lo, hi in infree + spans:
                if lo >= y0 + MARGIN - 1e-6 and hi <= y1 - MARGIN + 1e-6 and free(c, lo, hi):
                    put(c, lo, hi)
                    return True
            return False

        order = sorted([(c, True) for c, _ in ftc] + [(c, False) for c, _ in rest],
                       key=lambda x: (-len(x[0]), not x[1], -length(x[0])))
        for c, top_down in order:
            if place(c, top_down):
                continue
            ok = all(place([p], top_down) for p in c)
            rep["unaligned"].append(dict(chain=c, why="no common free window; ports placed one by one" if ok else
                                         "NO FREE WINDOW (port left unplaced)", length=length(c)))
            for p in c:
                if p not in new_win:
                    occ[seam_ports[p]].append(tuple(sorted(ports[p]["window_um"])))
        rep["rows"].append(dict(y0=y0, h=h, members=sorted(members), seam_ports=len(seam_ports), chains=len(chains),
                                anchored=len(anchored), ft_chains=len(ftc), other=len(rest)))
    for pid, w in new_win.items():
        if [round(v, 3) for v in sorted(ports[pid]["window_um"])] != [round(v, 3) for v in w]:
            rep["moved"] += 1
        ports[pid]["window_um"] = [round(w[0], 3), round(w[1], 3)]
    # bands + stations, per type (type frame; G0 proves every instance identical)
    LAY = {L["name"]: L for L in S.ASAP7_LAYERS}

    def cap_um(ln):
        return S.usable_tracks(LAY[ln], ln, 0.0, 1000.0) / 1000.0 * a.use

    def merge(strips, ext, capf):
        """strips [(lo, hi, bits)] -> merged bands [(lo, hi, bits)] each high enough for its bits at capf(lo, hi)."""
        st = sorted(strips)
        while True:
            out = []
            for lo_, hi_, b_ in st:
                if out and lo_ <= out[-1][1] + 2 * MARGIN:
                    p_ = out.pop()
                    lo_, hi_, b_ = min(p_[0], lo_), max(p_[1], hi_), p_[2] + b_
                need = b_ / capf(lo_, hi_)
                if hi_ - lo_ < need:
                    c_ = (lo_ + hi_) / 2
                    lo_, hi_ = c_ - need / 2, c_ + need / 2
                    if lo_ < 0:
                        lo_, hi_ = 0.0, need
                    if hi_ > ext:
                        lo_, hi_ = max(0.0, ext - need), ext
                out.append((lo_, hi_, b_))
            if len(out) == len(st):
                return out
            st = out

    def inside_core(cr, x, y):
        return any(r[0] < x < r[2] and r[1] < y < r[3] for r in cr)

    def hops_of(pts):
        return [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:])]

    reach = float(raw["budgets"].get("ft_station_max_um", 405.0))
    rowparts = [n for n in parts if any(abs(parts[n]["origin_um"][1] - y) < 1e-3 for y in a.row) and n not in a.fixed]
    shrunk_types = set()
    for pid in new_win:
        for side in ("src", "dst"):
            n = ports[pid][side]["part"]
            if n in parts and n not in a.fixed:
                shrunk_types.add(parts[n]["type"])
    for tn in sorted(shrunk_types):
        T[tn]["face_pins_per_um"] = {"E": a.pins_per_um, "W": a.pins_per_um}
    done = set()
    for n in sorted(rowparts):
        tn = parts[n]["type"]
        if tn in done or not re.search(a.types, tn):
            continue
        done.add(tn)
        t = T[tn]
        w, h = t["outline_um"]
        oy, ox = parts[n]["origin_um"][1], parts[n]["origin_um"][0]
        my = parts[n].get("orient", "R0") in ("MY", "R180")
        if parts[n].get("orient", "R0") in ("MX", "R180"):
            raise SystemExit(f"die_ft_band: {n} orient {parts[n]['orient']} (MX) not supported")
        cr0 = tcores(tn)
        crh = tcores(tn, a.halo)
        ew, ns = defaultdict(list), defaultdict(list)     # slot -> type-frame windows (face, lo, hi)
        for pid, pr in ports.items():
            for side in ("src", "dst"):
                if pr[side]["part"] != n:
                    continue
                s = slot_of(n, pr[side]["bus"])
                if not s:
                    continue
                lo, hi = sorted(pr["window_um"])
                if pr.get("face") in ("E", "W"):
                    f = pr["face"] if side == "src" else {"E": "W", "W": "E"}[pr["face"]]
                    if my:
                        f = {"E": "W", "W": "E"}[f]
                    ew[s["name"]].append((f, lo - oy, hi - oy, pid))
                elif pr.get("face") in ("N", "S"):
                    lo, hi = lo - ox, hi - ox
                    if my:
                        lo, hi = w - hi, w - lo
                    ns[s["name"]].append((lo, hi))
        if not ew and not ns:
            continue
        sl = {s["name"]: s for s in t.get("ft_slots", []) or []}

        def ycap(lo_, hi_):
            free_ = not any(r[1] < hi_ and lo_ < r[3] for r in cr0)
            return sum(cap_um(L) for L in a.layers if L == "M6" or free_)

        strips = [(min(v[1] for v in ws), max(v[2] for v in ws), sl[k]["width"]) for k, ws in ew.items()]
        bands = merge(strips, h, ycap)
        c7 = sum(cap_um(L) for L in a.v_layers)
        nstr = []
        for k, ws in ns.items():
            s = sl[k]
            inner = sorted(r[0] for r in s.get("regs_um", []) if 20.0 < r[1] < h - 20.0)
            cen = inner[len(inner) // 2] if inner else sum((p + q) / 2 for p, q in ws) / len(ws)
            nstr.append((cen - 0.5, cen + 0.5, s["width"]))
        stripes = merge(nstr, w, lambda lo_, hi_: c7)
        t["die_ft_bands"] = []
        bands = [(lo_ - max(0.0, 8.64 - (hi_ - lo_)) / 2, hi_ + max(0.0, 8.64 - (hi_ - lo_)) / 2, b_) for lo_, hi_, b_ in bands]
        stripes = [(lo_ - max(0.0, 8.64 - (hi_ - lo_)) / 2, hi_ + max(0.0, 8.64 - (hi_ - lo_)) / 2, b_)
                   for lo_, hi_, b_ in stripes]
        for lo_, hi_, b_ in bands:
            t["die_ft_bands"].append(dict(dir="EW", span_um=[snap(max(0.0, lo_), "down"), snap(min(h, hi_), "up")],
                                          layers=list(a.layers), die_share=a.die_share,
                                          note=f"DIE-FT-HBM v2 10-25: die-owned FT band, {b_} bits, track-sized"))
        for lo_, hi_, b_ in stripes:
            t["die_ft_bands"].append(dict(dir="NS", span_um=[snap(max(0.0, lo_), "down"), snap(min(w, hi_), "up")],
                                          layers=list(a.v_layers), die_share=a.die_share,
                                          note=f"DIE-FT-HBM v2 10-25: die-owned M7 FT stripe, {b_} bits, track-sized"))
        # re-station the straight E/W slots whose windows moved (knee station on jogs > --knee-max)
        rest_ = dict(restationed=0, kept_planned=0, knees=0, core_shift=0, core_kept=[], hop_over=[])
        for k, ws in ew.items():
            s = sl[k]
            if not (s["in_face"] in "EW" and s["out_face"] in "EW") or not s.get("regs_um"):
                continue
            moved_ = any(pid in new_win for _, _, _, pid in ws)
            fi = [v for v in ws if v[0] == s["in_face"]]
            fo = [v for v in ws if v[0] == s["out_face"]]
            if not moved_ or not fi or not fo:
                continue
            yi = (fi[0][1] + fi[0][2]) / 2
            yo = (fo[0][1] + fo[0][2]) / 2
            xin = 0.0 if s["in_face"] == "W" else w
            xout = w if s["out_face"] == "E" else 0.0
            xs = [r[0] for r in s["regs_um"]]
            best = None
            ks = [len(xs)] if abs(yi - yo) <= a.knee_max else range(len(xs))
            for kk in ks:          # stations 0..kk on yi, the rest on yo (station kk = the knee when jogging)
                pts = [(xin, yi)] + [(x, yi if j <= kk else yo) for j, x in enumerate(xs)] + [(xout, yo)]
                if abs(yi - yo) <= a.knee_max:
                    yc = (yi + yo) / 2
                    pts = [(xin, yi)] + [(x, yc) for x in xs] + [(xout, yo)]
                mh = max(hops_of(pts))
                if best is None or mh < best[0]:
                    best = (mh, pts)
            pts = best[1]
            regs = []
            for j in range(1, len(pts) - 1):
                x, y = pts[j]
                if inside_core(crh, x, y):
                    # nearest free site (2-D, 4.32-um grid within 300 um) that keeps both adjacent hops shortest
                    best_ = None
                    for dx in range(-69, 70):
                        for dy in range(-69, 70):
                            cx, cy = x + dx * 4.32, y + dy * 4.32
                            if not (0.0 <= cx <= w and 0.0 <= cy <= h) or inside_core(crh, cx, cy):
                                continue
                            pv, nx_ = pts[j - 1], pts[j + 1]
                            mh = max(abs(cx - pv[0]) + abs(cy - pv[1]), abs(cx - nx_[0]) + abs(cy - nx_[1]))
                            key = (mh > reach, abs(dx) + abs(dy), mh)
                            if best_ is None or key < best_[0]:
                                best_ = (key, cx, cy)
                    if best_ is not None:
                        x, y = best_[1], best_[2]
                        pts[j] = (x, y)
                        rest_["core_shift"] += 1
                    else:
                        x, y = s["regs_um"][j - 1]
                        pts[j] = (x, y)
                        rest_["core_kept"].append(k)
                regs.append([round(x, 3), round(y, 3)])
            # keep the PLANNED stations (sited by the plan generator in the free strips/channels) when they give the
            # shorter worst hop from the new windows
            plan_pts = [pts[0]] + [tuple(r) for r in s["regs_um"]] + [pts[-1]]
            if max(hops_of(plan_pts)) <= max(hops_of(pts)) + 1e-6 or any(inside_core(crh, *q) for q in pts[1:-1]):
                pts = plan_pts
                regs = [list(r) for r in s["regs_um"]]
                rest_["kept_planned"] += 1
            s["regs_um"] = regs
            rest_["restationed"] += 1
            if abs(yi - yo) > a.knee_max:
                rest_["knees"] += 1
            if max(hops_of(pts)) > reach + 1e-6:
                rest_["hop_over"].append((k, round(max(hops_of(pts)), 1)))
        rep["bands"][tn] = dict(bands=[(b["dir"], b["span_um"], b["layers"]) for b in t["die_ft_bands"]], **rest_)
    # audits: station-on-hard-core + local free std-cell area, every ft station of every type
    aud = dict(stations=0, in_core=[], tight=[])
    for tn, t in T.items():
        crh = tcores(tn, a.halo)
        cr0 = tcores(tn)
        w, h = t["outline_um"]
        for s in t.get("ft_slots", []) or []:
            for x, y in s.get("regs_um", []) or []:
                aud["stations"] += 1
                if inside_core(crh, x, y):
                    aud["in_core"].append(dict(type=tn, slot=s["name"], at=[x, y], bits=s["width"]))
                bx0, by0, bx1, by1 = max(0, x - 30), max(0, y - 30), min(w, x + 30), min(h, y + 30)
                area = (bx1 - bx0) * (by1 - by0) - sum(max(0, min(bx1, r[2]) - max(bx0, r[0])) *
                                                       max(0, min(by1, r[3]) - max(by0, r[1])) for r in cr0)
                if area < s["width"] * a.site_um2:
                    aud["tight"].append(dict(type=tn, slot=s["name"], at=[x, y], bits=s["width"],
                                             free_um2_60box=round(area), need_um2=round(s["width"] * a.site_um2)))
    rep["audit"] = dict(stations=aud["stations"], in_core=len(aud["in_core"]), tight=len(aud["tight"]),
                        in_core_list=aud["in_core"], tight_list=aud["tight"])
    out.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if f.name in ("die_plan.json",):
            continue
        d = out / f.name
        if f.is_dir():
            if d.exists():
                shutil.rmtree(d)
            shutil.copytree(f, d)
        else:
            shutil.copy2(f, d)
    raw["die"]["label"] = raw["die"].get("label", "") + " | die_ft_band v2 (DIE-FT-HBM 10-25): aligned row FT chains at 12/um + track-sized M4/M6 bands + M7 NS stripes"
    (out / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
    (out / "die_ft_band_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(moved=rep["moved"], shrunk=rep["shrunk"], rows=rep["rows"], unaligned=len(rep["unaligned"]),
                          bands=rep["bands"], audit={k: v for k, v in rep["audit"].items() if not k.endswith("_list")}),
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
