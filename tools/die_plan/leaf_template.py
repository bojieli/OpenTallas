#!/usr/bin/env python3
"""LEAF-TEMPLATE (FP-CONVERGE-S81, COORD ruling 11-25 05:5x): one parameterised floor for every ot_s81sl_leaf / ot_s81sl_kv_leaf type.

13 Fable reviews of the c9s leaf family found the same skeleton defects (slots < 28 um between hub cores, hubs boxed in, ft trunks over
lane columns, vn_a/vn_b far apart, stations / roots outside the outline, seat piles).  This tool

  seed   PLAN --types RE --out SEED.json     the template floor as a core_place.py seed {type: {inst: {origin_um, orient}}}:
                                             vn_b / vn_a on the centre line (gap STREET, centre distance <= 380 um), ve_m|ve_s abutted,
                                             vs above them, lanes in two groups (2 columns x rows) either side of the hub with a
                                             CORRIDOR (>= 150 um) between hub and lane group, STREET between lanes; orientation is kept
                                             (pins never move; core_place flips/legalises the seed and re-routes stations, taps, riders)
  check  PLAN --types RE [--json OUT]        the template rules measured on a plan (report-only; exit 0), see RULES
  run    PLAN --types RE --out-plan P --event E [-- extra core_place args]   seed + core_place.py --seed (+ --slot-clear/--ft-resite)

core_place.py is the mover: it keeps register counts, re-routes every station whose end moved, moves the coordinates that ride on a core
and runs the EQ gate; this module only designs the seed and states the acceptance rules.  Growth / re-shape / stations are pre-approved."""
import argparse
import json
import math
import re
import sys
from pathlib import Path

G = 4.32
STREET = 43.2             # seed street (10 x 4.32, also the >= 43 um facing-pin clearance)
MIN_STREET = 41.0         # the rule: >= 41 um between lane cores
CORRIDOR = 151.2          # >= 150 um hub corridor to each lane group (35 x 4.32)
SLOT_MIN = 28.08          # a gap in (0, SLOT_MIN) between two hard cores is a slot defect (ADV-SLOT-GAP)
HUB_MAX = 380.0           # vn_a / vn_b centre distance
EDGE = 8.64
LEAF_RE = re.compile(r"^ot_s81sl_(kv_)?leaf__")
ROT = ("R90", "R270", "MXR90", "MYR90")
RULES = ("OVERLAP", "OUTSIDE", "LANE-STREET", "SLOT", "HUB-DIST", "ITEM-OUTSIDE", "ITEM-IN-CORE")


def snap(v):
    return round(round(v / G) * G, 4)


def up(v):
    return round(math.ceil(v / G - 1e-9) * G, 4)


def dims(h):
    w, hh = h["outline_um"]
    return (hh, w) if h.get("orient", "R0") in ROT else (w, hh)


def rect(h):
    o = h["origin_um"]
    w, hh = dims(h)
    return (o[0], o[1], o[0] + w, o[1] + hh)


def short(h):
    return h["inst"].split(".", 1)[-1]


def gap(a, b):
    """edge gap of two rects; 0 for touching, negative for overlap depth, None when their projections do not overlap on either axis
    (a facing slot needs overlapping projection on the other axis)"""
    dx = max(a[0] - b[2], b[0] - a[2])
    dy = max(a[1] - b[3], b[1] - a[3])
    if dx < 0 and dy < 0:
        return -min(-dx, -dy)
    if dx >= 0 and dy < 0:
        return dx
    if dy >= 0 and dx < 0:
        return dy
    return None


def kind(h):
    s = short(h)
    if re.search(r"g_ln\[\d+\]", s):
        return "lane"
    if "u_b0" in s or "u_b1" in s:
        return "sram"
    return s.replace("u_vn.", "").replace("u_ve.", "")


