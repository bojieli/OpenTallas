#!/usr/bin/env python3
"""DIE-S81-85 11-09 LEAF-CLKENTRY-1109: macro-field regional clock entries + a wider vs/vq channel for the S81 leaf
types with the t21 geometry (left macro column, an 8.64-um vs/vq channel at x~300, the die-spine tap 0 'clk' at the SW
grid cell).  One plan event, applied to every matching leaf type.

COORD geom-1733-1109 on ot_s81sl_leaf__t21 attempt_20 (kw43 e9eda32d41c, 3_place.odb): clock root bottom-left
(180, 150) with the farthest sink 2004 um away; heavy clusters on the W pin edge (taps t29/t33/t35/t31, ~1100 sinks
each) and at tap t10 (2523 sinks, macro edge); col_V 6.47 at (240, 600) in the channel between the left macro column
and the macro at x~300.

What the attempt measures (CTS probe on a copy of attempt_20 3_place.odb: pre_cts nearest-tap split + TritonCTS with
the ORFS arguments + dpl + cts_post tap_balance, placement RC, TT):
  * 'clk' at (180, 152) is tap 0 of the 16-tap R4 grid, not the clock root of the type: every one of the 36 tap ports
    (16 grid + 20 added) is a die-spine drop.  The 2004 um is the pre-split auto-geom leg (all 20,678 sinks still on
    'clk' before PRE_CTS); after the split the farthest sink is 328 um from its own tap.
  * the W-edge clusters are the ft2/ft3 station banks (1104 bits each), each already on its own added tap: t29 / t31 /
    t33 / t35 trees 87-101 ps raw, spread <= 13 ps.  No change.
  * the deep trees are the macro field: t9 (1595 sinks) mean 327 / max 409 ps, t10 (2485) 267 / 355, t22 (599)
    285 / 403, every other tap 250 +- 25 after tap_balance (which only pads).  The late sinks sit in two narrow channels
    of the vn / vp field: the vn_a / vn_b strip (17.28 um, ~1250 sinks, 330-390 ps) and the band under vn_a around the
    vp SRAM pair (b0 / vn_a gap 22.68 um and the open area left of b0, ~1100 sinks, 307-366 ps), 100-200 um from the
    t9 / t10 pins with vn_a (356 um) between.
So the "clock entry at the left-cluster centroid" is not needed.  The congestion half is real but not where geom put it:
the geom col_V 6.47 at (240, 600) is the estimator projecting the 873 vs <-> ve_m macro-macro nets through vs (GRT
guides route 0 nets in that window); the routed hot spot is the 8.64-um vs / vq channel itself (GRT 10 iterations:
total overflow 8039, M5 1528 / M6 6129 / M7 382; channel vertical demand mean 0.48 / max 0.99 of capacity, M5 1.80).

Probe results (CTS + 10-iteration GRT on the attempt_20 copy; insertion = flops on the 36 die-spine taps, TT, placement RC):
                       insertion mean / max / spread    GRT overflow (M5/M6/M7)   vs/vq channel vert demand mean / max
  base                 259.9 / 408.5 / 225.1 ps          8039 (1528/6129/382)      0.48 / 0.99
  FIELD only           258.2 / 385.9 / 231.5             7930 (1547/5983/390)      0.48 / 0.98
  CHANNEL + FIELD      253.7 / 385.1 / 231.8             0                         0.17 / 0.79
  CHANNEL is the fix: overflow 8039 -> 0.  FIELD cuts the deep-tap max by 23 ps and the field spread from 177 to 31-37
  ps, but the entry sinks stay at 345-386 ps: the region tree under one BUFx24 costs ~145 ps for ~1100 sinks on top of
  the ~145-200 ps tap-port tree in front of the trunk.  It also leaves clk_t10 under its 250-ps target (166 ps mean:
  tap_balance only pads up to the tap max, still 263).  Sourcing rgn1 at clk_t22 instead was worse (438 / 455 ps).
  So the default event is CHANNEL only; FIELD (--field) stays an opt-in, validated plan form for a later re-try.

Form (per matching type):
  FIELD   (--field only) two core-clock REGIONAL entries (plan clock.tap_entries, pad_clock.tap_entries + pad_clock_entry.tcl, the
          RCK2 trunk form sourced at a die-spine tap port): clk_rgn0 takes the std-cell sinks in the vn_a / vn_b strip,
          clk_rgn1 the band under vn_a down to the bottom of the vp SRAM pair (x vn_a.x0 .. SRAM x1).  Driver = one
          BUFx24 at the strip centre / at the centre of the vn_a-to-SRAM gap; source tap = the nearest grid / added tap
          (L1), trunk hops <= 400 um; take_taps = every tap whose nearest-tap cell meets the region.  No new port: a new
          added tap would renumber the published landing collector_tree (frozen reset contract, added_tap_recentre
          DIE-S81-49), change the type RTL and the die top.  Applied where the vn / vp field has the t21 order (vn_b
          directly over vn_a, the SRAM pair stacked under it); else reported.
  CHANNEL the macro right of the narrow channel (vq) moves right so the vs / vq gap is CHANNEL_UM (25.92 = 3 x the
          8.64 macro lattice, the width t31 / t71 already have); outline unchanged; vq keeps >= 8.64 um to every other
          hard core and every tap / station site; vq's early core tap moves with it.  Applied to every matching type.
Match: vs, vsw, ve_m origins x < 200 um (left column), vq right of vs with y-overlap and gap <= 8.64 um, vq.x0 in
[250, 350] um, tap 0 'clk' in the SW quarter.  Every other key and type is asserted unchanged; a second run is refused.

usage: delta_leaf_clkentry_1109.py PLAN_IN PLAN_OUT [REPORT.json] [--probe PROBE.json] [--field]   (cwd = repo root)"""
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[3] / "tools" / "die_plan")]
from delta_romq_split_1106 import spans  # noqa: E402

