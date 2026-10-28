#!/usr/bin/env python3
"""S81 graded-mesh physical encoder (S81-CORES-R23, COORD ruling 5).

Turns the literal graded 3-rail mesh (graded_mesh_physical.materialize -> graded_metal.json) plus the placed clock
cells into ONE explicit M8/M9 shape set, keeping the real rail topology and the die PG spacing:
  * mesh rails     -- every literal segment rect unchanged (same axis, width, span; no uniform replacement); only the
                      two rail ENDS are extended by half their end via pad so every VIA89 array lies inside metal;
  * VIA89 arrays   -- the literal crossing arrays, checked inside the incident M8 AND M9 rects;
  * rail shields   -- two drawn VSS stripes per segment at the wide-metal spacing row of the rail width (ASAP7
                      SPACINGTABLE 0.5/1.0 um at PRL >= 1.8 um), NDR space otherwise;
  * driver banks   -- per bank one M8 collector over all unit Y pins (PG-aware track) + its jog to the rail
                      (M8 straight onto an M9 rail, M9 riser onto an M8 rail) and one M1->M7 pin stack + M7 riser
                      per unit;
  * local trees    -- per stub one drop from its A pin onto the rail (M9 onto an M8 rail, M8 onto an M9 rail) and a
                      pin stack; then every tree net (root / H-tree legs / reps / nodes / stubs) re-routed by the
                      SAME C128.TrackRouter + fixed_wires the base build used, now against PG + the graded rails;
  * census         -- same-layer shorts / spacing (incl. the PG wide rule) over PG + every encoded shape, via-in-
                      incident-rect, max width (M8 2.0 um), PG-gap occupancy (one rail per PG gap), literal graph
                      topology (1 component, (nx-1)(ny-1) cycles) and attachment continuity.
Geometry only: no extraction, timing or P&R claim. physical_encoder_qualified stays False unless every census row is 0.
"""
import argparse, bisect, collections, hashlib, json, math, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[1] / "die_plan"
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as D, die_clock_128 as C, schema as S   # noqa: E402

M8_MAXWIDTH = 2.0
PG_PITCH, PG_W = 8.64, 0.48
NET = "ck_mesh"
STACK = ("M1", "M2", "M3", "M4", "M5", "M6", "M7")


def rail_key(seg):
    x0, y0, x1, y1 = seg["centre_um"]
    return (seg["layer"], round(y0 if seg["layer"] == "M8" else x0, 6))


def rail_gap(w, run):
    """edge gap rail -> shield: the wider-shape spacing row for the rail width at its parallel run, NDR space floor"""
    return max(D.NDR["4w"]["space"], C.wide_spacing(w, run))


def gap_axis(v, pitch=4.32, track=0.08, toff=0.04):
    """centre-most 80-nm track of the ACTUAL PG gap holding v: the die grid alternates VDD/VSS every 4.32 um (each
    net on 8.64), so a gap is (k*4.32, (k+1)*4.32), not the 8.64 gap graded_mesh_physical.axis assumed"""
    k = math.floor(v / pitch)
    mid = k * pitch + pitch / 2
    n = round((mid - toff) / track)
    cands = [round(toff + (n + d) * track, 6) for d in (-1, 0, 1)]
    return min(cands, key=lambda q: (abs(q - mid), q))


def snap_to_pg_gaps(g, pitch=4.32, netmap=None):
    """the same literal mesh (same rails, order, widths, segments, via arrays, attachments) with every rail axis
    moved to the centre track of its actual PG gap (netmap given: to the VSS side at legal wide-row spacing,
    vss_side_axis); returns (g2, moves)"""
    if netmap is None:
        fx = {round(x, 6): gap_axis(x, pitch) for x in g["xs"]}
        fy = {round(y, 6): gap_axis(y, pitch) for y in g["ys"]}
    else:
        wm = collections.defaultdict(float)
        for s in g["segments"]:
            k = rail_key(s)
            wm[k] = max(wm[k], s["width_um"])
        fx = {round(x, 6): vss_side_axis(x, wm[("M9", round(x, 6))], netmap, "M9", pitch) for x in g["xs"]}
        fy = {round(y, 6): vss_side_axis(y, wm[("M8", round(y, 6))], netmap, "M8", pitch) for y in g["ys"]}
    if len(set(fx.values())) != len(fx) or len(set(fy.values())) != len(fy):
        raise ValueError("two rails snap into one PG gap")
    X = lambda x: fx[round(x, 6)]   # noqa: E731
    Y = lambda y: fy[round(y, 6)]   # noqa: E731
    segs = []
    for s in g["segments"]:
        x0, y0, x1, y1 = s["centre_um"]
        w = s["width_um"]
        c = [X(x0), Y(y0), X(x1), Y(y1)]
        r = [c[0], c[1] - w / 2, c[2], c[1] + w / 2] if s["layer"] == "M8" else [c[0] - w / 2, c[1], c[0] + w / 2, c[3]]
        segs.append(dict(s, centre_um=c, rect_um=[round(v, 6) for v in r]))
    vias = [dict(v, x_um=X(v["x_um"]), y_um=Y(v["y_um"])) for v in g["vias"]]
    att = []
    for a in g["attachments"]:
        x, y = a["xy_um"]
        att.append(dict(a, xy_um=[X(x), y] if a["layer"] == "M9" else [x, Y(y)]))
    moves = [abs(a - b) for a, b in list(fx.items()) + list(fy.items())]
    g2 = dict(g, segments=segs, vias=vias, attachments=att, xs=sorted(fx.values()), ys=sorted(fy.values()))
    return g2, dict(max_um=round(max(moves), 4), mean_um=round(sum(moves) / len(moves), 4), rails=len(moves))


def gap_fit_findings(g, pgr):
    """segments whose width + the wide-row spacing to BOTH actual neighbouring PG stripes does not fit their gap"""
    idx = {"M8": collections.defaultdict(list), "M9": collections.defaultdict(list)}
    for net, lay, x0, y0, x1, y1 in pgr:
        if lay == "M8":
            idx[lay][round((y0 + y1) / 2, 3)].append((x0, x1, y1 - y0))
        elif lay == "M9":
            idx[lay][round((x0 + x1) / 2, 3)].append((y0, y1, x1 - x0))
    cs = {L: sorted(idx[L]) for L in idx}
    bad = []
    for s in g["segments"]:
        lay = s["layer"]
        x0, y0, x1, y1 = s["centre_um"]
        c, a0, a1 = (y0, min(x0, x1), max(x0, x1)) if lay == "M8" else (x0, min(y0, y1), max(y0, y1))
        w, L = s["width_um"], cs[lay]
        i = bisect.bisect_left(L, c)
        for p in L[max(0, i - 2):i + 2]:
            for lo, hi, pw in idx[lay][p]:
                prl = min(a1, hi) - max(a0, lo)
                if prl <= 0:
                    continue
                need = max(D.NDR["4w"]["space"], C.wide_spacing(max(w, pw), prl))
                gap = abs(c - p) - w / 2 - pw / 2
                if gap < need - 1e-6:
                    bad.append(dict(layer=lay, axis=c, span=[a0, a1], width=w, pg=p, pg_width=pw, gap=round(gap, 4), need=need))
    return bad


def rail_rects(g):
    """[(seg, layer, axis, width, along_lo, along_hi)] of the literal segments, every rail PIECE end (rail end, or an
    end left by the PHY-band clip) extended by half of its end via pad so the VIA89 array lies inside metal"""
    pad = {(round(v["x_um"], 6), round(v["y_um"], 6)): v["pad_um"] for v in g["vias"]}
    rails = collections.defaultdict(list)
    for s in g["segments"]:
        rails[rail_key(s)].append(s)
    out = []
    for (lay, c), segs in rails.items():
        segs.sort(key=lambda s: min(s["centre_um"][0], s["centre_um"][2]) if lay == "M8" else min(s["centre_um"][1], s["centre_um"][3]))
        span = [seg_span(s) for s in segs]
        for i, s in enumerate(segs):
            a0, a1 = span[i]
            e0 = e1 = 0.0
            if i == 0 or abs(span[i - 1][1] - a0) > 1e-6:
                e0 = pad.get((round(a0, 6), round(c, 6)) if lay == "M8" else (round(c, 6), round(a0, 6)), 0.0) / 2
            if i == len(segs) - 1 or abs(span[i + 1][0] - a1) > 1e-6:
                e1 = pad.get((round(a1, 6), round(c, 6)) if lay == "M8" else (round(c, 6), round(a1, 6)), 0.0) / 2
            out.append((s, lay, c, s["width_um"], round(a0 - e0, 6), round(a1 + e1, 6)))
    return out, rails


