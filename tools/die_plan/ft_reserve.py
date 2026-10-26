"""Explicit FT track reservation shared by the partition kits and the die GRT model (DIE-PROTO-KV 2026-10-25,
COORD ruling (a) 21:16 + clarification: "routing guides or blockages on the declared FT tracks, matching the die model
exactly (same fraction, same tracks)").

Explicit-band plans dispatch to ft_bands.py: per-type background ft_track_frac
(default .25), replaced by max overlapping die_share inside declared layer/spans.
Kit and die consume identical type-frame rectangles, transformed at each instance;
M2/M3 are blocked in the FT pass. The legacy KV contract below is unchanged.

Legacy KV model.  The FT tracks are one lattice-periodic pattern in the DIE frame, identical inside every partition: on every
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
  hook : (PATH-KV-FTRES 10-26, COORD 23:53: FT nets of the kit DO route on the stripes) the kit data file that
         tools/die_plan/ft_grt.tcl reads in the kit GRT: slot names + FT stripes + complement stripes (kit frame);
         ft_grt.tcl routes the FT nets on the FT stripes only and the own nets off them (two GRT passes with
         disjoint M4-M7 resources, merged), M4-M7 layer adjustment 0.  Default for the KV hg / hgi / io kits
         (gen_phys.write_type_kit ft_reserve, FT_RESERVE_DEFAULT_RE).
  die  : over every partition outline the die may route ONLY on the FT stripes: obstruct the complement stripes and
         drop the global M4-M7 layer adjustment (die_obs_rects).  Outside partitions the die keeps every track.

usage:
    ft_reserve.py share  PLAN.json                      # per-layer fraction + track counts
    ft_reserve.py kit    PLAN.json TYPE --out FILE.tcl  # kit hook (type frame)
    ft_reserve.py die    PLAN.json --out FILE.tcl       # die-model complement obstructions (die frame)
    ft_reserve.py check  PLAN.json --types t1,t2        # dry run: every instance's kit FT stripes == die FT stripes
    ft_reserve.py hook   PLAN.json TYPE --out FILE.tcl  # ft_grt.tcl data (slots, FT + complement stripes)
    ft_reserve.py audit  PLAN.json TYPE FT.guide OWN.guide [--out J]   # post-GRT: FT guides on stripes, own off
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


def bands_mode(P):
    """An explicit-band plan uses one background+band track contract throughout; KV without bands is unchanged."""
    return any(t.get("die_ft_bands") for t in P.types.values())


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
    if bands_mode(P):
        import ft_bands
        return ft_bands.type_rects(P, tn)
    w, h = P.types[tn]["outline_um"]
    out = []
    for L in RESERVE_LAYERS:
        out += _rects(P, L, 0.0, 0.0, w, h, True)
    return out


def die_obs_rects(P):
    """die-model obstructions: the non-FT stripes of M4-M7 over every partition outline (die frame)."""
    out = []
    for n, p in sorted(P.parts.items()):
        if bands_mode(P):
            import ft_bands
            out.extend(ft_bands.to_die(P, n, r) for r in ft_bands.type_rects(P, p["type"], False))
            continue
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
        if bands_mode(P):
            import ft_bands
            inst = [n for n,p in P.parts.items() if p["type"] == tn]
            for n in inst:
                for r in kit: ft_bands.to_die(P,n,r)
            w,h = P.types[tn]["outline_um"]
            areas = {L: sum((r[3]-r[1])*(r[4]-r[2]) for r in kit if r[0]==L) for L in RESERVE_LAYERS}
            rep[tn] = dict(instances=len(inst), layers={L:dict(ft_area_um2=a,share=a/(w*h)) for L,a in areas.items()},
                           mismatched_instances=[], PASS=True, basis="one type-frame rectangle set transformed for both kit and die")
            continue
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
    sh = type_share(P, tn)
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


def type_rects_nonft(P, tn):
    """complement (non-FT) stripes of M4-M7 in the TYPE frame."""
    if bands_mode(P):
        import ft_bands
        w,h = P.types[tn]["outline_um"]
        return ft_bands.type_rects(P, tn, False) + [(L,0,0,w,h) for L in ("M2","M3") if L in P.layers]
    w, h = P.types[tn]["outline_um"]
    out = []
    for L in RESERVE_LAYERS:
        out += _rects(P, L, 0.0, 0.0, w, h, False)
    return out


def type_share(P, tn):
    if not bands_mode(P):
        return share(P)
    w,h = P.types[tn]["outline_um"]
    rs = type_rects(P,tn)
    return {L: dict(dir=P.layers[L]["dir"], share=round(sum((r[3]-r[1])*(r[4]-r[2])
                 for r in rs if r[0]==L)/(w*h),6)) for L in RESERVE_LAYERS}


def hook_tcl(P, tn):
    slots = [s["name"] for s in P.types[tn].get("ft_slots", [])]
    def lst(rs):
        return " ".join("{%s %.4f %.4f %.4f %.4f}" % r for r in rs)
    sh = type_share(P, tn)
    return "\n".join([
        f"# GENERATED by tools/die_plan/ft_reserve.py hook: FT track reservation data of type {tn} (die plan {P.name}).",
        "# Read by ft_grt.tcl (kit GRT): FT nets (slots below) route on ot_ftres_ft only, own logic off it.",
        "# share " + " ".join(f"{L}={v['share']}" for L, v in sh.items()),
        "set ot_ftres_slots {" + " ".join(slots) + "}",
        "set ot_ftres_ft {" + lst(type_rects(P, tn)) + "}",
        "set ot_ftres_nonft {" + lst(type_rects_nonft(P, tn)) + "}", ""])


def install_kit(P, tn, kit_dir, enabled=None):
    """Install the pinned two-pass GRT hook; return budget metadata or None.

    Generator integration: call after grt_pre.tcl/grt_post.tcl exist, then
    attach the return value to budget['ft_reserve']. Explicit-band plans
    require every type's background contract; KV's legacy type defaults stay.
    """
    import re
    import shutil
    if enabled is False:
        if bands_mode(P):
            raise ValueError("explicit die_ft_bands require kit FT reservation")
        return None
    if enabled is None and not (bands_mode(P) or re.match(r"^kv3_(hg|hgi|io)(_|$)", tn)):
        return None
    kd = Path(kit_dir)
    (kd / "ft_reserve.tcl").write_text(hook_tcl(P, tn))
    shutil.copyfile(Path(__file__).with_name("ft_grt.tcl"), kd / "ft_grt.tcl")
    with open(kd / "grt_pre.tcl", "a") as fh:
        fh.write("\n# Explicit FT track contract: planning route adjustments, two-pass repaired route in post.\n"
                 "set ::ot_ftres_stage pre\nsource [file join $gp_dir ft_grt.tcl]\n")
    post = kd / "grt_post.tcl"
    post.write_text("# Explicit FT reservation of repaired nets, merged before timing measurement.\n"
        "set ::ot_ftres_stage post\nsource [file join [file dirname [file normalize [info script]]] ft_grt.tcl]\n"
        + post.read_text())
    return dict(tool="tools/die_plan/ft_reserve.py + ft_grt.tcl",
        geometry="type background+explicit bands" if bands_mode(P) else "legacy KV middle-half lattice",
        layers=list(RESERVE_LAYERS), share={L:v['share'] for L,v in type_share(P,tn).items()},
        slots=[s['name'] for s in P.types[tn].get('ft_slots',[])], m4_m7_layer_adjustment=0,
        rule="same FT rectangles in kit two-pass GRT and die complement; core/PG/clock OBS additive")


def read_guides(path):
    """{net: [(layer, x0, y0, x1, y1) um]} from an OpenROAD guide file (DBU 1000 per um for asap7 is NOT assumed:
    coordinates are converted with dbu)."""
    out, cur, inb = {}, None, False
    for ln in open(path):
        t = ln.split()
        if not t:
            continue
        if t[0] == "(":
            inb = True
            continue
        if t[0] == ")":
            inb, cur = False, None
            continue
        if not inb:
            cur = t[0]
            out.setdefault(cur, [])
        elif len(t) >= 5:
            out[cur].append((t[4], *map(int, t[:4])))
    return out


def _frac_in(P, L, a0, a1):
    """fraction of [a0, a1] (um, cross-track direction) covered by the FT bands of layer L."""
    G = P.grid
    _, fts = cell_tracks(P, L)
    p = P.layers[L]["pitch_um"]
    lo, hi = fts[0] - p / 2, fts[-1] + p / 2
    if a1 <= a0:
        return 0.0
    cov = 0.0
    for k in range(int(math.floor(a0 / G)), int(math.ceil(a1 / G)) + 1):
        cov += max(0.0, min(a1, k * G + hi) - max(a0, k * G + lo))
    return cov / (a1 - a0)


def audit(P, tn, ft_guide, own_guide, dbu=1000):
    """post-GRT conformance on the guides of the two passes (gcell boxes).  A WIRE box (extent along the layer's
    routing direction > 2 gcells) of an FT net must lie mostly on the FT bands, a wire box of an own net mostly off
    them.  GRT works in gcells whose edges need not fall on band edges, so a gcell straddling a band edge offers
    tracks of both classes: a wire box is a violation only when it holds NO track of its class (FT box entirely off
    the bands, own box entirely on them).  Short boxes (<= 2 gcells: via stacks / pin access, GRT does not charge vias against
    obstructions) are counted separately as INFO."""
    rep = {}
    ftg = read_guides(ft_guide)
    gc = min((min(b[3] - b[1], b[4] - b[2]) for bs in ftg.values() for b in bs if b[3] > b[1] and b[4] > b[2]), default=0)
    for cls, path, want_ft in (("ft", ft_guide, True), ("own", own_guide, False)):
        g = ftg if want_ft else {n: b for n, b in read_guides(path).items() if n not in ftg}
        per = {L: dict(wire_boxes=0, wire_bad=0, short_boxes=0, short_wrong=0, wire_um=0.0, wire_bad_um=0.0)
               for L in (("M2", "M3") + RESERVE_LAYERS if bands_mode(P) else RESERVE_LAYERS)}
        bad_nets = set()
        for net, boxes in g.items():
            for L, x0, y0, x1, y1 in boxes:
                if L not in per:
                    continue
                horiz = P.layers[L]["dir"] == "H"
                a0, a1 = ((y0, y1) if horiz else (x0, x1))
                ln = (x1 - x0) if horiz else (y1 - y0)
                if bands_mode(P):
                    import ft_bands
                    f = ft_bands.coverage((x0/dbu,y0/dbu,x1/dbu,y1/dbu),
                        [r[1:] for r in type_rects(P, tn) if r[0] == L])
                else:
                    f = _frac_in(P, L, a0 / dbu, a1 / dbu)
                wrong = (f < 1e-6) if want_ft else (f > 1 - 1e-6)
                if ln > 2 * gc:
                    per[L]["wire_boxes"] += 1
                    per[L]["wire_um"] += ln / dbu
                    if wrong:
                        per[L]["wire_bad"] += 1
                        per[L]["wire_bad_um"] += ln / dbu
                        bad_nets.add(net)
                else:
                    per[L]["short_boxes"] += 1
                    per[L]["short_wrong"] += int(wrong)
        for v in per.values():
            v["wire_um"], v["wire_bad_um"] = round(v["wire_um"], 1), round(v["wire_bad_um"], 1)
        rep[cls] = dict(nets=len(g), layers=per, bad_nets=len(bad_nets), bad_net_sample=sorted(bad_nets)[:10])
    rep["gcell_um"] = gc / dbu
    rep["PASS"] = rep["ft"]["bad_nets"] == 0 and rep["own"]["bad_nets"] == 0
    return rep


def die_tcl(P):
    rs = die_obs_rects(P)
    return "\n".join(f"create_obstruction -region {{{a:.4f} {b:.4f} {c:.4f} {d:.4f}}} -layer {L}"
                     for L, a, b, c, d in rs) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("share", "kit", "die", "check", "hook", "audit"):
        s = sp.add_parser(c)
        s.add_argument("plan")
        if c in ("kit", "hook", "audit"):
            s.add_argument("type")
        if c == "audit":
            s.add_argument("ft_guide")
            s.add_argument("own_guide")
            s.add_argument("--dbu", type=int, default=1000)
            s.add_argument("--out")
        if c in ("kit", "die", "hook"):
            s.add_argument("--out", required=True)
        if c == "check":
            s.add_argument("--types", required=True)
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan), Path(a.plan))
    if a.cmd == "share":
        print(json.dumps(share(P), indent=1))
    elif a.cmd == "kit":
        Path(a.out).write_text(kit_tcl(P, a.type))
    elif a.cmd == "hook":
        Path(a.out).write_text(hook_tcl(P, a.type))
    elif a.cmd == "audit":
        r = audit(P, a.type, a.ft_guide, a.own_guide, a.dbu)
        txt = json.dumps(r, indent=1)
        if a.out:
            Path(a.out).write_text(txt + "\n")
        print(txt)
        return 0 if r["PASS"] else 1
    elif a.cmd == "die":
        Path(a.out).write_text(die_tcl(P))
        print("die obstructions", len(die_obs_rects(P)))
    else:
        r = check(P, a.types.split(","))
        print(json.dumps(r, indent=1))
        return 0 if all(v["PASS"] for v in r.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