def build_seed(t, street=STREET, corridor=CORRIDOR):
    """-> ({inst: {origin_um, orient}}, notes) for one leaf type row; raises ValueError when the outline cannot hold the template"""
    W, H = t["outline_um"]
    hc = {kind(h): h for h in t["hard_cores"] if kind(h) not in ("lane", "sram")}
    lanes = sorted((h for h in t["hard_cores"] if kind(h) == "lane"), key=lambda h: int(re.search(r"\[(\d+)\]", h["inst"]).group(1)))
    srams = sorted((h for h in t["hard_cores"] if kind(h) == "sram"), key=lambda h: h["inst"])
    need = ("u_a", "u_b", "u_m", "u_s", "u_vs")
    for n in need:
        if n not in hc:
            raise ValueError("no %s core" % n)
    seed, notes = {}, []

    def put(h, x, y):
        seed[h["inst"]] = {"origin_um": [snap(x), snap(y)], "orient": h.get("orient", "R0")}

    ld = dims(lanes[0])
    vb, va = dims(hc["u_b"]), dims(hc["u_a"])
    vem, ves = dims(hc["u_m"]), dims(hc["u_s"])
    vsd = dims(hc["u_vs"])
    hubw = max(vb[0], va[0], vem[0] + ves[0], vsd[0])
    cx = snap(W / 2 - hubw / 2)
    # centre column, bottom to top: vn_b, vn_a (centre distance <= 380), ve_m|ve_s abutted, vs
    y = up(max(EDGE, 0.0))
    cols = [("u_b", vb), ("u_a", va)]
    ycur = y
    pos = {}
    for n, d in cols:
        pos[n] = (cx + (hubw - d[0]) / 2, ycur)
        ycur = up(ycur + d[1] + street)
    pos["u_m"] = (cx + (hubw - vem[0] - ves[0]) / 2, ycur)
    pos["u_s"] = (pos["u_m"][0] + vem[0], ycur)
    ycur = up(ycur + max(vem[1], ves[1]) + street)
    pos["u_vs"] = (cx + (hubw - vsd[0]) / 2, ycur)
    top = ycur + vsd[1]
    if top > H - EDGE:
        raise ValueError("centre column %.1f um > outline %.1f" % (top, H))
    for n, p in pos.items():
        put(hc[n], *p)
    cd = abs((pos["u_a"][1] + va[1] / 2) - (pos["u_b"][1] + vb[1] / 2))
    notes.append("hub centre distance %.1f um" % cd)
    # lane groups: 2 columns x rows each side, corridor from the hub column edge
    per = (len(lanes) + 1) // 2
    ncol = 2
    nrow = math.ceil(per / ncol)
    gw = ncol * ld[0] + (ncol - 1) * street
    gh = nrow * ld[1] + (nrow - 1) * street
    xl = cx - corridor - gw
    xr = cx + hubw + corridor
    if xl < EDGE or xr + gw > W - EDGE:
        raise ValueError("lane groups need x %.1f..%.1f of %.1f" % (xl, xr + gw, W))
    y0 = snap((H - gh) / 2)
    for i, h in enumerate(lanes):
        g, k = divmod(i, per)
        c, r = k % ncol, k // ncol
        x = (xl if g == 0 else xr) + c * (ld[0] + street)
        put(h, x, y0 + r * (ld[1] + street))
    # remaining service cores (vsw, vq, rxsb, rxsf) and SRAMs in the free bands below / above the lane groups
    rest = [hc[n] for n in ("u_vsw", "u_vq", "u_rxsb", "u_rxsf") if n in hc]
    bands = []
    for g, x0 in ((0, xl), (1, xr)):
        bands.append((x0, EDGE, gw, y0 - street - EDGE))                  # below the group
        bands.append((x0, y0 + gh + street, gw, H - EDGE - (y0 + gh + street)))   # above
    order = sorted(rest, key=lambda h: -dims(h)[0] * dims(h)[1])
    free = [list(b) for b in bands]
    for h in order:
        w, hh = dims(h)
        for b in free:
            if b[2] >= w and b[3] >= hh:
                put(h, b[0], b[1])
                b[0] += w + street
                b[2] -= w + street
                break
        else:
            raise ValueError("no band for %s (%.0f x %.0f)" % (short(h), w, hh))
    ytop = top
    for h in srams:                                   # SRAM pair stacked in the centre column above vs, else in a band
        w, hh = dims(h)
        yy = up(ytop + street)
        if yy + hh <= H - EDGE and w <= hubw:
            put(h, cx + (hubw - w) / 2, yy)
            ytop = yy + hh
            continue
        for b in free:
            if b[2] >= w and b[3] >= hh:
                put(h, b[0], b[1] + b[3] - hh)
                b[3] -= hh + street
                break
        else:
            raise ValueError("no band for %s" % short(h))
    return seed, notes