def seg_span(s):
    x0, y0, x1, y1 = s["centre_um"]
    return (min(x0, x1), max(x0, x1)) if s["layer"] == "M8" else (min(y0, y1), max(y0, y1))


def rail_shapes(g, nd, shield="VSS", drawn=True, sides=None):
    """(shapes, rails) of the literal segments (rail_rects ends).  drawn: two VSS stripes per segment (enc1 form);
    sides: {id(seg): [offset sign, ...]} = only the drawn VSS shields shield_plan() found legal (VDD-facing sides)."""
    rr, rails = rail_rects(g)
    shapes, ws = [], nd["width"]
    for s, lay, c, w, lo, hi in rr:
        shapes.append((lay, NET, "mesh", round(c - w / 2, 6), round(c + w / 2, 6), lo, hi))
        off = w / 2 + rail_gap(w, hi - lo) + ws / 2
        sg_list = (-1, 1) if drawn else (sides or {}).get(id(s), ())
        for sg in sg_list:
            shapes.append((lay, shield, "rail_shield", round(c + sg * off - ws / 2, 6), round(c + sg * off + ws / 2, 6), lo, hi))
    return shapes, rails


# ---- S81-CORES-R24 (COORD ruling 1, 10-27): PHY PG bands + VSS-only PG shields --------------------------------------
PHY_PG_MIN_W = 1.0   # die PG stripes wider than this are PHY-domain PG (pd14: 1.92-um VDDPHY/VSS); core grid is 0.48
PHY_SPACE = 1.0      # every mesh rail keeps the 1.0-um wide-metal spacing to the PHY PG band, in every direction


def rect_gap(a, b):
    """edge-to-edge distance of two (x0, y0, x1, y1) rects (0 when they touch/overlap; Euclidean at corners)"""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


class StripeIndex:
    """PG stripes of one class per layer, searchable by across-axis centre"""

    def __init__(self, pgr, pick):
        self.rows = {"M8": [], "M9": []}
        for net, lay, x0, y0, x1, y1 in pgr:
            if lay in self.rows and pick(net, lay, x0, y0, x1, y1):
                c = (y0 + y1) / 2 if lay == "M8" else (x0 + x1) / 2
                self.rows[lay].append((c, (x0, y0, x1, y1), net))
        for L in self.rows:
            self.rows[L].sort(key=lambda r: r[0])
        self.cs = {L: [r[0] for r in self.rows[L]] for L in self.rows}

    def near(self, lay, lo, hi):
        cs = self.cs[lay]
        return self.rows[lay][bisect.bisect_left(cs, lo):bisect.bisect_right(cs, hi)]


def phy_index(pgr):
    return StripeIndex(pgr, lambda n, L, x0, y0, x1, y1: ((y1 - y0) if L == "M8" else (x1 - x0)) > PHY_PG_MIN_W)


def xy_rect(lay, c, w, lo, hi):
    return (lo, c - w / 2, hi, c + w / 2) if lay == "M8" else (c - w / 2, lo, c + w / 2, hi)


def phy_band_findings(shapes, phx, space=PHY_SPACE, kinds=("mesh",)):
    """encoded shapes of `kinds` closer than `space` (2-D edge distance) to any PHY PG stripe of the same layer"""
    bad = []
    for sh in shapes:
        if kinds is not None and sh[2] not in kinds:
            continue
        lay, plo, phi, alo, ahi = sh[0], sh[3], sh[4], sh[5], sh[6]
        r = (alo, plo, ahi, phi) if lay == "M8" else (plo, alo, phi, ahi)
        for c, st, net in phx.near(lay, plo - space - 2.0, phi + space + 2.0):
            gap = rect_gap(r, st)
            if gap < space - 1e-6:
                bad.append(dict(layer=lay, kind=sh[2], rect=[round(v, 4) for v in r], phy=[round(v, 4) for v in st], net=net, gap=round(gap, 4)))
                break
    return bad


def phy_clip(g, pgr, space=PHY_SPACE):
    """COORD R24 ruling 1: no mesh rail enters a PHY PG band.  Drops every literal segment whose metal (incl. its piece-
    end pad extension) is closer than `space` to a PHY PG stripe, then trims each remaining rail piece back to its last
    VIA89 crossing (a rail ends ON a crossing whose via array lies outside the band, never as a dangling stub), drops the
    vias that lost their M8 or M9 rail, and moves every attachment that lost its rail to the nearest remaining rail point
    (same rail end, or the crossing M9/M8 rail through the same row/column).  Widths/axes of kept segments unchanged.
    Returns (g2, report)."""
    phx = phy_index(pgr)
    segs = list(g["segments"])
    clipped, trimmed = 0, 0
    gone = set()        # (rail, along) endpoints of every dropped segment: only such piece ends are trimmed
    while True:
        cur = dict(g, segments=segs)
        rr, _ = rail_rects(cur)
        bad = set()
        for s, lay, c, w, lo, hi in rr:
            r = xy_rect(lay, c, w, lo, hi)
            for _, st, _ in phx.near(lay, c - w / 2 - space - 2.0, c + w / 2 + space + 2.0):
                if rect_gap(r, st) < space - 1e-6:
                    bad.add(id(s))
                    break
        # trim dangling piece ends back to a via crossing
        keep = [s for s in segs if id(s) not in bad]
        clipped += len(bad)
        for s in segs:
            if id(s) in bad:
                gone.update((rail_key(s), round(a, 6)) for a in seg_span(s))
        rails = collections.defaultdict(list)
        for s in keep:
            rails[rail_key(s)].append(s)
        kc = {k: [seg_span(s) for s in v] for k, v in rails.items()}
        _cov = lambda lay, c, a: any(lo - 1e-6 <= a <= hi + 1e-6 for lo, hi in kc.get((lay, round(c, 6)), ()))  # noqa: E731
        vxy = {(round(v["x_um"], 6), round(v["y_um"], 6)) for v in g["vias"]
               if _cov("M8", v["y_um"], v["x_um"]) and _cov("M9", v["x_um"], v["y_um"])}     # crossings still on both rails
        keep2, nt = [], 0
        on_via = lambda lay, c, a: ((round(a, 6), round(c, 6)) if lay == "M8" else (round(c, 6), round(a, 6))) in vxy  # noqa: E731
        for (lay, c), rs in rails.items():
            rs.sort(key=lambda s: seg_span(s)[0])
            pieces, cur_p = [], []
            for s in rs:
                if cur_p and abs(seg_span(cur_p[-1])[1] - seg_span(s)[0]) > 1e-6:
                    pieces.append(cur_p); cur_p = []
                cur_p.append(s)
            if cur_p:
                pieces.append(cur_p)
            for pc in pieces:
                i, j = 0, len(pc)
                while i < j and ((lay, c), round(seg_span(pc[i])[0], 6)) in gone and not on_via(lay, c, seg_span(pc[i])[0]):
                    gone.update(((lay, c), round(a, 6)) for a in seg_span(pc[i]))
                    i += 1
                while j > i and ((lay, c), round(seg_span(pc[j - 1])[1], 6)) in gone and not on_via(lay, c, seg_span(pc[j - 1])[1]):
                    gone.update(((lay, c), round(a, 6)) for a in seg_span(pc[j - 1]))
                    j -= 1
                nt += len(pc) - (j - i)
                keep2 += pc[i:j]
        trimmed += nt
        if not bad and not nt:
            break
        segs = keep2
    # vias: keep a crossing only while BOTH its M8 and M9 rails still cover it
    cover = collections.defaultdict(list)
    for s in segs:
        cover[rail_key(s)].append(seg_span(s))
    def covered(lay, c, a):
        return any(lo - 1e-6 <= a <= hi + 1e-6 for lo, hi in cover.get((lay, round(c, 6)), ()))
    vias = [v for v in g["vias"] if covered("M8", v["y_um"], v["x_um"]) and covered("M9", v["x_um"], v["y_um"])]
    # rail pieces left without any path to the main mesh (e.g. a rail run wholly inside a PHY domain) are floating
    # metal: drop them (reported), keeping the largest connected piece set
    pieces = []          # [key, lo, hi, [segs]]
    by_rail = collections.defaultdict(list)
    for s in segs:
        by_rail[rail_key(s)].append(s)
    for key, rs in by_rail.items():
        rs.sort(key=lambda s: seg_span(s)[0])
        for s in rs:
            if pieces and pieces[-1][0] == key and abs(pieces[-1][2] - seg_span(s)[0]) <= 1e-6:
                pieces[-1][2] = seg_span(s)[1]; pieces[-1][3].append(s)
            else:
                pieces.append([key, seg_span(s)[0], seg_span(s)[1], [s]])
    plook = collections.defaultdict(list)
    for i, pc in enumerate(pieces):
        plook[pc[0]].append(i)
    par = list(range(len(pieces)))
    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    def piece_at(lay, c, a):
        for i in plook.get((lay, round(c, 6)), ()):
            if pieces[i][1] - 1e-6 <= a <= pieces[i][2] + 1e-6:
                return i
        return None
    for v in vias:
        i, j = piece_at("M8", v["y_um"], v["x_um"]), piece_at("M9", v["x_um"], v["y_um"])
        par[find(i)] = find(j)
    comp = collections.Counter(find(i) for i in range(len(pieces)))
    main = comp.most_common(1)[0][0] if comp else None
    floating = [pc for i, pc in enumerate(pieces) if find(i) != main]
    if floating:
        drop = {id(s) for pc in floating for s in pc[3]}
        segs = [s for s in segs if id(s) not in drop]
        cover = collections.defaultdict(list)
        for s in segs:
            cover[rail_key(s)].append(seg_span(s))
        vias = [v for v in vias if covered("M8", v["y_um"], v["x_um"]) and covered("M9", v["x_um"], v["y_um"])]
    # attachments
    m9x = sorted({k[1] for k in cover if k[0] == "M9"})
    m8y = sorted({k[1] for k in cover if k[0] == "M8"})
    att, moved = [], []
    for a in g["attachments"]:
        x, y = a["xy_um"]
        lay = a["layer"]
        c, q = (y, x) if lay == "M8" else (x, y)
        if covered(lay, c, q):
            att.append(a)
            continue
        cands = []
        for lo, hi in cover.get((lay, round(c, 6)), ()):         # same rail, nearest kept end
            e = lo if abs(q - lo) < abs(q - hi) else hi
            cands.append((abs(q - e), lay, [e, c] if lay == "M8" else [c, e]))
        P, axes = ("M9", m9x) if lay == "M8" else ("M8", m8y)      # crossing rail through the same row/column
        i = bisect.bisect_left(axes, q)
        for ax in axes[max(0, i - 3):i + 3]:
            if covered(P, ax, c):
                cands.append((abs(q - ax), P, [ax, c] if P == "M9" else [c, ax]))
        if not cands:
            raise ValueError("attachment has no rail left after the PHY clip: " + str(a))
        d, L2, xy = min(cands, key=lambda t: (t[0], t[1]))
        moved.append(dict(role=a["role"], units=a["units"][:2], frm=[lay, x, y], to=[L2] + xy, dist_um=round(d, 4)))
        att.append(dict(a, layer=L2, xy_um=[round(v, 6) for v in xy]))
    g2 = dict(g, segments=segs, vias=vias, attachments=att)
    rep = dict(phy_stripes=sum(len(v) for v in phx.rows.values()), segments_clipped=clipped, segments_trimmed=trimmed,
               floating_pieces_dropped=len(floating), floating_segments_dropped=sum(len(pc[3]) for pc in floating),
               segments_kept=len(segs), vias_dropped=len(g["vias"]) - len(vias),
               rails_removed=len({rail_key(s) for s in g["segments"]}) - len({rail_key(s) for s in segs}),
               attachments_moved=len(moved), attachments_moved_by_role=dict(collections.Counter(m["role"] for m in moved)),
               attachment_move_max_um=round(max([m["dist_um"] for m in moved] or [0]), 4))
    return g2, rep, moved


