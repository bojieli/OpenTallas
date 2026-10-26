"""Explicit FT track reservation shared by the partition kits and the die GRT model (DIE-PROTO-KV 2026-10-25,
COORD ruling (a) 21:16 + clarification: "routing guides or blockages on the declared FT tracks, matching the die model
exactly (same fraction, same tracks)").

Model.  The FT tracks are one lattice-periodic pattern in the DIE frame, identical inside every partition: on every
partition signal layer L in RESERVE_LAYERS, inside each die lattice cell [k*G, (k+1)*G) (G = die grid_um = 8.64 um,
lcm of every pitch, every partition origin and outline is on it) the tracks whose centre lies in the cell's middle
half [G/4, 3G/4) (y for an H layer, x for a V layer) are FT tracks.  The band is centred, so the pattern is invariant
under every partition orient (R0/MX/MY/R180: a mirror maps a cell onto a cell and its middle half onto itself) and
under any lattice translation: a replicated type sees the SAME tracks in every instance, and the kit frame and the die
frame name the same physical tracks.  Fraction per layer (symmetric tracks, offset = pitch / 2):
    M4 / M5 (pitch 0.048): 90 of 180 tracks = 0.5000      M6 / M7 (pitch 0.064): 67 of 135 = 0.4963
(135 is odd: 0.5 exactly is not mirror-symmetric on M6/M7; 67/135 is the closest symmetric share).
M2 / M3: the die model blocks them over every partition (abstract OBS M1-M3, die nets never route there), so the
reservation there is 0 in both models; M8 / M9 are die clock / reset / PG (ruling 9.3).

  kit  : obstruct the FT stripes for the partition's OWN logic (ft_reserve.tcl, odb obstructions, M4-M7).
  die  : over every partition outline the die may route ONLY on the FT stripes: obstruct the complement stripes and
         drop the global M4-M7 layer adjustment (die_obs_rects).  Outside partitions the die keeps every track.

usage:
    ft_reserve.py share  PLAN.json                      # per-layer fraction + track counts
    ft_reserve.py kit    PLAN.json TYPE --out FILE.tcl  # kit hook (type frame)
    ft_reserve.py die    PLAN.json --out FILE.tcl       # die-model complement obstructions (die frame)
    ft_reserve.py check  PLAN.json --types t1,t2        # dry run: every instance's kit FT stripes == die FT stripes
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402

RESERVE_LAYERS = ("M4", "M5", "M6", "M7")
BAND = (0.25, 0.75)        # middle half of each lattice cell


def _eq(a, b):
    return abs(a - b) < 1e-6


def cell_tracks(P, L):
    """(track centres in [0, G), FT track centres) of layer L inside one lattice cell."""
    G = P.grid
    lay = P.layers[L]
    p, o = lay["pitch_um"], lay["offset_um"]
    n = int(round(G / p))
    if not _eq(n * p, G):
        raise ValueError(f"{L}: pitch {p} does not divide the lattice {G}")
    tr = [round(o + k * p, 6) for k in range(n)]
    lo, hi = BAND[0] * G, BAND[1] * G
    return tr, [t for t in tr if lo - 1e-6 <= t < hi - 1e-6]


def share(P):
    out = {}
    for L in RESERVE_LAYERS:
        tr, ft = cell_tracks(P, L)
        out[L] = dict(dir=P.layers[L]["dir"], tracks_per_cell=len(tr), ft_tracks_per_cell=len(ft),
                      share=round(len(ft) / len(tr), 4), band_um=[BAND[0] * P.grid, BAND[1] * P.grid])
    return out


def _stripes(P, L, a0, a1, ft=True):
    """[(lo, hi)] coordinate intervals in [a0, a1] (lattice-aligned, absolute die coordinates) covering exactly the FT
    tracks (ft=True) or the non-FT tracks (ft=False) of layer L, each edge half way between two tracks."""
    G = P.grid
    tr, fts = cell_tracks(P, L)
    p = P.layers[L]["pitch_um"]
    lo_t, hi_t = fts[0] - p / 2, fts[-1] + p / 2           # FT band edges inside a cell (between tracks)
    out = []
    k0, k1 = int(round(a0 / G)), int(round(a1 / G))
    if not (_eq(k0 * G, a0) and _eq(k1 * G, a1)):
        raise ValueError(f"span {a0}..{a1} not on the {G}-um lattice")
    for k in range(k0, k1):
        c = k * G
        if ft:
            out.append((round(c + lo_t, 4), round(c + hi_t, 4)))
        else:
            out.append((round(c, 4), round(c + lo_t, 4)))
            out.append((round(c + hi_t, 4), round(c + G, 4)))
    # merge touching non-FT stripes across cell edges
    m = []
    for a, b in out:
        if m and _eq(m[-1][1], a):
            m[-1] = (m[-1][0], b)
        else:
            m.append((a, b))
    return m


def _rects(P, L, x0, y0, x1, y1, ft):
    if P.layers[L]["dir"] == "H":
        return [(L, x0, a, x1, b) for a, b in _stripes(P, L, y0, y1, ft)]
    return [(L, a, y0, b, y1) for a, b in _stripes(P, L, x0, x1, ft)]


def type_rects(P, tn):
    """kit FT stripes in the TYPE frame (origin 0, lattice-aligned outline)."""
    w, h = P.types[tn]["outline_um"]
    out = []
    for L in RESERVE_LAYERS:
        out += _rects(P, L, 0.0, 0.0, w, h, True)
    return out


def die_obs_rects(P):
    """die-model obstructions: the non-FT stripes of M4-M7 over every partition outline (die frame)."""
    out = []
    for n, p in sorted(P.parts.items()):
        w, h = P.types[p["type"]]["outline_um"]
        ox, oy = p["origin_um"]
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        for L in RESERVE_LAYERS:
            out += _rects(P, L, ox, oy, ox + w, oy + h, False)
    return out


def _to_die(P, part, r):
    p = P.parts[part]
    w, h = P.types[p["type"]]["outline_um"]
    ox, oy = p["origin_um"]
    o = p.get("orient", "R0")
    L, x0, y0, x1, y1 = r
    if o in ("MY", "R180"):
        x0, x1 = w - x1, w - x0
    if o in ("MX", "R180"):
        y0, y1 = h - y1, h - y0
    return (L, round(ox + x0, 4), round(oy + y0, 4), round(ox + x1, 4), round(oy + y1, 4))


def check(P, types):
    """dry run: (a) every instance of each type: its kit FT stripes mapped to the die frame == the die model's FT
    stripes over that instance (the complement of die_obs_rects inside the outline), track for track;
    (b) the FT track set of each layer is the same list in the kit and the die frame."""
    rep = {}
    for tn in types:
        kit = type_rects(P, tn)
        inst = [n for n, p in P.parts.items() if p["type"] == tn]
        bad = []
        for n in inst:
            p = P.parts[n]
            w, h = P.types[tn]["outline_um"]
            ox, oy = p["origin_um"]
            die_ft = sorted(r for L in RESERVE_LAYERS for r in _rects(P, L, ox, oy, ox + w, oy + h, True))
            mapped = sorted(_to_die(P, n, r) for r in kit)
            if len(die_ft) != len(mapped) or any(a[0] != b[0] or any(not _eq(u, v) for u, v in zip(a[1:], b[1:]))
                                                 for a, b in zip(die_ft, mapped)):
                bad.append(n)
        per = {}
        for L in RESERVE_LAYERS:
            tr, ft = cell_tracks(P, L)
            rs = [r for r in kit if r[0] == L]
            p_ = P.layers[L]["pitch_um"]
            o_ = P.layers[L]["offset_um"]
            span = P.types[tn]["outline_um"][1 if P.layers[L]["dir"] == "H" else 0]
            ntr = int(round(span / p_))
            iv = [((r[2], r[4]) if P.layers[L]["dir"] == "H" else (r[1], r[3])) for r in rs]
            nft = sum(1 for k in range(ntr) if any(a < o_ + k * p_ < b for a, b in iv))
            per[L] = dict(type_tracks=ntr, ft_tracks=nft, share=round(nft / ntr, 4), stripes=len(rs))
        rep[tn] = dict(instances=len(inst), orients=sorted({P.parts[n].get("orient", "R0") for n in inst}),
                       mismatched_instances=bad, layers=per, PASS=not bad)
    return rep


def kit_tcl(P, tn):
    rs = type_rects(P, tn)
    sh = share(P)
    t = [f"# GENERATED by tools/die_plan/ft_reserve.py: FT track reservation of type {tn} (die plan {P.name}).",
         "# Lattice FT stripes (middle half of every die lattice cell) obstructed for the partition's own logic;",
         "# the die GRT model (ft_reserve.die_obs_rects) routes die FT only on these same tracks.",
         "# share " + " ".join(f"{L}={v['share']}" for L, v in sh.items()),
         "set blk [ord::get_db_block]", "set dbu [$blk getDbUnitsPerMicron]", "set tech [ord::get_db_tech]"]
    cur = None
    for L, a, b, c, d in rs:
        if L != cur:
            t.append(f"set lay [$tech findLayer {L}]")
            cur = L
        t.append("odb::dbObstruction_create $blk $lay " + " ".join(f"[expr {{round({v:.4f}*$dbu)}}]" for v in (a, b, c, d)))
    t.append(f"puts \"OT_FT_RESERVE {tn} stripes {len(rs)}\"")
    return "\n".join(t) + "\n"


def die_tcl(P):
    rs = die_obs_rects(P)
    return "\n".join(f"create_obstruction -region {{{a:.4f} {b:.4f} {c:.4f} {d:.4f}}} -layer {L}"
                     for L, a, b, c, d in rs) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("share", "kit", "die", "check"):
        s = sp.add_parser(c)
        s.add_argument("plan")
        if c == "kit":
            s.add_argument("type")
        if c in ("kit", "die"):
            s.add_argument("--out", required=True)
        if c == "check":
            s.add_argument("--types", required=True)
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan), Path(a.plan))
    if a.cmd == "share":
        print(json.dumps(share(P), indent=1))
    elif a.cmd == "kit":
        Path(a.out).write_text(kit_tcl(P, a.type))
    elif a.cmd == "die":
        Path(a.out).write_text(die_tcl(P))
        print("die obstructions", len(die_obs_rects(P)))
    else:
        r = check(P, a.types.split(","))
        print(json.dumps(r, indent=1))
        return 0 if all(v["PASS"] for v in r.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