def check_type(t):
    """-> {rule: [detail]} of the template rules on one type row"""
    W, H = t["outline_um"]
    hcs = t.get("hard_cores") or []
    rs = [rect(h) for h in hcs]
    out = {r: [] for r in RULES}
    for i, (h, a) in enumerate(zip(hcs, rs)):
        if a[0] < 0 or a[1] < 0 or a[2] > W + 1e-6 or a[3] > H + 1e-6:
            out["OUTSIDE"].append(short(h))
        for j in range(i + 1, len(hcs)):
            g = gap(a, rs[j])
            if g is None:
                continue
            ki, kj = kind(h), kind(hcs[j])
            if g < -1e-6:
                out["OVERLAP"].append("%s|%s %.2f" % (short(h), short(hcs[j]), g))
            elif 0 < g < SLOT_MIN:
                out["SLOT"].append("%s|%s %.2f" % (short(h), short(hcs[j]), g))
            if ki == "lane" and kj == "lane" and -1e-6 <= g < MIN_STREET - 1e-6:
                out["LANE-STREET"].append("%s|%s %.2f" % (short(h), short(hcs[j]), g))
    byk = {kind(h): h for h in hcs}
    if "u_a" in byk and "u_b" in byk:
        a, b = rect(byk["u_a"]), rect(byk["u_b"])
        d = math.hypot((a[0] + a[2]) / 2 - (b[0] + b[2]) / 2, (a[1] + a[3]) / 2 - (b[1] + b[3]) / 2)
        if d > HUB_MAX:
            out["HUB-DIST"].append("vn_a-vn_b %.1f um" % d)

    def items():
        for s in t.get("internal_stations") or []:
            for p in s.get("regs_um") or []:
                yield "station reg", p
        for k, v in (t.get("relay_sites") or {}).items():
            yield "relay " + k, v
        for f in t.get("ft_slots") or []:
            for p in f.get("regs_um") or []:
                yield "ft reg", p
            for grp in f.get("bit_sites_um") or []:
                for p in grp:
                    yield "ft bit", p
        for p in (t.get("clock") or {}).get("reach_fix_sinks") or []:
            yield "reach_fix", (p if isinstance(p[0], (int, float)) else p[0])

    seen = {}
    for what, p in items():
        try:
            x, y = float(p[0]), float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        if x < 0 or y < 0 or x > W or y > H:
            seen["o:" + what] = seen.get("o:" + what, 0) + 1
        elif any(a[0] + 0.01 < x < a[2] - 0.01 and a[1] + 0.01 < y < a[3] - 0.01 for a in rs):
            seen["c:" + what] = seen.get("c:" + what, 0) + 1
    for k, n in sorted(seen.items()):
        out["ITEM-OUTSIDE" if k[0] == "o" else "ITEM-IN-CORE"].append("%s x%d" % (k[2:], n))
    return out


def cmd_seed(a):
    P = json.loads(Path(a.plan).read_text())
    seeds, rep = {}, {}
    for tn, t in sorted(P["partition_types"].items()):
        if not LEAF_RE.match(tn) or not re.search(a.types, tn) or not t.get("hard_cores"):
            continue
        try:
            s, notes = build_seed(t, a.street, a.corridor)
        except ValueError as e:
            rep[tn] = "INFEASIBLE: %s" % e
            continue
        seeds[tn] = s
        rep[tn] = "; ".join(notes)
    Path(a.out).write_text(json.dumps(seeds) + "\n")
    for k, v in rep.items():
        print(k, v)
    print("seeded %d of %d" % (len(seeds), len(rep)))


def cmd_check(a):
    P = json.loads(Path(a.plan).read_text())
    res = {}
    for tn, t in sorted(P["partition_types"].items()):
        if LEAF_RE.match(tn) and re.search(a.types, tn) and t.get("hard_cores"):
            res[tn] = check_type(t)
    cnt = {r: sum(1 for v in res.values() if v[r]) for r in RULES}
    for tn, v in res.items():
        print(tn, " ".join("%s=%d" % (r, len(v[r])) for r in RULES if v[r]) or "OK")
    print("types", len(res), "failing by rule", cnt)
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1) + "\n")