def clip_ends(g, pgr, reach=12.0):
    """[x, y] of rail piece ends within `reach` um of a PHY PG stripe (zoom targets for the full-metal review)"""
    phx = phy_index(pgr)
    rr, _ = rail_rects(g)
    out = []
    for s, lay, c, w, lo, hi in rr:
        for a in (lo, hi):
            p = (a, c) if lay == "M8" else (c, a)
            if any(rect_gap((p[0], p[1], p[0], p[1]), st) < reach for _, st, _ in phx.near(lay, c - reach - 1, c + reach + 1)):
                out.append([round(p[0], 4), round(p[1], 4)])
    return sorted({tuple(x) for x in out})


def dangling_ends(g):
    """rail piece ends (rail ends and clip gaps) that do not sit on a VIA89 crossing of g"""
    vx = {(round(v["x_um"], 6), round(v["y_um"], 6)) for v in g["vias"]}
    by = collections.defaultdict(list)
    for s in g["segments"]:
        by[rail_key(s)].append(seg_span(s))
    out = []
    for (lay, c), sp in by.items():
        sp.sort()
        ends = [sp[0][0], sp[-1][1]]
        for (_, b0), (a1, _) in zip(sp, sp[1:]):
            if abs(a1 - b0) > 1e-6:
                ends += [b0, a1]
        for a in ends:
            if ((round(a, 6), round(c, 6)) if lay == "M8" else (round(c, 6), round(a, 6))) not in vx:
                out.append(dict(layer=lay, axis=c, end=a))
    return out


def pg_net_at(pgr):
    """{layer: {round(centre, 3): net}} of the core PG grid (one net per stripe centre, checked)"""
    m = {"M8": {}, "M9": {}}
    for net, lay, x0, y0, x1, y1 in pgr:
        if lay not in m:
            continue
        c = round((y0 + y1) / 2 if lay == "M8" else (x0 + x1) / 2, 3)
        if m[lay].setdefault(c, net) != net and "VSS" in (net, m[lay][c]):
            raise ValueError(f"PG stripe centre {lay} {c} carries VSS and {net}")
    return m


def shield_plan(g, pgr, nd, shield="VSS", drawn=False):
    """COORD R24 ruling 1 shield accounting, per rail segment side: the adjacent same-layer PG stripe (overlapping the
    segment's run) counts as the clock shield on that side only when it is VSS and at legal spacing (>= the wide-row
    space of the pair); a VDD/VDDPHY neighbour never counts -- that side gets a drawn VSS shield at the rail's wide-row
    gap when it fits before the VDD stripe (NDR/wide space), else it is MISSING.  Returns (sides, report, rows)."""
    idx = StripeIndex(pgr, lambda *a: True)
    ws = nd["width"]
    sides, cnt, um = {}, collections.Counter(), collections.Counter()
    rows = []
    for s in g["segments"]:
        lay = s["layer"]
        x0, y0, x1, y1 = s["centre_um"]
        c = y0 if lay == "M8" else x0
        a0, a1 = seg_span(s)
        w, run = s["width_um"], a1 - a0
        for sg in (-1, 1):
            best = None
            for pc, st, net in idx.near(lay, c - 6.0, c + 6.0):
                if sg * (pc - c) <= 0:
                    continue
                lo, hi = (st[0], st[2]) if lay == "M8" else (st[1], st[3])
                if min(hi, a1) - max(lo, a0) <= 0:
                    continue
                if best is None or abs(pc - c) < abs(best[0] - c):
                    best = (pc, st, net, (st[3] - st[1]) if lay == "M8" else (st[2] - st[0]))
            if best is None:
                k = "missing_no_pg"
            else:
                pc, st, net, pw = best
                gap = abs(pc - c) - w / 2 - pw / 2
                need = max(D.NDR["4w"]["space"], C.wide_spacing(max(w, pw), run))
                if net == shield:
                    k = "vss_pg" if gap >= need - 1e-6 else "vss_pg_illegal"
                else:
                    sneed = rail_gap(w, run) + ws + max(nd["space"], C.wide_spacing(max(ws, pw), run))
                    if gap >= sneed - 1e-6:
                        k = "vss_drawn" if drawn else "missing_vdd_side_drawable"
                        sides.setdefault(id(s), []).append(sg)
                    else:
                        k = "missing_vdd_side"
                        if len(rows) < 400:
                            rows.append(dict(layer=lay, axis=c, span=[a0, a1], width=w, side=sg, pg=pc, net=net, gap=round(gap, 4), need_drawn=round(sneed, 4)))
            cnt[k] += 1
            um[k] += run
    rep = dict(sides=dict(cnt), side_um={k: round(v, 1) for k, v in um.items()},
               missing_by_width=dict(collections.Counter(str(r["width"]) for r in rows)))
    return sides, rep, rows