EVENT = "LEAF-CLKENTRY-1109"
LEAF = re.compile(r"^ot_s81sl_leaf__t\d+")
CELL = "BUFx24_ASAP7_75t_R"          # the kit CTS root / sink buffer (RCK2 trunk cell)
HOP_UM = 400.0                       # < pad_clock.ENTRY_HOP_UM 405 (12.1e)
CLEAR = 8.64                         # schema.TAP_CLEAR_UM, the macro lattice / minimum macro channel
CHANNEL_UM = 25.92                   # target vs / vq gap
LEFT_X_UM = 200.0                    # left macro column: vs, vsw, ve_m origin x below this
VQ_X_UM = (250.0, 350.0)             # the "x~300" channel: vq left edge window
FIELD_GAP_UM = (2 * CLEAR, 30.0)     # vn_a / vn_b strip and vn_a / SRAM gap: a legal driver row fits, still a channel
SAMPLE_UM = 8.64                     # region sampling for take_taps (nearest-tap cells meeting the region)
NAMES = ("clk_rgn0", "clk_rgn1")
I = dict(vs="u_lf.u_vs", vq="u_lf.u_vq", vsw="u_lf.u_vsw", vem="u_lf.u_ve.u_m", vna="u_lf.u_vn.u_a",
         vnb="u_lf.u_vn.u_b", b0="u_lf.u_vp.u_b0", b1="u_lf.u_vp.u_b1")
EVIDENCE = ("ot_s81sl_leaf__t21 attempt_20 (kw43 e9eda32d41c) 3_place.odb CTS probe (pre_cts split + TritonCTS ORFS args + "
            "tap_balance, placement RC, TT): t9 1595 sinks mean 327 / max 409 ps, t10 2485 sinks 267 / 355, t22 599 "
            "285 / 403; late sinks in the vn_a/vn_b strip (~1250, 330-390 ps) and the band under vn_a around the vp "
            "SRAM pair (~1100, 307-366 ps); COORD geom-1733-1109")


def box(c):
    (x, y), (w, h) = c["origin_um"], c["outline_um"]
    return [x, y, x + w, y + h]


def cores(t):
    return {c["inst"]: box(c) for c in t.get("hard_cores", [])}


def yover(a, b):
    return min(a[3], b[3]) - max(a[1], b[1])


def xover(a, b):
    return min(a[2], b[2]) - max(a[0], b[0])


def sep(a, b):
    """L-inf clearance between two boxes (negative = overlap)"""
    return max(b[0] - a[2], a[0] - b[2], b[1] - a[3], a[1] - b[3])


def r3(v):
    return round(float(v), 3)