def _load_model(plan, tn, die, repo):
    """TypeModel + Grid of core_place.py for one type, set up exactly as core_place.main does (scoring only)"""
    import gzip
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import core_place as CP
    RS = CP.RS
    plan = Path(plan)
    repo = Path(repo)
    raw = plan.read_bytes()
    P = json.loads(gzip.decompress(raw)) if plan.suffix == ".gz" else json.loads(raw)
    RS.REF_DIRS[:] = [str(plan.parent)]
    die_dir = repo / "physical" / "die_plan" / die
    if not die_dir.is_dir():
        die_dir = plan.parent
    rs_cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"])
    here = Path(CP.__file__).resolve().parent
    try:
        rs_cfg["views"] = json.loads((here / "route_supply_views.json").read_text()).get("views", {})
    except (OSError, ValueError):
        rs_cfg["views"] = {}
    try:
        rs_cfg["kit_views"] = json.loads((here / "route_supply_kit_views.json").read_text()).get(die, {})
    except (OSError, ValueError, AttributeError):
        rs_cfg["kit_views"] = {}
    conns = RS.load_conns(die_dir, None, plan.parent, [])
    cfg = dict(gap=34.56, sweeps=12, topk=4, lam=4.0, reach=360.0, grid_um=21.6, grt_halving="full", fixed_re="", rs=rs_cfg,
               flips_only=False, gap_pinface=None, face_clear=[], slot_clear=[".*"], window_clear=False, ft_resite=True,
               taps_movable=False, bus_reg=False, detour_fix=False, take_regs=False, slot_ft=0.0, block_shift=False, link_reg=[])
    t = P["partition_types"][tn]
    M = CP.TypeModel(tn, t, die_dir, repo, conns, cfg)
    mg = 34.56
    for k in range(M.m):
        for j in range(k + 1, M.m):
            x, y, w, h = M.cbb[k]
            X, Y, Wj, Hj = M.cbb[j]
            mg = min(mg, max(X - (x + w), x - (X + Wj), Y - (y + h), y - (Y + Hj)))
    cfg["gap"] = max(CP.G, math.floor(mg / CP.G + 1e-6) * CP.G)
    Gd = CP.Grid(M, cfg)
    M.init_limits()
    return CP, P, t, M, Gd


def _score(M, Gd, lam=4.0):
    SH, SV = Gd.supply()
    DH, DV = Gd.demand()
    oH, oV, _, _ = Gd.ovf(DH, DV, SH, SV)
    q = range(len(M.L))
    bit = M.cost(q)
    tv = M.tviol(q)
    return bit + 25.0 * oH / 1e3 + 11.0 * oV / 1e3 + 2e5 * tv, dict(bit_mm=round(bit / 1e3), ovfH=round(oH), ovfV=round(oV), tv=tv)