def subtract(iv, cuts, min_len=0.0):
    """interval iv minus the union of cuts -> remaining pieces longer than min_len"""
    out = [list(iv)]
    for a, b in sorted(cuts):
        nxt = []
        for lo, hi in out:
            if b <= lo or a >= hi:
                nxt.append([lo, hi]); continue
            if a > lo:
                nxt.append([lo, a])
            if b < hi:
                nxt.append([b, hi])
        out = nxt
    return [(round(lo, 6), round(hi, 6)) for lo, hi in out if hi - lo > min_len + 1e-9]


def vss_shields(g, pgr, nd, shield="VSS", space=PHY_SPACE, pitch=4.32, pgw=0.48, junction_frac=0.9, row_limit=400):
    """--vss-side drawn shields: per rail segment one VSS stripe on its VDD-facing side at the segment's own wide-row
    gap, drawn only when it fits before the VDD stripe (wide row vs that stripe); then cut (2-D) to keep `space` from
    every PHY PG stripe and the wide-row space from every wider graded neighbour segment of the same rail (the shield
    steps with the grading; short gaps remain only at width steps).  A segment side counts vss_drawn when fully
    covered, vss_drawn_junction_trimmed when >= junction_frac covered and every gap is a width-step cut, else missing.
    Returns (shapes, report, rows)."""
    nm = pg_net_at(pgr)
    phx = phy_index(pgr)
    rr, _ = rail_rects(g)
    byrail = collections.defaultdict(list)
    for t in rr:
        byrail[(t[1], t[2])].append(t)
    ws = nd["width"]
    shapes, cnt, um, rows = [], collections.Counter(), collections.Counter(), []
    for (lay, c), ts in byrail.items():
        k = math.floor(c / pitch)
        lo_c, hi_c = round(k * pitch, 3), round((k + 1) * pitch, 3)
        vdd = hi_c if nm[lay].get(lo_c) == shield else lo_c if nm[lay].get(hi_c) == shield else None
        for i, (s, _, _, w, lo, hi) in enumerate(ts):
            a0, a1 = seg_span(s)
            cover, why = [], "missing_no_pg"
            if vdd is not None:
                why = "missing_vdd_side"
                sg = 1 if vdd > c else -1
                run = hi - lo
                room = abs(vdd - c) - w / 2 - pgw / 2
                sneed = rail_gap(w, run) + ws + max(nd["space"], C.wide_spacing(max(ws, pgw), run))
                if room >= sneed - 1e-6:
                    off = c + sg * (w / 2 + rail_gap(w, run) + ws / 2)
                    plo, phi = off - ws / 2, off + ws / 2
                    cuts, jcuts = [], []
                    for _, st, _ in phx.near(lay, plo - space - 2.0, phi + space + 2.0):
                        slo, shi, alo, ahi = (st[1], st[3], st[0], st[2]) if lay == "M8" else (st[0], st[2], st[1], st[3])
                        lat = max(slo - phi, plo - shi, 0.0)
                        if lat < space - 1e-6:
                            d = math.sqrt(space * space - lat * lat)
                            cuts.append((alo - d, ahi + d))
                    for j in range(max(0, i - 3), min(len(ts), i + 4)):
                        if j == i:
                            continue
                        _, _, _, wn, nlo, nhi = ts[j]
                        lat = abs(off - c) - ws / 2 - wn / 2
                        req = rail_gap(wn, 1e9)
                        if lat < req - 1e-6:
                            jcuts.append((nlo - req, nhi + req))     # box (census) metric at width steps
                    cover = subtract((lo, hi), cuts + jcuts, min_len=2 * ws)
                    for x0, x1 in cover:
                        shapes.append((lay, shield, "rail_shield", round(plo, 6), round(phi, 6), x0, x1))
                    got = sum(max(0.0, min(x1, a1) - max(x0, a0)) for x0, x1 in cover)
                    nophy = not subtract((a0, a1), [(x0, x1) for x0, x1 in cover] + jcuts)   # every gap is a width-step cut
                    if got >= (a1 - a0) - 1e-6:
                        why = "vss_drawn"
                    elif got >= junction_frac * (a1 - a0) and nophy:
                        why = "vss_drawn_junction_trimmed"
                    else:
                        why = "missing_vdd_side_partial" if cover else "missing_vdd_side"
            cnt[why] += 1; um[why] += a1 - a0
            if why.startswith("missing") and len(rows) < row_limit:
                rows.append(dict(layer=lay, axis=c, span=[a0, a1], width=w, vdd=vdd, kind=why))
    rep = dict(shield_shapes=len(shapes), vdd_sides=dict(cnt), vdd_side_um={k: round(v, 1) for k, v in um.items()},
               missing_by_width=dict(collections.Counter(str(r["width"]) for r in rows)))
    return shapes, rep, rows


# ---- S81-CORES-R24b (COORD ruling c, 10-27): 100 % VSS shield coverage ----------------------------------------------
def shield_width_cap(nd, pitch=4.32, pgw=0.48, grid=0.08, wmax=M8_MAXWIDTH):
    """widest rail (on the 0.08 grid) whose core PG gap still holds: VSS stripe | wide-row space | rail | wide-row space |
    drawn VSS shield | NDR/wide space | VDD stripe"""
    gap = pitch - pgw
    w = round(math.floor(wmax / grid + 1e-9) * grid, 6)
    while w > 0:
        need = (max(D.NDR["4w"]["space"], C.wide_spacing(max(w, pgw), 1e9)) + w + rail_gap(w, 1e9) + nd["width"]
                + max(nd["space"], C.wide_spacing(max(nd["width"], pgw), 1e9)))
        if need <= gap + 1e-6:
            return w
        w = round(w - grid, 6)
    raise ValueError("no rail width fits a shielded PG gap")


def cap_widths(g, cap):
    """the same literal mesh with every segment wider than `cap` narrowed to `cap` (axis/span unchanged) and every
    VIA89 array shrunk to the cuts that still fit the narrowed metal; returns (g2, report incl. an R estimate)"""
    segs, n, um, dr = [], collections.Counter(), 0.0, []
    for s in g["segments"]:
        w = s["width_um"]
        if w <= cap + 1e-9:
            segs.append(s); continue
        x0, y0, x1, y1 = s["centre_um"]
        r = [x0, y0 - cap / 2, x1, y1 + cap / 2] if s["layer"] == "M8" else [x0 - cap / 2, y0, x1 + cap / 2, y1]
        segs.append(dict(s, width_um=cap, rect_um=[round(v, 6) for v in r]))
        n[(s["layer"], w)] += 1
        L = abs(x1 - x0) + abs(y1 - y0)
        um += L
        dr.append(w / cap - 1.0)
    vias, cuts0, cuts1 = [], 0, 0
    for v in g["vias"]:
        cuts0 += v["rows"] * v["cols"]
        if v["pad_um"] > cap + 1e-9:
            k = int(math.floor((cap - v["pad_um"] + (v["rows"] - 1) * v["pitch_um"]) / v["pitch_um"] + 1e-9)) + 1
            k = max(1, min(k, v["rows"]))
            pad = round(v["pad_um"] - (v["rows"] - k) * v["pitch_um"], 6)
            v = dict(v, rows=k, cols=k, pad_um=pad)
        cuts1 += v["rows"] * v["cols"]
        vias.append(v)
    rep = dict(cap_um=cap, segments_narrowed=sum(n.values()), narrowed_by_layer_width={f"{k[0]}:{k[1]}": c for k, c in sorted(n.items())},
               narrowed_um=round(um, 1), segment_R_increase_max_pct=round(100 * max(dr or [0]), 2),
               via_cuts_before=cuts0, via_cuts_after=cuts1)
    return dict(g, segments=segs, vias=vias), rep


def _stripe_cuts(lay, plo, phi, alo, ahi, idx, space, nd, shield):
    """along-axis cuts of a shield strip [plo, phi] x [alo, ahi] (2-D): `space` from every PHY PG stripe (any net), the
    NDR/wide space from every core PG stripe of another net; same-net core VSS stripes need no space"""
    cuts = []
    for _, st, net in idx.near(lay, plo - 4.0, phi + 4.0):
        slo, shi, a0, a1 = (st[1], st[3], st[0], st[2]) if lay == "M8" else (st[0], st[2], st[1], st[3])
        pw = shi - slo
        if pw > PHY_PG_MIN_W:
            req = space
        elif net == shield:
            continue
        else:
            req = max(nd["space"], C.wide_spacing(max(pw, phi - plo), max(0.0, min(a1, ahi) - max(a0, alo))))
        lat = max(slo - phi, plo - shi, 0.0)
        if lat < req - 1e-6:
            d = math.sqrt(req * req - lat * lat)
            cuts.append((a0 - d, a1 + d))
    return cuts