def classify(P, tn, t):
    import schema as S
    B = cores(t)
    W, H = t["outline_um"]
    row = dict(type=tn)
    if any(I[k] not in B for k in ("vs", "vq", "vsw", "vem")):
        row["why"] = "no vs/vq/vsw/ve_m hard cores"
        return row
    vs, vq = B[I["vs"]], B[I["vq"]]
    row["left_column"] = all(B[I[k]][0] < LEFT_X_UM for k in ("vs", "vsw", "vem"))
    gap = vq[0] - vs[2] if yover(vs, vq) > 0 and vq[0] > vs[2] else None
    row["vs_vq_gap_um"] = None if gap is None else r3(gap)
    row["vq_x0_um"] = r3(vq[0])
    g = S._grid_taps(P, tn)
    row["tap0"] = [g[0][0], r3(g[0][1]), r3(g[0][2])]
    row["sw_root"] = g[0][0] == "clk" and g[0][1] < W / 4 and g[0][2] < H / 4
    row["channel"] = bool(row["left_column"] and gap is not None and gap <= CLEAR + 1e-6
                          and VQ_X_UM[0] <= vq[0] <= VQ_X_UM[1] and row["sw_root"])
    row["field"] = field_geometry(B) if row["channel"] else None
    if not row["channel"]:
        row["why"] = ("not the left-column family" if not row["left_column"] else
                      f"vs/vq gap {row['vs_vq_gap_um']} um, vq.x0 {row['vq_x0_um']} (needs <= {CLEAR} and x~300)")
    return row


def field_geometry(B):
    """the t21 vn / vp order: vn_b directly over vn_a (strip gap in FIELD_GAP_UM), one vp SRAM directly under vn_a
    (same gap rule) and the other SRAM under that one; returns the two regions + driver points, or None"""
    if any(I[k] not in B for k in ("vna", "vnb", "b0", "b1")):
        return None
    na, nb = B[I["vna"]], B[I["vnb"]]
    s_gap = nb[1] - na[3]
    if not (FIELD_GAP_UM[0] - 1e-6 <= s_gap <= FIELD_GAP_UM[1] and xover(na, nb) > 0.5 * (na[2] - na[0])):
        return None
    srams = sorted((B[I["b0"]], B[I["b1"]]), key=lambda b: -b[3])          # upper first
    up, lo = srams
    b_gap = na[1] - up[3]
    if not (FIELD_GAP_UM[0] - 1e-6 <= b_gap <= FIELD_GAP_UM[1] and xover(na, up) > 0 and xover(up, lo) > 0
            and up[1] - lo[3] >= 0):
        return None
    strip = [max(na[0], nb[0]), na[3], min(na[2], nb[2]), nb[1]]
    band = [na[0], lo[1], min(na[2], max(up[2], lo[2])), na[1]]
    return dict(strip=[r3(v) for v in strip], strip_xy=[r3((strip[0] + strip[2]) / 2), r3((strip[1] + strip[3]) / 2)],
                band=[r3(v) for v in band], band_xy=[r3((band[0] + band[2]) / 2), r3((na[1] + up[3]) / 2)],
                strip_gap_um=r3(s_gap), band_gap_um=r3(b_gap))


def l_points(a, corner, b, n):
    """n points evenly spaced along the L path a -> corner -> b (the last is b)."""
    legs = [(a, corner), (corner, b)]
    lens = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in legs]
    total = sum(lens)
    out = []
    for k in range(1, n + 1):
        s = total * k / n
        for (p, q), ln in zip(legs, lens):
            if s <= ln + 1e-9 and ln > 0:
                f = s / ln
                out.append([r3(p[0] + (q[0] - p[0]) * f), r3(p[1] + (q[1] - p[1]) * f)])
                break
            s -= ln
    return out


