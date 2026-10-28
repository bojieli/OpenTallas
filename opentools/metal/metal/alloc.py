"""Top-metal clock track ALLOCATOR (opentools.metal): place each clock wire of one routing layer on a legal position.

Duty split (lanes/OSS-TOOLS.md): clkplan COUNTS track demand vs supply; this module ALLOCATES actual positions
(clock rows, shields, PG interleave, pin-window / via access) on that count; mscts builds on the result.
Technology-free: every number comes from the shared plan (opentools.plan/1: pg[], pin_windows[], clock.ndr) or the
wire list.  Coordinates: the across-run axis ('y' for an H layer), um.

Model per layer:
  * PG stripes repeat every pitch_um (stripes{offset_um, width_um, net}); a clock wire lives in a PG GAP.
  * NDR per wire: width w, space s, shield none | drawn (two drawn shields of shield_width_um) | pg_flank (the
    neighbouring PG stripes are the shields: ONE wire per gap, centred, gap otherwise empty along the wire's span).
    Footprint F = w (+ 2 (s + ws) when drawn).  Two wires that overlap along the run need >= s between footprints;
    a footprint needs >= s to a PG stripe edge.
  * Pin windows: bands of +-half_um around each slot row (rows{pitch_um, offset_um, half_um}).  A wire may enter
    a window only if it belongs to that row (row = the row index of the cell whose pin it serves, 'own' trunk);
    every other wire (escape, foreign trunk, second trunk) must keep its footprint + s outside all windows
    (via access to the row's cell pins).
  * A wire also has y_pref (its ideal track) and max_jog_um (how far it may move; default one PG pitch).
Greedy allocation in the given order (own-row trunks first, then by span length, longest first); each wire takes the
legal position nearest y_pref on a grid of `grid_um`.  Unplaced wires are CONFLICTS with the blocking objects listed.
phase_scan(): off-window slots per row period as a function of the row phase vs the PG grid (plan-level fix finder).
"""
import math


def stripes_in(pg, lo, hi):
    """[(c, w, net)] PG stripe centres in [lo - pitch, hi + pitch]."""
    P = pg["pitch_um"]
    out = []
    for k in range(int(math.floor(lo / P)) - 1, int(math.ceil(hi / P)) + 2):
        for s in pg.get("stripes", []):
            out.append((k * P + s["offset_um"], s["width_um"], s.get("net", "PG")))
    return sorted(out)


def windows_in(wins, lo, hi):
    """[(a, b, row_index)] pin windows in [lo, hi]; row index = round((centre - offset) / pitch)."""
    out = []
    for w in wins:
        if "rows" in w:
            P, o, h = w["rows"]["pitch_um"], w["rows"]["offset_um"], w["rows"]["half_um"]
            for k in range(int(math.floor((lo - o) / P)) - 1, int(math.ceil((hi - o) / P)) + 2):
                out.append((k * P + o - h, k * P + o + h, k))
        else:
            for i, p in enumerate(w.get("positions_um", [])):
                out.append((p - w["half_um"], p + w["half_um"], i))
    return out


def footprint(ndr):
    w, s = ndr["width_um"], ndr["space_um"]
    if ndr.get("shield", "none") == "drawn":
        return w + 2 * (s + (ndr.get("shield_width_um") or w))
    return w


def _ovl(a0, a1, b0, b1):
    return a0 < b1 and b0 < a1