def _vss_cover(lay, c, w, a0, a1, sg, idx, shield, reach=6.0):
    """[(along lo, along hi, stripe rect, phy)] of [a0, a1] covered on side sg by an adjacent legal VSS PG stripe with
    no other-net PG stripe nearer over that run"""
    vss, other = [], []
    for pc, st, net in idx.near(lay, c - reach, c + reach):
        if sg * (pc - c) <= 0:
            continue
        slo, shi, s0, s1 = (st[1], st[3], st[0], st[2]) if lay == "M8" else (st[0], st[2], st[1], st[3])
        gap = (slo - (c + w / 2)) if sg > 0 else ((c - w / 2) - shi)
        ov = (max(s0, a0), min(s1, a1))
        if ov[1] - ov[0] <= 1e-9:
            continue
        (vss if net == shield else other).append((gap, ov, st, shi - slo))
    out = []
    for gap, ov, st, pw in vss:
        if gap < max(D.NDR["4w"]["space"], C.wide_spacing(max(w, pw), ov[1] - ov[0])) - 1e-6:
            continue
        for x0, x1 in subtract(ov, [o for gq, o, _, _ in other if gq < gap]):
            out.append((x0, x1, st, pw > PHY_PG_MIN_W))
    return out


def _vss_side_fill(lay, c, sg, pc, inf, idx, space, nd, shield, ws, ext=2.0):
    """drawn VSS strips on the VSS side (sign sg) of rail piece pc over every run its VSS PG stripes leave uncovered"""
    P0, P1 = pc[0][4], pc[-1][5]
    cov = []
    for _, _, _, w, lo, hi in pc:
        cov += [(x0, x1) for x0, x1, _, _ in _vss_cover(lay, c, w, max(lo, P0), min(hi, P1), sg, idx, shield)]
    holes = subtract((seg_span(pc[0][0])[0], seg_span(pc[-1][0])[1]), cov)      # over the literal spans (no pad ext)
    out = []
    for u0, u1 in holes:
        e0, e1 = max(P0, u0 - ext), min(P1, u1 + ext)
        bp = sorted({e0, e1} | {min(max(v, e0), e1) for a, b, _ in inf for v in (a, b)})
        for a, b in zip(bp, bp[1:]):
            if b - a <= 1e-9:
                continue
            m = (a + b) / 2
            o = max(off for lo, hi, off in inf if lo < m < hi)
            p = c + sg * o
            for x0, x1 in subtract((a, b), _stripe_cuts(lay, p - ws / 2, p + ws / 2, a, b, idx, space, nd, shield), min_len=0.0):
                out.append((lay, shield, "rail_shield", round(p - ws / 2, 6), round(p + ws / 2, 6), round(x0, 6), round(x1, 6)))
        # bridge onto a core (non-PHY) VSS stripe inside each extension, where one covers the rail
        for z0, z1 in ((e0, u0), (u1, e1)):
            if z1 - z0 < ws - 1e-9:
                continue
            for x0, x1, st, phy in _vss_cover(lay, c, 0.0, z0, z1, sg, idx, shield):
                if phy or x1 - x0 < ws - 1e-9:
                    continue
                m = (x0 + x1) / 2
                o = max([off for lo, hi, off in inf if lo < m < hi] or [0])
                slo, shi = (st[1], st[3]) if lay == "M8" else (st[0], st[2])
                pin = c + sg * (o - ws / 2)
                far = slo if sg > 0 else shi
                q0, q1 = sorted((pin, far))
                al = (round(m - ws / 2, 6), round(m + ws / 2, 6))
                if [z for z in _stripe_cuts(lay, q0, q1, al[0], al[1], idx, space, nd, shield) if z[0] < al[1] and z[1] > al[0]]:
                    continue
                out.append((lay, shield, "rail_shield", round(q0, 6), round(q1, 6), al[0], al[1]))
                break
    return out


def shield_profile(g, pgr, nd, shield="VSS", space=PHY_SPACE, pitch=4.32):
    """--shield-full: one drawn VSS shield per rail on its VDD side, as a stepped profile.  At every along position t
    the shield sits at O(t) = max over the rail segments whose box-spacing reach covers t of (w/2 + wide-row gap(w) +
    ws/2), so it steps WITH the grading (no gap at width steps); steps are joined by a ws-long across-axis bridge inside
    the lower-offset run.  Cut (2-D) only where a PHY PG stripe (1.0 um) or another-net PG stripe would be too close.
    Returns (shapes, runs) -- runs = [(rail key, side sign, along lo, along hi, offset)] of the drawn strips."""
    nm = pg_net_at(pgr)
    idx = StripeIndex(pgr, lambda *a: True)
    rr, _ = rail_rects(g)
    byrail = collections.defaultdict(list)
    for t in rr:
        byrail[(t[1], t[2])].append(t)
    ws = nd["width"]
    shapes, runs = [], []
    for (lay, c), ts in byrail.items():
        k = math.floor(c / pitch)
        lo_c, hi_c = round(k * pitch, 3), round((k + 1) * pitch, 3)
        vdd = hi_c if nm[lay].get(lo_c) == shield else lo_c if nm[lay].get(hi_c) == shield else None
        if vdd is None:
            continue
        sg = 1 if vdd > c else -1
        ts = sorted(ts, key=lambda t: t[4])
        pieces, cur = [], []
        for t in ts:
            if cur and t[4] > cur[-1][5] + 1e-6:
                pieces.append(cur); cur = []
            cur.append(t)
        if cur:
            pieces.append(cur)
        for pc in pieces:
            P0, P1 = pc[0][4], pc[-1][5]
            inf = []
            for _, _, _, w, lo, hi in pc:
                req = rail_gap(w, 1e9)
                inf.append((lo - req, hi + req, w / 2 + req + ws / 2))
            bp = sorted({P0, P1} | {min(max(v, P0), P1) for a, b, _ in inf for v in (a, b)})
            ivs = []
            for a, b in zip(bp, bp[1:]):
                if b - a <= 1e-9:
                    continue
                m = (a + b) / 2
                o = round(max(off for lo, hi, off in inf if lo < m < hi), 6)
                if ivs and abs(ivs[-1][2] - o) < 1e-9 and abs(ivs[-1][1] - a) < 1e-9:
                    ivs[-1][1] = b
                else:
                    ivs.append([a, b, o])
            kept = []
            for a, b, o in ivs:
                p = c + sg * o
                cov = subtract((a, b), _stripe_cuts(lay, p - ws / 2, p + ws / 2, a, b, idx, space, nd, shield), min_len=2 * ws)
                kept.append((a, b, o, cov))
                for x0, x1 in cov:
                    shapes.append((lay, shield, "rail_shield", round(p - ws / 2, 6), round(p + ws / 2, 6), x0, x1))
                    runs.append(((lay, c), sg, x0, x1, o))
            # VSS side: wherever no legal adjacent VSS PG stripe covers the rail (PG interruptions, e.g. the 7.44-um
            # PHY-domain / core-grid hand-over), a drawn VSS fill strip at the same stepped offset, extended into the
            # covered run and bridged onto the core VSS stripe there (same net) so it is tied without a VIA89
            shapes += _vss_side_fill(lay, c, -sg, pc, inf, idx, space, nd, shield, ws)
            for (a0, b0, o0, c0), (a1, b1, o1, c1) in zip(kept, kept[1:]):
                tb = b0
                if abs(a1 - tb) > 1e-9 or not c0 or not c1 or abs(c0[-1][1] - tb) > 1e-9 or abs(c1[0][0] - tb) > 1e-9:
                    continue
                lo_o, hi_o = min(o0, o1), max(o0, o1)
                al = (tb - ws, tb) if o0 < o1 else (tb, tb + ws)
                pl, ph = sorted((c + sg * lo_o, c + sg * hi_o))
                bl = (round(pl - ws / 2, 6), round(ph + ws / 2, 6))
                cl = [(x0, x1) for x0, x1 in _stripe_cuts(lay, bl[0], bl[1], al[0], al[1], idx, space, nd, shield) if x0 < al[1] and x1 > al[0]]
                if cl:
                    continue
                shapes.append((lay, shield, "rail_shield", bl[0], bl[1], round(al[0], 6), round(al[1], 6)))
    return shapes, runs