def entries_for(P, tn, fg):
    import gen_phys as GP
    taps = [(n, float(x), float(y)) for n, x, y in GP.clock_pins(P, tn)]
    l1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    out = []
    for name, reg, xy in ((NAMES[0], fg["strip"], fg["strip_xy"]), (NAMES[1], fg["band"], fg["band_xy"])):
        src = min(taps, key=lambda q: l1(q[1:], xy))
        L = l1(src[1:], xy)
        n = max(1, math.ceil(L / HOP_UM))
        pts = l_points(list(src[1:]), [src[1], xy[1]], xy, n)
        take = set()
        nx, ny = max(1, int((reg[2] - reg[0]) // SAMPLE_UM)), max(1, int((reg[3] - reg[1]) // SAMPLE_UM))
        for i in range(nx + 1):
            for j in range(ny + 1):
                p = (reg[0] + (reg[2] - reg[0]) * i / nx, reg[1] + (reg[3] - reg[1]) * j / ny)
                take.add(min(taps, key=lambda q: l1(q[1:], p))[0])
        take.add(src[0])
        order = {q[0]: k for k, q in enumerate(taps)}
        out.append(dict(name=name, tap=src[0], take_taps=sorted(take, key=order.get), xy_um=pts[-1],
                        stations_um=pts[:-1], cell=CELL, region_um=[reg],
                        evidence=f"{EVENT} (DIE-S81-85, COORD geom-1733-1109): macro-field regional entry, "
                                 f"trunk {L:.1f} um from {src[0]}. Basis: {EVIDENCE}"))
    return out


def widen(P, tn, t):
    """move vq right so the vs / vq gap is CHANNEL_UM; returns (dx, report) or raises on any clearance loss"""
    import gen_phys as GP
    B = cores(t)
    vs, vq = B[I["vs"]], B[I["vq"]]
    dx = r3(CHANNEL_UM - (vq[0] - vs[2]))
    nq = [vq[0] + dx, vq[1], vq[2] + dx, vq[3]]
    W, H = t["outline_um"]
    if nq[2] > W - CLEAR:
        raise SystemExit(f"{tn}: moved vq {nq} leaves the outline margin")
    near = []
    for inst, b in B.items():
        if inst == I["vq"]:
            continue
        s = sep(nq, b)
        if s < CLEAR - 1e-6:
            raise SystemExit(f"{tn}: moved vq {nq} within {CLEAR} um of {inst} {b}")
        near.append((r3(s), inst))
    halo = [nq[0] - CLEAR, nq[1] - CLEAR, nq[2] + CLEAR, nq[3] + CLEAR]
    inside = lambda x, y, bb: bb[0] + 1e-6 < x < bb[2] - 1e-6 and bb[1] + 1e-6 < y < bb[3] - 1e-6
    own = [k for k, c in enumerate(t["clock"].get("taps", [])) if c.get("name", "").startswith(I["vq"] + ".")]
    pts = [(n, x, y) for n, x, y in GP.clock_pins(P, tn)]
    pts += [(c["name"], *c["xy"]) for k, c in enumerate(t["clock"].get("taps", [])) if k not in own and c.get("xy")]
    for n, x, y in pts:
        if inside(x, y, halo):
            raise SystemExit(f"{tn}: tap {n} ({x}, {y}) inside the moved vq halo {halo}")
    for s in t.get("ft_slots", []):
        for bits in s.get("bit_sites_um", []):
            for x, y in bits:
                if inside(x, y, nq):
                    raise SystemExit(f"{tn}: ft slot {s['name']} bit site ({x}, {y}) under the moved vq {nq}")
    for st in t.get("internal_stations", []):
        for x, y in st.get("regs_um", []):
            if inside(x, y, nq):
                raise SystemExit(f"{tn}: internal station register ({x}, {y}) under the moved vq {nq}")
    right = min((b[0] - vq[2], inst) for inst, b in B.items() if yover(vq, b) > 0 and b[0] >= vq[2])
    return dx, own, dict(vq_from=[r3(v) for v in vq], vq_to=[r3(v) for v in nq], dx_um=dx,
                         vs_vq_gap_um=[r3(vq[0] - vs[2]), r3(nq[0] - vs[2])],
                         right_neighbour=right[1], right_gap_um=[r3(right[0]), r3(right[0] - dx)],
                         min_clear_um=min(near)[0], min_clear_to=min(near)[1])


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    probe = sys.argv[sys.argv.index("--probe") + 1] if "--probe" in sys.argv else None
    field = "--field" in sys.argv
    if probe:
        args.remove(probe)
    pin_p, pout = args[:2]
    rep_p = args[2] if len(args) > 2 else None
    import schema as S
    import pad_clock as PC
    import taps as TP
    text = open(pin_p).read()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    P = S.Plan(json.loads(text), pin_p)
    leafs = sorted(tn for tn in raw["partition_types"] if LEAF.match(tn))
    rows = [classify(P, tn, raw["partition_types"][tn]) for tn in leafs]
    hit = [r for r in rows if r["channel"]]
    if not hit:
        raise SystemExit("no leaf type with the t21 geometry")
    sp = spans(text)
    edits, done = [], []
    for r in hit:
        tn = r["type"]
        t = raw["partition_types"][tn]
        if "tap_entries" in t["clock"]:
            raise SystemExit(f"{tn}: tap_entries already present (second run refused)")
        dx, own, wr = widen(P, tn, t)
        r["move"] = wr
        k = next(i for i, c in enumerate(t["hard_cores"]) if c["inst"] == I["vq"])
        t["hard_cores"][k]["origin_um"] = [r3(t["hard_cores"][k]["origin_um"][0] + dx), t["hard_cores"][k]["origin_um"][1]]
        edits.append((*sp[("partition_types", tn, "hard_cores", k, "origin_um")], t["hard_cores"][k]["origin_um"]))
        for j in own:
            c = t["clock"]["taps"][j]
            c["xy"] = [r3(c["xy"][0] + dx), c["xy"][1]]
            edits.append((*sp[("partition_types", tn, "clock", "taps", j, "xy")], c["xy"]))
            r.setdefault("moved_core_taps", []).append(c["name"])
        if r["field"] and field:
            ents = entries_for(P, tn, r["field"])
            t["clock"]["tap_entries"] = ents
            a, b = sp[("partition_types", tn, "clock")]
            body = text[a:b]
            m = re.match(r'\{\s*\n( *)"', body)
            assert m, f"{tn}: clock object is not multi-line"
            ind = m.group(1)
            end = b - 1
            while text[end - 1] in " \t\r\n":
                end -= 1
            dump = json.dumps(ents, indent=1).replace("\n", "\n" + ind)
            edits.append((end, end, f',\n{ind}"tap_entries": {dump}'))
            r["entries"] = [dict(name=e["name"], tap=e["tap"], take_taps=e["take_taps"], xy_um=e["xy_um"],
                                 stations_um=e["stations_um"], region_um=e["region_um"]) for e in ents]
        else:
            r["entries"] = []
            r["field_why"] = ("t21 field order; regional entries not applied (opt-in --field: probe max -23 ps only, "
                              "entry sinks 345-386 ps, clk_t10 left under target)" if r["field"] else
                              "vn / vp field not in the t21 order (vn_b over vn_a, SRAM pair under it): no regional entry")
        done.append(tn)
    for a, b, new in sorted(edits, key=lambda e: e[0], reverse=True):
        text = text[:a] + (new if isinstance(new, str) else json.dumps(new, separators=(", ", ": ") if ", " in text[a:b] else (",", ":"))) + text[b:]
    if json.loads(text) != raw:
        raise SystemExit("text edits do not reproduce the edited plan")
    for kk in raw:
        if kk != "partition_types":
            assert raw[kk] == orig[kk], kk
    for tn in raw["partition_types"]:
        a, b = copy.deepcopy(raw["partition_types"][tn]), copy.deepcopy(orig["partition_types"][tn])
        if tn in done:
            a["clock"].pop("tap_entries", None)
            for c, d in zip(a["hard_cores"], b["hard_cores"]):
                if c["inst"] == I["vq"]:
                    c["origin_um"] = d["origin_um"]
            for c, d in zip(a["clock"].get("taps", []), b["clock"].get("taps", [])):
                if c.get("name", "").startswith(I["vq"] + "."):
                    c["xy"] = d["xy"]
        assert a == b, tn
    P2 = S.Plan(json.loads(text), pout)
    for r in hit:
        tn = r["type"]
        assert len(PC.tap_entries(P2, tn)) == len(r["entries"]), tn
        TP.grid_explicit_sites(P2, tn)
        r["grid_explicit_taps"] = "PASS" if TP.grid_explicit_taps(P2, tn) else "PASS(empty)"
    open(pout, "w").write(text)
    rep = dict(event=EVENT, lane="DIE-S81-85", finding="COORD geom-1733-1109 (ot_s81sl_leaf__t21 attempt_20)",
               plan_in=dict(sha256=sha(open(pin_p).read()), path=str(pin_p)), plan_out=dict(sha256=sha(text), path=str(pout)),
               rule=dict(left_x_um=LEFT_X_UM, vq_x_um=VQ_X_UM, channel_um=CHANNEL_UM, clear_um=CLEAR, hop_um=HOP_UM,
                         field_gap_um=FIELD_GAP_UM, cell=CELL),
               mode="channel+field" if field else "channel",
               matched=[r["type"] for r in hit], field_entries=[r["type"] for r in hit if r["entries"]],
               field_geometry_types=[r["type"] for r in hit if r["field"]],
               types=hit, family_not_matched=[r for r in rows if not r["channel"] and r.get("left_column")],
               scanned=len(rows))
    if probe:
        rep["probe"] = json.loads(open(probe).read())
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")
    for r in hit:
        print(json.dumps(dict(type=r["type"], dx=r["move"]["dx_um"], gap=r["move"]["vs_vq_gap_um"],
                              entries=[(e["name"], e["tap"], e["xy_um"]) for e in r["entries"]])))


if __name__ == "__main__":
    main()