def cmd_optimize(a):
    """connectivity-aware seed: start from the template floor, then swap identical lane cores between template slots (and mirror whole
    groups) while the core_place objective (bit-um + overflow + timing violations) improves; writes the seed for core_place --seed"""
    import random
    P0 = json.loads(Path(a.plan).read_text())
    out = {}
    for tn, t in sorted(P0["partition_types"].items()):
        if not LEAF_RE.match(tn) or not re.search(a.types, tn) or not t.get("hard_cores"):
            continue
        try:
            seed, notes = build_seed(t, a.street, a.corridor)
        except ValueError as e:
            print(tn, "INFEASIBLE", e)
            continue
        CP, _, _, M, Gd = _load_model(a.plan, tn, a.die, a.repo)
        log = lambda s: print(s, flush=True)   # noqa: E731
        CP.apply_seed(M, seed, log)
        sc0, d0 = _score(M, Gd)
        lanes = [k for k in range(M.m) if re.search(r"g_ln\[\d+\]", M.inst[M.CL[k][0]])]
        print(tn, "template seed", d0, "lanes", len(lanes), flush=True)
        rnd = random.Random(1)
        best, bd = sc0, d0
        for sweep in range(a.sweeps):
            imp = 0
            pairs = [(x, y) for i, x in enumerate(lanes) for y in lanes[i + 1:]]
            rnd.shuffle(pairs)
            for x, y in pairs:
                px, py = tuple(M.cpos[x]), tuple(M.cpos[y]); M.cpos[x] = py; M.cpos[y] = px
                sc, d = _score(M, Gd)
                if sc < best - 1e-6:
                    best, bd, imp = sc, d, imp + 1
                else:
                    px, py = tuple(M.cpos[x]), tuple(M.cpos[y]); M.cpos[x] = py; M.cpos[y] = px
            print(" sweep", sweep, "swaps", imp, bd, flush=True)
            if not imp:
                break
        # phase 2: orientation flips of every cluster (pins face the right way) and short shifts of the hub/service clusters
        shifts = [(dx * STREET, dy * STREET) for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2) if (dx or dy)]
        for sweep in range(a.sweeps):
            imp = 0
            order = list(range(M.m))
            rnd.shuffle(order)
            for k in order:
                for fo in ("R0", "MY", "MX", "R180"):
                    if fo == M.cflip[k]:
                        continue
                    old = M.cflip[k]
                    M.cflip[k] = fo
                    if not M.legal(k, *M.cpos[k]):
                        M.cflip[k] = old
                        continue
                    sc, d = _score(M, Gd)
                    if sc < best - 1e-6:
                        best, bd, imp = sc, d, imp + 1
                    else:
                        M.cflip[k] = old
                if k in lanes:
                    continue
                x0, y0 = M.cpos[k]
                bpos = None
                for dx, dy in shifts:
                    pos = (snap(x0 + dx), snap(y0 + dy))
                    if not M.legal(k, *pos):
                        continue
                    M.cpos[k] = pos
                    sc, d = _score(M, Gd)
                    if sc < best - 1e-6:
                        best, bd, bpos = sc, d, pos
                M.cpos[k] = bpos if bpos else (x0, y0)
                imp += 1 if bpos else 0
            print(" flip/shift sweep", sweep, "improved", imp, bd, flush=True)
            if not imp:
                break
        res = {}
        for k in range(M.m):
            i = M.CL[k][0]
            res[M.inst[i]] = {"origin_um": [float(M.core_origin(i)[0]), float(M.core_origin(i)[1])], "orient": M.core_orient(i)}
        out[tn] = res
        print(tn, "optimised", bd, "from", d0, flush=True)
    Path(a.out).write_text(json.dumps(out) + "\n")


def cmd_run(a, rest):
    import subprocess
    seedf = str(Path(a.out_plan).with_suffix(".seed.json"))
    ns = argparse.Namespace(plan=a.plan, types=a.types, out=seedf, street=a.street, corridor=a.corridor)
    cmd_seed(ns)
    names = [tn for tn in json.loads(Path(seedf).read_text())]
    tool = Path(__file__).resolve().parent / "core_place.py"
    cmd = [sys.executable, "-I", str(tool), a.plan, "--types", ",".join(names), "--seed", seedf, "--out-plan", a.out_plan,
           "--event", a.event, "--slot-clear", ".*", "--ft-resite"] + rest
    print(" ".join(cmd))
    return subprocess.call(cmd)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("seed", "check", "run", "optimize"):
        p = sub.add_parser(n)
        p.add_argument("plan")
        p.add_argument("--types", default=".*")
        p.add_argument("--street", type=float, default=STREET)
        p.add_argument("--corridor", type=float, default=CORRIDOR)
        if n in ("seed", "optimize"):
            p.add_argument("--out", required=True)
        if n == "optimize":
            p.add_argument("--die", default="s81")
            p.add_argument("--repo", default=".")
            p.add_argument("--sweeps", type=int, default=6)
        if n == "check":
            p.add_argument("--json")
        if n == "run":
            p.add_argument("--out-plan", required=True)
            p.add_argument("--event", required=True)
    a, rest = ap.parse_known_args(argv)
    if a.cmd == "seed":
        cmd_seed(a)
    elif a.cmd == "check":
        cmd_check(a)
    elif a.cmd == "optimize":
        cmd_optimize(a)
    else:
        return cmd_run(a, [x for x in rest if x != "--"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