def shield_census(g, pgr, shapes, nd, shield="VSS", reach=6.0, row_limit=400):
    """per rail segment, BOTH sides: the along length NOT covered by a VSS shape that is the rail's adjacent metal on
    that side at legal spacing (a drawn VSS shield, or a VSS PG stripe with no other-net PG stripe nearer over that
    run; a VDD/VDDPHY stripe never counts).  A side is unshielded when any length > 1 nm is uncovered."""
    idx = StripeIndex(pgr, lambda *a: True)
    sh = collections.defaultdict(list)          # (layer, side-rail axis) via across-centre index of drawn shields
    for s in shapes:
        if s[2] == "rail_shield" and s[1] == shield:
            sh[s[0]].append(((s[3] + s[4]) / 2, s[3], s[4], s[5], s[6]))
    for L in sh:
        sh[L].sort()
    shc = {L: [r[0] for r in sh[L]] for L in sh}
    cnt, um, rows = collections.Counter(), collections.Counter(), []
    for s in g["segments"]:
        lay = s["layer"]
        x0, y0, x1, y1 = s["centre_um"]
        c = y0 if lay == "M8" else x0
        a0, a1 = seg_span(s)
        w = s["width_um"]
        for sg in (-1, 1):
            vss, other = [], []
            for pc, st, net in idx.near(lay, c - reach, c + reach):
                if sg * (pc - c) <= 0:
                    continue
                slo, shi, s0, s1 = (st[1], st[3], st[0], st[2]) if lay == "M8" else (st[0], st[2], st[1], st[3])
                gap = (slo - (c + w / 2)) if sg > 0 else ((c - w / 2) - shi)
                ov = (max(s0, a0), min(s1, a1))
                if ov[1] - ov[0] <= 1e-9:
                    continue
                (vss if net == shield else other).append((gap, ov, shi - slo))
            covered = []
            for gap, ov, pw in vss:
                need = max(D.NDR["4w"]["space"], C.wide_spacing(max(w, pw), ov[1] - ov[0]))
                if gap < need - 1e-6:
                    continue
                covered += subtract(ov, [o for gq, o, _ in other if gq < gap])
            L = sh.get(lay, [])
            cs = shc.get(lay, [])
            for q in L[bisect.bisect_left(cs, c - reach):bisect.bisect_right(cs, c + reach)]:
                qc, plo, phi, s0, s1 = q
                if sg * (qc - c) <= 0:
                    continue
                gap = (plo - (c + w / 2)) if sg > 0 else ((c - w / 2) - phi)
                if gap < max(D.NDR["4w"]["space"], C.wide_spacing(w, 1e9)) - 1e-6 and gap < rail_gap(w, s1 - s0) - 1e-6:
                    continue
                ov = (max(s0, a0), min(s1, a1))
                if ov[1] - ov[0] <= 1e-9:
                    continue
                covered += subtract(ov, [o for gq, o, _ in other if gq < gap])
            miss = subtract((a0, a1), covered)
            ml = sum(b - a for a, b in miss)
            k = "shielded" if ml <= 1e-3 else "unshielded"
            cnt[k] += 1; um[k] += ml if k == "unshielded" else (a1 - a0)
            if k == "unshielded" and len(rows) < row_limit:
                rows.append(dict(layer=lay, axis=c, span=[a0, a1], width=w, side=sg, missing=[[round(a, 4), round(b, 4)] for a, b in miss]))
    return dict(sides=dict(cnt), unshielded_um=round(um["unshielded"], 3), shielded_side_um=round(um["shielded"], 1)), rows


def shield_ties(shapes, pgr, shield="VSS", cut=0.04):
    """VIA89 ties of the drawn shields to the die VSS grid: one cut wherever a shield strip crosses an orthogonal-layer
    VSS stripe with the cut inside both; shields joined by bridges/abutment form one group; a group without a tie is
    floating.  Returns (ties [(x, y)], report)."""
    other = {"M8": "M9", "M9": "M8"}
    vx = StripeIndex(pgr, lambda n, L, *a: n == shield)
    sh = [s for s in shapes if s[2] == "rail_shield" and s[1] == shield]
    par = list(range(len(sh)))

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    by = collections.defaultdict(list)
    for i, s in enumerate(sh):
        by[(s[0], math.floor((s[3] + s[4]) / 2 / 4.32))].append(i)   # one rail gap per bucket
    for (lay, b), ids in by.items():
        ids2 = ids + by.get((lay, b - 1), []) + by.get((lay, b + 1), [])
        ids.sort(key=lambda i: sh[i][5])
        for i in ids:
            for j in ids2:
                if j <= i:
                    continue
                s, t = sh[i], sh[j]
                if max(t[3] - s[4], s[3] - t[4]) <= 1e-6 and max(t[5] - s[6], s[5] - t[6]) <= 1e-6:
                    par[find(i)] = find(j)
    ties, tied = [], set()
    for i, s in enumerate(sh):
        lay, plo, phi, alo, ahi = s[0], s[3], s[4], s[5], s[6]
        if phi - plo < 2 * cut - 1e-9:
            continue
        pc = (plo + phi) / 2
        for c2, st, _ in vx.near(other[lay], alo + cut, ahi - cut):
            # orthogonal stripe: its across-centre c2 lies on this shield's along axis; its along span must cover pc
            a0, a1 = (st[1], st[3]) if lay == "M8" else (st[0], st[2])
            if a0 + cut <= pc <= a1 - cut:
                ties.append((round(c2, 6), round(pc, 6)) if lay == "M8" else (round(pc, 6), round(c2, 6)))
                tied.add(find(i))
                break
    same = StripeIndex(pgr, lambda n, L, *a: n == shield and (((a[3] - a[1]) if L == "M8" else (a[2] - a[0])) <= PHY_PG_MIN_W))
    touch = 0
    for i, s in enumerate(sh):
        if find(i) in tied:
            continue
        lay, plo, phi, alo, ahi = s[0], s[3], s[4], s[5], s[6]
        for _, st, _ in same.near(lay, plo - 1.0, phi + 1.0):
            q0, q1, b0, b1 = (st[1], st[3], st[0], st[2]) if lay == "M8" else (st[0], st[2], st[1], st[3])
            if max(q0 - phi, plo - q1) <= 1e-6 and max(b0 - ahi, alo - b1) <= 1e-6:
                tied.add(find(i)); touch += 1
                break
    groups = {find(i) for i in range(len(sh))}
    floating = groups - tied
    rep = dict(shield_shapes=len(sh), shield_groups=len(groups), tie_vias=len(ties), groups_tied_by_core_vss_touch=touch, floating_groups=len(floating),
               floating_um=round(sum(sh[i][6] - sh[i][5] for i in range(len(sh)) if find(i) in floating), 3))
    return ties, rep, [list(sh[i]) for i in range(len(sh)) if find(i) in floating][:200]


def vss_side_axis(c, wmax, netmap, lay, pitch=4.32, pgw=0.48, track=0.08, toff=0.04):
    """axis in c's 4.32-um PG gap with the rail's widest metal at the legal wide-row space from the VSS stripe (so the
    VSS stripe is its adjacent shield and the VDD side keeps the most room for a drawn VSS shield); falls back to the
    gap centre when the far side would be illegal or the gap has no VSS stripe"""
    k = math.floor(c / pitch)
    lo, hi = round(k * pitch, 3), round((k + 1) * pitch, 3)
    nl, nh = netmap[lay].get(lo), netmap[lay].get(hi)
    if "VSS" not in (nl, nh):
        return gap_axis(c, pitch)
    need = rail_gap(wmax, 1e9)
    if nl == "VSS":
        a = lo + pgw / 2 + need + wmax / 2
        a = toff + math.ceil((a - toff) / track - 1e-9) * track
        far = hi - pgw / 2 - (a + wmax / 2)
    else:
        a = hi - pgw / 2 - need - wmax / 2
        a = toff + math.floor((a - toff) / track + 1e-9) * track
        far = (a - wmax / 2) - (lo + pgw / 2)
    if far < need - 1e-6:
        return gap_axis(c, pitch)
    return round(a, 6)