def allocate(layer, wires, grid_um=0.02, order="default"):
    """layer = dict(pg{pitch_um, stripes[]}, pin_windows[]); wires = [dict(name, ndr, y_pref, x0, x1, row|None,
    max_jog_um?)].  -> dict(placed{name: y}, conflicts[{name, y_pref, blockers[]}], stats)"""
    pg, wins = layer["pg"], layer.get("pin_windows", [])
    if order == "default":
        wires = sorted(wires, key=lambda w: (w.get("row") is None, -(w["x1"] - w["x0"])))
    placed, occ, conflicts = {}, [], []          # occ: (ylo, yhi, x0, x1, name, space, pg_flank)
    for w in wires:
        ndr = w["ndr"]
        F, s = footprint(ndr), ndr["space_um"]
        jog = w.get("max_jog_um", pg["pitch_um"])
        lo, hi = w["y_pref"] - jog, w["y_pref"] + jog
        st = stripes_in(pg, lo, hi)
        W = windows_in(wins, lo - 10, hi + 10)
        gaps = [(a[0] + a[1] / 2, b[0] - b[1] / 2) for a, b in zip(st, st[1:]) if b[0] - b[1] / 2 > a[0] + a[1] / 2]
        cands = []
        for g0, g1 in gaps:
            if ndr.get("shield") == "pg_flank":
                c = (g0 + g1) / 2
                if g1 - g0 >= w["ndr"]["width_um"] + 2 * s - 1e-9:
                    cands.append((c, g0, g1, True))
                continue
            y = g0 + s + F / 2
            while y <= g1 - s - F / 2 + 1e-9:
                cands.append((y, g0, g1, False))
                y += grid_um
        cands = [c for c in cands if abs(c[0] - w["y_pref"]) <= jog + 1e-9]
        cands.sort(key=lambda c: abs(c[0] - w["y_pref"]))
        why = {}
        ok = None
        for y, g0, g1, flank in cands:
            a, b = y - F / 2, y + F / 2
            bad = None
            for wa, wb, k in W:
                if _ovl(a - s, b + s, wa, wb) and k != w.get("row"):
                    bad = f"window row {k} [{wa:.2f},{wb:.2f}]"
                    break
            if bad is None:
                for (oa, ob, ox0, ox1, on, os_, ofl) in occ:
                    if not _ovl(w["x0"], w["x1"], ox0, ox1):
                        continue
                    sp = max(s, os_)
                    same_gap = _ovl(g0, g1, oa, ob)
                    if _ovl(a - sp, b + sp, oa, ob) or (same_gap and (flank or ofl)):
                        bad = f"wire {on} @{(oa + ob) / 2:.2f}"
                        break
            if bad is None:
                ok = y
                break
            why[bad] = why.get(bad, 0) + 1
        if ok is None:
            conflicts.append(dict(name=w["name"], y_pref=w["y_pref"], row=w.get("row"), candidates=len(cands),
                                  blockers=sorted(why, key=lambda k: -why[k])[:6]))
            continue
        placed[w["name"]] = round(ok, 4)
        occ.append((ok - F / 2, ok + F / 2, w["x0"], w["x1"], w["name"], s, ndr.get("shield") == "pg_flank"))
    return dict(placed=placed, conflicts=conflicts, stats=dict(wires=len(wires), placed=len(placed), conflicts=len(conflicts)))


def phase_scan(pg, ndr, rows, step_um=0.04):
    """off-window slots per row period vs row phase phi (row centre offset from the PG origin), one wire per gap
    slot model (pg_flank / one-per-gap).  rows = {pitch_um, half_um}.  -> [(phi, off_window_slots, in_window_slots)]"""
    Pr, h = rows["pitch_um"], rows["half_um"]
    s = ndr["space_um"]
    F = footprint(ndr)
    a, b = int(round(Pr * 1000)), int(round(pg["pitch_um"] * 1000))
    span = a * b // math.gcd(a, b) / 1000.0            # common period of rows and PG
    st = stripes_in(pg, 0, span)
    gaps = [((a[0] + a[1] / 2), (b[0] - b[1] / 2)) for a, b in zip(st, st[1:])]
    slots = [(g0 + g1) / 2 for g0, g1 in gaps if 0 <= (g0 + g1) / 2 < span and g1 - g0 >= ndr["width_um"] + 2 * s - 1e-9]
    out = []
    n = int(round(Pr / step_um))
    for i in range(n):
        phi = i * step_um
        W = windows_in([dict(rows=dict(pitch_um=Pr, offset_um=phi, half_um=h))], -Pr, span + Pr)
        off = sum(1 for c in slots if not any(_ovl(c - F / 2 - s, c + F / 2 + s, a, b) for a, b, _ in W))
        out.append((round(phi, 3), off * Pr / span, (len(slots) - off) * Pr / span))
    return out
