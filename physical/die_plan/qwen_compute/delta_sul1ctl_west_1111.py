#!/usr/bin/env python3
"""DIE-QC-97 SUL1CTL-WEST 11-11 plan event: move the QC sc x_su_l1_ctl column out of the east gap, +1 station.

MEASURED cause (slw_sc_v1__cl63e5a7a2 kit, rows cdebcb5d0041 and 00b638766951, plan ddcd87425566): route FAIL
GRT-0116, 221 overflow (M6 98, M3 56, M7 40), all in the 23-um gap between the qfd_dv_s5_sc2_leaf* hard core
(x 345.6-590.16, y 648-1162.08) and the E outline (613.44), along the core height.  The 457-bit S -> N x_su_l1_ctl
slot runs its four inner stations up that gap at x 604.8 (y 104, 423, 743, 1063).  The SC-EGAP layout is already in
these types, so this is a separate class.  route_supply (edge_outline, plan-route-3 core_conns) on the fixed head:
face_V 1.144/1.218 on slw_sc_v1, and face_V > 1.0 on all nine sc types that carry this column.

Form (owner-agreed west reroute, +1 pin cycle): the column moves to the open west channel at x 180-285 and gets one
more station (5 -> 6), so no hop goes over the knee: S0 stays the S-face entry, S1-S5 = TARGETS.  Each new station
is the old S1 bit-site group (its 15 x 25 um block of 1.404 x 0.27 cells, bit order unchanged) moved rigidly, snapped to the
site grid (x 0.216, y 0.27), and legalised by the nearest clear offset (2.16-um steps): no site box may overlap
another slot's site, an already placed new station, a count-strap site, a landing band rect or a hard core, or leave
the outline.  Register and per-bit hops <= KNEE_UM (403; bind reach 405).  main() also checks every bit against the
real type pin table (die_hop_scan.type_tables) and refuses a hop over the knee.

Latency (+1 station = +1 cycle, the ft_add_station convention): each sl_<s>_su_l1__x_su_l1_ctl lane whose sc
partition is a moved type gets stations/natural/cycles +1.  Its R8 partner sl_<s>_su_l0__x_su_l0_ctl in the
su_vmw_ctl_<s> bus group (DIE-QC-95 VM write landing) gets pad/cycles +1 so the group still lands in one cycle.
No other plan field changes: ports, widths, faces, windows, layers, other slots and other types are byte-same.

Refuses before touching anything: a missing type / slot / lane / group, a column not at its recorded position or
station count (already applied, or the plan changed: merge by hand), group lanes that were not aligned, and any
station that cannot be legalised under the knee.
    delta_sul1ctl_west_1111.py PLAN.json OUT.json   -> prints {stations, lanes, sha256_in, sha256_out}
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SLOT = "x_su_l1_ctl"
KNEE_UM = 403.0
SITE_X, SITE_Y = 0.216, 0.27
STEP = 2.16
MAX_STEPS = 24
TYPES = ("slw_sc_v1__cl63e5a7a2", "slw_sc_v1__cl64543eaf__cl5e017c6f", "slw_sc_v1__cl64543eaf__cl4590432d",
         "slw_sc_v2", "slw_sc_v3", "sle_sc_v1__cl115da35f", "sle_sc_v1__cl7479a5ec", "sle_sc_v2", "sle_sc_v3")
ORIG_REGS = ((431.056, 0.0), (604.8, 103.68), (604.8, 423.36), (604.8, 743.04), (604.8, 1062.72))
TARGETS = ((285.0, 175.0), (190.0, 460.0), (190.0, 840.0), (270.0, 1160.0), (450.0, 1300.0))
LANE = re.compile(r"sl_([EW]\d+)_su_l1__x_su_l1_ctl$")
NOTE = "DIE-QC-97 SUL1CTL-WEST 11-11: column moved west (x 180-285), stations 5 -> 6 (+1 pin cycle)"


def r4(v):
    return round(v + 0.0, 4)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _slot(t, name):
    for f in t.get("ft_slots") or []:
        if f.get("name") == name:
            return f
    return None


def _close(a, b):
    return abs(a[0] - b[0]) < 1e-3 and abs(a[1] - b[1]) < 1e-3


def _box(p, cell):
    return (p[0], p[1], p[0] + cell[0], p[1] + cell[1])


def _ov(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _snap(v, q):
    return round(round(v / q) * q, 4)


def _out_pt(f, p, W, H):
    lo, hi = (f.get("out_window_um") or (0.0, W))[:2]
    return (min(max(p[0], lo), hi), H)


def _obstacles(t, f, cell):
    """every other slot's site, count-strap sites, landing bands, hard cores (the moved slot's old sites excluded)."""
    obs = []
    for g in t.get("ft_slots") or []:
        if g is f:
            continue
        gc = g.get("bit_site_cell_um") or cell
        for grp in g.get("bit_sites_um") or []:
            if grp and isinstance(grp[0], list):
                obs += [_box(p, gc) for p in grp]
    for s in t.get("count_straps") or []:
        obs += [_box(p, cell) for p in (s.get("sites_um") or []) if isinstance(p, list)]
    for b in (((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).values():
        if b.get("rect_um"):
            obs.append(tuple(map(float, b["rect_um"])))
    for h in t.get("hard_cores") or []:
        (ox, oy), (cw, ch) = h["origin_um"], h["outline_um"]
        obs.append((ox, oy, ox + cw, oy + ch))
    return obs


def _check_type(tn, t):
    f = _slot(t, SLOT)
    if f is None:
        raise SystemExit(f"SUL1CTL-WEST: {tn} has no ft slot {SLOT}")
    regs = f.get("regs_um") or []
    if int(f.get("stations", 0)) != len(ORIG_REGS) or len(regs) != len(ORIG_REGS) or \
            not all(_close(a, b) for a, b in zip(regs, ORIG_REGS)):
        raise SystemExit(f"SUL1CTL-WEST: {tn} {SLOT} stations {f.get('stations')} regs {regs}, expected "
                         f"{len(ORIG_REGS)} at {[list(p) for p in ORIG_REGS]} (event already applied or plan "
                         "changed: merge by hand)")
    S = f.get("bit_sites_um") or []
    if len(S) != len(ORIG_REGS) - 1 or len({len(g) for g in S}) != 1 or f.get("in_face") != "S" or \
            f.get("out_face") != "N":
        raise SystemExit(f"SUL1CTL-WEST: {tn} {SLOT} is not the recorded S -> N column with "
                         f"{len(ORIG_REGS) - 1} equal bit-site groups")
    return f


def place_column(tn, t):
    f = _slot(t, SLOT)
    W, H = map(float, t["outline_um"])
    cell = f.get("bit_site_cell_um") or [1.404, 0.27]
    shape = [[p[0] - ORIG_REGS[1][0], p[1] - ORIG_REGS[1][1]] for p in f["bit_sites_um"][0]]
    obs = _obstacles(t, f, cell)
    entry = list(ORIG_REGS[0])
    regs, groups, rep = [entry], [], []
    cands = sorted(((a, b) for a in range(-MAX_STEPS, MAX_STEPS + 1) for b in range(-MAX_STEPS, MAX_STEPS + 1)),
                   key=lambda ab: (abs(ab[0]) + abs(ab[1]), abs(ab[1]), ab))
    for k, tgt in enumerate(TARGETS):
        last = k == len(TARGETS) - 1
        base = (_snap(tgt[0] - ORIG_REGS[1][0], SITE_X) + ORIG_REGS[1][0],
                _snap(tgt[1] - ORIG_REGS[1][1], SITE_Y) + ORIG_REGS[1][1])
        for a, b in cands:
            reg = [r4(base[0] + a * STEP), r4(base[1] + b * STEP)]
            grp = [[r4(reg[0] + p[0]), r4(reg[1] + p[1])] for p in shape]
            if min(p[0] for p in grp) < 0 or max(p[0] for p in grp) + cell[0] > W or \
                    min(p[1] for p in grp) < 0 or max(p[1] for p in grp) + cell[1] > H:
                continue
            boxes = [_box(p, cell) for p in grp]
            if any(_ov(bx, o) for bx in boxes for o in obs):
                continue
            hr = man(regs[-1], reg)
            hb = max(man(p, q) for p, q in zip(groups[-1], grp)) if groups else \
                max(man(entry, p) for p in grp)
            if last:
                hr = max(hr, man(reg, _out_pt(f, reg, W, H)))
                hb = max(hb, max(man(p, _out_pt(f, p, W, H)) for p in grp))
            if hr > KNEE_UM or hb > KNEE_UM:
                continue
            break
        else:
            raise SystemExit(f"SUL1CTL-WEST: {tn} station {k + 1}: no legal site group within "
                             f"+-{MAX_STEPS * STEP} um of {list(tgt)} (hop <= {KNEE_UM})")
        regs.append(reg)
        groups.append(grp)
        obs += boxes
        rep.append(dict(station=k + 1, target=list(tgt), reg=reg, nudge_um=[r4(a * STEP), r4(b * STEP)],
                        reg_hop=round(hr, 2), bit_hop_max=round(hb, 2)))
    f["regs_um"] = regs
    f["bit_sites_um"] = groups
    f["stations"] = len(regs)
    f["note"] = (f.get("note", "") + " | " + NOTE).strip(" |")
    return dict(type=tn, stations=[len(ORIG_REGS), len(regs)], sites=len(shape), placed=rep)


def lane_changes(raw):
    """[(su_l1 lane, su_l0 partner)] of the slices whose sc partition is a moved type (refuses before any change)."""
    lanes = raw["latency"]["lanes"]
    parts = {p["name"]: p for p in raw.get("partitions") or []}
    groups = {g["name"]: g for g in raw.get("latency_groups") or []}
    out = []
    for lid in sorted(lanes):
        m = LANE.match(lid)
        if not m:
            continue
        s = m[1]
        p = parts.get(f"sl_{s}_sc") or {}
        if p.get("type") not in TYPES:
            continue
        x0 = f"sl_{s}_su_l0__x_su_l0_ctl"
        g = groups.get(f"su_vmw_ctl_{s}")
        if x0 not in lanes or not g or sorted(g["lanes"]) != sorted([x0, lid]):
            raise SystemExit(f"SUL1CTL-WEST: {lid}: no su_vmw_ctl_{s} bus group with {x0}")
        if int(lanes[x0]["cycles"]) != int(lanes[lid]["cycles"]):
            raise SystemExit(f"SUL1CTL-WEST: {s}: su_l0/su_l1 ctl lanes not aligned "
                             f"({lanes[x0]['cycles']} vs {lanes[lid]['cycles']})")
        out.append((lid, x0))
    used = {(parts.get(f"sl_{LANE.match(l)[1]}_sc") or {}).get("type") for l, _ in out}
    if not used >= set(TYPES):
        raise SystemExit(f"SUL1CTL-WEST: no su_l1 ctl lane through {sorted(set(TYPES) - used)}")
    return out


def apply(raw):
    pt = raw["partition_types"]
    missing = [t for t in TYPES if t not in pt]
    if missing:
        raise SystemExit(f"SUL1CTL-WEST: plan lacks sc types {missing}")
    for tn in TYPES:                      # refuse before touching anything
        _check_type(tn, pt[tn])
    pairs = lane_changes(raw)
    rep = [place_column(tn, pt[tn]) for tn in TYPES]
    lanes = raw["latency"]["lanes"]
    lrep = []
    for l1, l0 in pairs:
        a, b = dict(lanes[l1]), dict(lanes[l0])
        for k in ("stations", "natural", "cycles"):
            lanes[l1][k] = int(lanes[l1][k]) + 1
        for k in ("pad", "cycles"):
            lanes[l0][k] = int(lanes[l0].get(k, 0)) + 1
        lrep.append(dict(lane=l1, cycles=[a["cycles"], lanes[l1]["cycles"]], partner=l0,
                         partner_pad=[b.get("pad", 0), lanes[l0]["pad"]]))
    return raw, rep, lrep


def verify(raw0, raw1, repo):
    """real-pin per-bit hops (die_hop_scan) and the re-derived latency delta (gen.latency_table)."""
    sys.path.insert(0, str(Path(repo) / "tools" / "die_plan"))
    sys.path.insert(0, str(Path(repo)))
    import schema as S, gen, die_hop_scan as DH, ft_bit_sites  # noqa: E401,E402
    P = S.Plan(raw1)
    hops = {}
    for tn in TYPES:
        ft_bit_sites.validate_slot(_slot(P.types[tn], SLOT))
        pins, chains = DH.type_tables(P, tn)
        po = pins[SLOT + "_o"]
        w = 0.0
        for bit, st in chains[SLOT].items():
            pts = list(st) + [po[bit][:2]]
            w = max([w] + [DH.md(a, b) for a, b in zip(pts, pts[1:])])
        if w > KNEE_UM:
            raise SystemExit(f"SUL1CTL-WEST: {tn} real-pin hop {w:.1f} > {KNEE_UM}")
        hops[tn] = round(w, 2)
    t0, t1 = gen.latency_table(S.Plan(raw0)), gen.latency_table(P)
    dl = {k: {f: t1[k].get(f, 0) - t0[k].get(f, 0) for f in ("stations", "natural", "pad", "cycles")
              if t1[k].get(f, 0) != t0[k].get(f, 0)} for k in t1 if t1[k] != t0[k]}
    return hops, dl


def _style(b, obj):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, separators=(",", ":"))):
        if f(obj).encode() == b:
            return f
    raise SystemExit("SUL1CTL-WEST: input JSON style not recognised (would not stay byte-same)")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--repo", default=str(Path(__file__).resolve().parents[3]),
                   help="checkout whose tools/die_plan verifies the result (real pins, latency)")
    p.add_argument("--no-verify", action="store_true")
    a = p.parse_args(argv)
    src = Path(a.input).read_bytes()
    raw = json.loads(src)
    dump = _style(src, raw)
    raw0 = json.loads(src)
    raw, rep, lrep = apply(raw)
    res = {"stations": rep, "lanes": lrep}
    if not a.no_verify:
        res["real_pin_hop_max"], res["latency_delta_rederived"] = verify(raw0, raw, a.repo)
    out = dump(raw).encode()
    Path(a.output).write_bytes(out)
    res.update(sha256_in=hashlib.sha256(src).hexdigest(), sha256_out=hashlib.sha256(out).hexdigest())
    print(json.dumps(res))


if __name__ == "__main__":
    main()