def via_findings(g, shapes):
    """VIA89 pads that are not inside the union of the incident M8 and M9 rail rects"""
    idx = {"M8": collections.defaultdict(list), "M9": collections.defaultdict(list)}
    for s in shapes:
        if s[2] == "mesh":
            idx[s[0]][round((s[3] + s[4]) / 2, 6)].append(s)
    bad = []
    for v in g["vias"]:
        x, y, h = v["x_um"], v["y_um"], v["pad_um"] / 2
        for lay, c, q in (("M8", y, x), ("M9", x, y)):
            rs = idx[lay].get(round(c, 6), [])
            inc = [r for r in rs if r[5] - 1e-6 <= q <= r[6] + 1e-6]
            ok = bool(inc) and all(r[3] <= c - h + 1e-6 and c + h <= r[4] + 1e-6 for r in inc) \
                and min(r[5] for r in inc) <= q - h + 1e-6 and q + h <= max(r[6] for r in inc) + 1e-6
            if not ok:
                bad.append(dict(via=[x, y], layer=lay, pad_um=v["pad_um"], incident=[list(r) for r in inc]))
    return bad


def pg_gap_findings(rails, pgr):
    """rails sharing one PG gap, and rails whose metal is closer than the wide row to a PG stripe (across-axis)"""
    pgc = {"M8": sorted({round((r[3] + r[5]) / 2, 6) for r in pgr if r[1] == "M8"}),
           "M9": sorted({round((r[2] + r[4]) / 2, 6) for r in pgr if r[1] == "M9"})}
    gaps, close = collections.defaultdict(list), []
    for (lay, c), segs in rails.items():
        cs = pgc[lay]
        i = bisect.bisect_left(cs, c)
        lo = cs[i - 1] if i else None
        hi = cs[i] if i < len(cs) else None
        gaps[(lay, lo, hi)].append(c)
        w = max(s["width_um"] for s in segs)
        for p in (lo, hi):
            if p is not None and abs(c - p) - w / 2 - PG_W / 2 < rail_gap(w, 1e9) - 1e-6:
                close.append(dict(layer=lay, rail=c, pg=p, width=w))
    shared = [dict(layer=k[0], gap=[k[1], k[2]], rails=v) for k, v in gaps.items() if len(v) > 1]
    return shared, close


def bank_tie(router, cells, bank_units, attach, nd):
    """M8 collector over all unit Y pins + jog onto the rail; per unit M1-M7 stack and M7 riser. Returns segs, stacks."""
    pins = [C.pin_xy(cells, u, "Y", D.ROW_Y) for u in bank_units]
    xs, ys = [p[0] for p in pins], [p[1] for p in pins]
    ax, ay = attach["xy_um"]
    yc = sum(ys) / len(ys)
    segs, errs = [], []
    if attach["layer"] == "M9":           # vertical rail at x=ax: the collector runs on M8 straight onto it
        a0, a1 = min(xs + [ax]), max(xs + [ax])
        c, m, e = router.place("M8", yc, a0, a1, NET)
        if c is None:
            errs.append(dict(kind="no_collector_track", units=bank_units, ideal=yc))
            return segs, [], errs
        segs.append(("M8", a0, c, a1, c, NET, "bank", m, e))
        if abs(c - ay) > 1e-6:            # rail attachment y moves with the legal collector track
            attach["xy_um"] = [ax, c]
    else:                                  # horizontal rail at y=ay: M8 collector over the pins + M9 riser
        a0, a1 = min(xs), max(xs)
        c, m, e = router.place("M8", yc, a0 - 0.02, a1 + 0.02, NET)
        if c is None:
            errs.append(dict(kind="no_collector_track", units=bank_units, ideal=yc))
            return segs, [], errs
        segs.append(("M8", a0 - 0.02, c, a1 + 0.02, c, NET, "bank", m, e))
        xr = min(max(ax, a0), a1)
        cx, mx, ex = router.place("M9", xr, min(c, ay), max(c, ay), NET)
        if cx is None:
            errs.append(dict(kind="no_riser_track", units=bank_units, ideal=xr))
            return segs, [], errs
        segs.append(("M9", cx, min(c, ay), cx, max(c, ay), NET, "bank_riser", mx, ex))
        attach["xy_um"] = [cx, ay]
    stacks = [dict(unit=u, pin="Y", xy_um=[x, y], layers=list(STACK), riser_M7=[y, c], lands="M8") for u, (x, y) in zip(bank_units, pins)]
    return segs, stacks, errs


def stub_tie(router, cells, attach):
    u = attach["units"][0]
    px, py = C.pin_xy(cells, u, "A", D.ROW_Y)
    ax, ay = attach["xy_um"]
    if attach["layer"] == "M8":           # drop on M9 from the pin row onto the M8 rail
        c, m, e = router.place("M9", px, min(py, ay), max(py, ay), NET)
        if c is None:
            return [], None, dict(kind="no_stub_drop", unit=u, ideal=px)
        attach["xy_um"] = [c, ay]
        return [("M9", c, min(py, ay), c, max(py, ay), NET, "stub_drop", m, e)], \
            dict(unit=u, pin="A", xy_um=[px, py], layers=list(STACK) + ["M8"], lands="M9", jog_M8=[px, c]), None
    c, m, e = router.place("M8", py, min(px, ax), max(px, ax), NET)
    if c is None:
        return [], None, dict(kind="no_stub_drop", unit=u, ideal=py)
    attach["xy_um"] = [ax, c]
    return [("M8", min(px, ax), c, max(px, ax), c, NET, "stub_drop", m, e)], \
        dict(unit=u, pin="A", xy_um=[px, py], layers=list(STACK), lands="M8", riser_M7=[py, c]), None


def mesh_graph(g):
    """graded_mesh_graph summary; after a PHY clip the full-grid expected cycle count no longer applies, so a
    topology mismatch is returned (not raised) and judged on components == 1 by the caller"""
    import graded_mesh_graph as GG
    try:
        return GG.build(g)["summary"]
    except ValueError as ex:
        a = ex.args[0]
        if isinstance(a, tuple) and a and a[0] == "literal mesh graph topology":
            return dict(components=a[1], cycles=a[2], expected_cycles=a[3], full_grid_expected=False)
        raise


def encode(plan, build, out, limit=400, gap_snap=False, phy_clip_on=False, vss_side=False, shield_full=False):
    import die_infra as DI
    P = S.Plan(S.load(plan), str(plan))
    b, dst = Path(build), Path(out)
    dst.mkdir(parents=True, exist_ok=True)
    g = json.loads((b / "graded_metal.json").read_text())
    M = json.loads((b / "mesh.json").read_text())
    cells = json.loads((b / "place.json").read_text())
    nets = json.loads((b / "nets.json").read_text())["nets"]
    nd, sh = D.NDR[M["meta"].get("ndr", "4w")], "VSS"
    pgr = DI.pg_rects(P, C.pg_grid(P))
    snap, wcap = None, None
    if shield_full:  # R24b ruling c: every rail side shielded -> rails no wider than a shielded core PG gap holds
        vss_side = gap_snap = True
        g, wcap = cap_widths(g, shield_width_cap(nd))
    if gap_snap:     # rails to the actual 4.32-um PG gaps; PG stripes both sides are the rail shields (12.7a pg mode)
        g, snap = snap_to_pg_gaps(g, netmap=pg_net_at(pgr) if vss_side else None)
    clip, moved = None, []
    full_cycles = None
    if phy_clip_on:  # COORD R24 ruling 1: rails stop >= 1.0 um before every PHY PG band, at a VIA89 crossing
        full_cycles = mesh_graph(g)
        g, clip, moved = phy_clip(g, pgr)
    sides, shield_rep, shield_rows = shield_plan(g, pgr, nd, sh)
    rshapes, rails = rail_shapes(g, nd, sh, drawn=not gap_snap)
    tie_rep, ties_v, floating = None, [], []
    if shield_full:  # stepped per-rail VDD-side shield + both-side coverage census + VSS-grid ties
        dsh, _runs = shield_profile(g, pgr, nd, sh)
        rshapes += dsh
        crep, crows = shield_census(g, pgr, dsh, nd, sh)
        ties_v, tie_rep, floating = shield_ties(dsh, pgr, sh)
        shield_rep = dict(census=crep, ties=tie_rep, width_cap=wcap)
        shield_rows = crows
    elif vss_side:   # VSS stripe = shield on its side (accounted above); VDD side gets a drawn per-piece VSS shield
        dsh, drep, drows = vss_shields(g, pgr, nd, sh)
        rshapes += dsh
        shield_rep = dict(vss_side=dict((k, v) for k, v in shield_rep["sides"].items() if k.startswith("vss_pg")), drawn=drep)
        shield_rows = drows
    gfit = gap_fit_findings(g, pgr)
    wmax = {L: max([s["width_um"] for s in g["segments"] if s["layer"] == L] or [0]) for L in ("M8", "M9")}
    vbad = via_findings(g, rshapes)
    shared, close = pg_gap_findings(rails, pgr)
    graph = mesh_graph(g)
    # 1) PG, 2) literal rails + shields, 3) bank collectors / stub drops, 4) every tree net -- one router, in order
    router = C.TrackRouter(nd, sh, D.DEFAULT_TRACKS, D.TRACK_MOVE_UM)
    router.reserve(C.pg_shapes(pgr))
    router.reserve(rshapes)
    tie_segs, stacks, errs = [], [], []
    for a in g["attachments"]:
        if a["role"] == "driver":
            s_, st_, e_ = bank_tie(router, cells, a["units"], a, nd)
            tie_segs += s_; stacks += st_; errs += e_
        else:
            s_, st_, e_ = stub_tie(router, cells, a)
            tie_segs += s_
            if st_: stacks.append(st_)
            if e_: errs.append(e_)
    perr = []
    try:
        wires = C.fixed_wires(M, cells, nets, D.BUF_W, D.ROW_Y, router=router)
    except C.PlanError as ex:
        wires, perr = [], ex.args[0] if ex.args else [str(ex)]
    # full census: PG + rails/shields + ties + tree, every pair of different nets, PG wide rule included
    ties = C.clock_shapes([s[:7] + (s[7],) + (s[8],) for s in tie_segs], nd, sh)
    tree = C.clock_shapes(C.tree_segs(wires), nd, sh) if wires else []
    census = C.metal_census(C.pg_shapes(pgr) + rshapes + ties + tree, nd["space"], limit=limit)
    phx = phy_index(pgr)
    phyb_mesh = phy_band_findings(rshapes, phx, kinds=("mesh", "rail_shield"))
    phyb_other = phy_band_findings(ties + tree, phx, kinds=None)   # info: router-placed, already PG-wide-rule legal
    tree_mode = collections.Counter(m for w in wires for m in (w.get("shield_modes") or []))
    rep = dict(
        schema="opentallas.s81.graded_mesh_encode.v1",
        build=str(b), plan_sha256=hashlib.sha256(Path(plan).read_bytes()).hexdigest(),
        graded_metal_sha256=hashlib.sha256((b / "graded_metal.json").read_bytes()).hexdigest(),
        rails=dict(M8=sum(1 for k in rails if k[0] == "M8"), M9=sum(1 for k in rails if k[0] == "M9")),
        segments=len(g["segments"]), crossings=len(g["vias"]), via_cuts=sum(v["rows"] * v["cols"] for v in g["vias"]),
        rail_width_max_um=wmax, m8_maxwidth_um=M8_MAXWIDTH, m8_maxwidth_violations=sum(1 for s in g["segments"] if s["layer"] == "M8" and s["width_um"] > M8_MAXWIDTH + 1e-9),
        rail_end_extensions=sum(1 for s in rshapes if s[2] == "mesh") and None,
        via_outside_incident=len(vbad), gap_snap=snap, rail_shield_mode="pg" if gap_snap else "drawn",
        segments_not_fitting_pg_gap=len(gfit), segments_not_fitting_by_pg_width=dict(collections.Counter(str(f["pg_width"]) for f in gfit)), pg_gap_shared=len(shared), rail_pg_too_close=len(close),
        graph=graph, attachments=collections.Counter(a["role"] for a in g["attachments"]),
        bank_tie_segments=sum(1 for s in tie_segs if s[6] in ("bank", "bank_riser")),
        stub_drops=sum(1 for s in tie_segs if s[6] == "stub_drop"), pin_stacks=len(stacks), tie_errors=len(errs),
        tree_nets=len(wires), tree_segments=sum(len(w["segs"]) for w in wires), tree_mm=round(sum(w["wire_um"] for w in wires) / 1000, 3),
        tree_shield_modes=dict(tree_mode), tree_plan_errors=len(perr), router_modes=dict(router.modes),
        router_move_max_um=round(max(router.moves or [0]), 4), pg_rects=len(pgr),
        metal_shapes=census["shapes"], metal_shorts=census["shorts"], metal_spacing=census["spacing"],
        shorts_by_kind=census["shorts_by_kind"], spacing_by_kind=census["spacing_by_kind"],
        rail_ends_off_via=len(dangling_ends(g)), phy_clip=clip, graph_before_clip=full_cycles, phy_band_mesh=len(phyb_mesh), phy_band_other_info=len(phyb_other),
        shield_mode="full" if shield_full else ("vss_side" if vss_side else ("pg" if gap_snap else "drawn")), shield=shield_rep)
    rep["rail_end_extensions"] = 2 * (rep["rails"]["M8"] + rep["rails"]["M9"])
    fails = [k for k in ("segments_not_fitting_pg_gap", "m8_maxwidth_violations", "via_outside_incident", "pg_gap_shared", "rail_pg_too_close",
                         "tie_errors", "tree_plan_errors", "metal_shorts", "metal_spacing", "phy_band_mesh", "rail_ends_off_via") if rep[k]]
    if graph["components"] != 1 or (not phy_clip_on and graph["cycles"] != graph["expected_cycles"]):
        fails.append("graph_topology")
    if shield_full:
        if shield_rep["census"]["sides"].get("unshielded"):
            fails.append("shield_sides_missing")
        if tie_rep["floating_groups"]:
            fails.append("shield_floating")
    elif vss_side and (any(k.startswith("missing") for k in shield_rep["drawn"]["vdd_sides"]) or shield_rep["vss_side"].get("vss_pg_illegal")):
        fails.append("shield_sides_missing")
    rep["fails"] = fails
    rep["status"] = "ENCODED_CENSUS_PASS" if not fails else "ENCODED_CENSUS_FAIL"
    rep["physical_encoder_qualified"] = False
    rep["limits"] = ["geometry only; extraction/EM/IR/timing OPEN", "M1-M7 pin stacks + M7 risers recorded, not "
                     "censused against signal routing",
                     "shield ties = 1-cut VIA89 at each shield x orthogonal VSS stripe crossing (census of placement only)" if shield_full
                     else "VSS shield ties to the die grid not re-derived here"]
    enc = dict(shapes=rshapes + ties + tree, vias=g["vias"], stacks=stacks, attachments=g["attachments"],
               tie_segs=[list(s) for s in tie_segs], tree_wires=wires, pg_rects=[list(r) for r in pgr],
               phy_clip_ends=clip_ends(g, pgr)[:400] if phy_clip_on else [], shield_ties=ties_v)
    (dst / "encoded_metal.json").write_text(json.dumps(enc, separators=(",", ":")) + "\n")
    (dst / "ENCODE.json").write_text(json.dumps(rep, indent=1) + "\n")
    (dst / "findings.json").write_text(json.dumps(dict(census_rows=census["rows"], via=vbad[:limit], pg_gap_shared=shared[:limit],
                                                       rail_pg_close=close[:limit], gap_fit=gfit[:limit], tie_errors=errs[:limit], plan_errors=perr[:limit],
                                                       phy_band_mesh=phyb_mesh[:limit], phy_band_other=phyb_other[:limit], attachments_moved=moved[:limit],
                                                       shield_missing=shield_rows[:limit], shield_floating=floating[:limit]), indent=0) + "\n")
    print(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True); ap.add_argument("--build", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--gap-snap", action="store_true", help="move every rail to the centre of its ACTUAL 4.32-um PG gap")
    ap.add_argument("--phy-clip", action="store_true", help="R24: stop every rail >= 1.0 um before PHY PG bands, at a crossing")
    ap.add_argument("--vss-side", action="store_true", help="R24: rail at legal spacing to the VSS stripe; drawn VSS shield on VDD sides")
    ap.add_argument("--shield-full", action="store_true", help="R24b: 100%% shield: width cap, stepped VDD-side shield, both-side census, ties")
    a = ap.parse_args()
    encode(a.plan, a.build, a.out, gap_snap=a.gap_snap, phy_clip_on=a.phy_clip, vss_side=a.vss_side, shield_full=a.shield_full)
