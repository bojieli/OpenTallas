#!/usr/bin/env python3
"""METHODOLOGY v4.1 12.8 (OWNER 2026-10-26 ~07:3x / d1 ~08:0x): root-cause die clock structure, no tweaks.

Opt-in through ``die_clock_mesh.py build --rule-12-8``; the flag is recorded in mesh.json meta["rule_12_8"] and every
later step (balance / combo / mesh / report) follows it from there.  Without the flag nothing here runs, so the
default flow is byte-identical.

  (1) skew gate (12.4b): CPPR is credited ONLY at the last common H-tree/tree node of the two taps (the region root
      for two taps fed from one mesh, the die root across regions).  The mesh-node-credited number (credit = the
      smaller of the two stub-input early/late ranges) is INFO only.
  (2) early taps (12.3 / 12.8d): no compensation.  A tap with a declared early offset is a gate FAIL that names the
      core type to restructure; arrivals are compared raw (no offset add-back), no compensating branches.
  (3) sizing (12.8d / d1): no measured balance pads, no per-tap trims, no useful skew, no post-CTS swaps.  The plan
      tool sizes each stub buffer ONCE, deterministically, from plan geometry + loads (liberty NLDM + plan wire RC),
      before any block is built; it never reads a CTS / GRT / STA result.  ``balance`` becomes a structural audit
      (plan-model tree imbalance per level), adds no cell and reads no measurement.
  (4) shielding (12.7a): every H-tree leg, split tail, stub and the root net is a FIXED pre-route (special net, M8
      horizontal / M9 vertical NDR wire) with a VSS stripe on both sides and a routing obstruction over the shield
      spacing, so no parallel signal track lies within it; GRT routes none of them.  Their RC comes from the same
      fixed geometry (SPEF written here), so meta.clock_shield.complete is True.
"""
import gzip
import math
import re
from collections import defaultdict
from pathlib import Path

TREE_OFF_UM = 0.864        # fixed tree wires run one track pair off the cell-pin line: never collinear with a strap
SEG_UM = 25.0              # pi-section length of the fixed-wire SPEF
STUB_SIZES = ("BUFx4_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R",
              "BUFx16f_ASAP7_75t_R", "BUFx24_ASAP7_75t_R")
TAP_SLEW_MAX_PS = 80.0     # plan design limit for the modelled stub output slew (partition first tap buffer)
MESH_SLEW_PS = 40.0        # plan assumption for the stub input slew (mesh)


def enabled(M):
    return bool((M.get("meta") or {}).get("rule_12_8"))


# ------------------------------------------------------------------------------------------------------ liberty
def _table(blk, kind):
    m = re.search(kind + r" \(\w+\) \{\s*index_1 \(\"([^\"]+)\"\);\s*index_2 \(\"([^\"]+)\"\);\s*values \((.*?)\);",
                  blk, re.S)
    sl = [float(v) for v in m.group(1).split(",")]
    ld = [float(v) for v in m.group(2).split(",")]
    rows = [[float(v) for v in r.split(",")] for r in re.findall(r"\"([^\"]+)\"", m.group(3))]
    return sl, ld, rows


def lib_cells(corner, libdir, names=STUB_SIZES):
    """{cell: dict(delay=(sl, ld, rows), trans=(...), cap=fF)} from the ASAP7 RVT INVBUF NLDM liberty."""
    f = Path(libdir) / f"asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz"
    txt = gzip.open(f, "rt").read()
    out = {}
    for n in names:
        i = txt.index(f"cell ({n})")
        j = txt.find("cell (", i + 10)
        blk = txt[i:j if j > 0 else len(txt)]
        out[n] = dict(delay=_table(blk, "cell_rise"), trans=_table(blk, "rise_transition"),
                      cap=float(re.search(r"rise_capacitance : ([\d.]+)", blk).group(1)))
    return out


def _bilin(tab, s, c):
    sl, ld, rows = tab

    def seg(v, xs):
        k = max(1, min(len(xs) - 1, next((q for q in range(1, len(xs)) if v <= xs[q]), len(xs) - 1)))
        return k, (v - xs[k - 1]) / (xs[k] - xs[k - 1])
    i, ti = seg(s, sl)
    j, tj = seg(c, ld)
    a = rows[i - 1][j - 1] + tj * (rows[i - 1][j] - rows[i - 1][j - 1])
    b = rows[i][j - 1] + tj * (rows[i][j] - rows[i][j - 1])
    return a + ti * (b - a)


def stage(lib, slew_in, r_wire, c_wire, c_load):
    """plan RC model of one buffer stage: NLDM at the lumped load + Elmore of its wire; returns (delay, out slew)."""
    d = _bilin(lib["delay"], slew_in, c_wire + c_load)
    s = _bilin(lib["trans"], slew_in, c_wire + c_load)
    el = r_wire * (c_wire / 2 + c_load)                 # kohm * fF = ps
    return d + el, math.sqrt(s * s + (2.2 * el) ** 2)


def wire_rc(nd, layer_rc):
    r = (layer_rc["M8"][0] + layer_rc["M9"][0]) / 2 * nd["rf"]
    c = (layer_rc["M8"][1] + layer_rc["M9"][1]) / 2 * nd["cf"]
    return r, c


def _centre(cells, c, buf_w, row_y):
    v = cells[c]
    return v["x"] + buf_w / 2, v["y"] + row_y / 2


def stub_chains(cells, nets, taps):
    """tap port -> [cell, ..., 'port:t_...'] from its stub buffer through the split repeaters to the port."""
    by_drv = {n["drv"]: n for n in nets}
    out = {}
    for t in taps:
        ch, c = [t["stub"]], t["stub"]
        while True:
            ld = by_drv[c]["loads"]
            assert len(ld) == 1, f"stub chain {t['stub']} branches"
            ch.append(ld[0])
            if ld[0].startswith("port:"):
                break
            c = ld[0]
        out[t["port"]] = ch
    return out


def size_stubs(cells, nets, taps, libs, nd, layer_rc, tap_load_ff, buf, buf_w, row_y,
               slew_max=TAP_SLEW_MAX_PS, slew_in=MESH_SLEW_PS):
    """12.8 d1: deterministic per-tap stub sizing from the plan RC/load model only.  Per clock region the target is
    the slowest stub chain at full size (BUFx24); every other stub takes the size whose modelled chain delay is
    closest to that target with modelled stage slews <= slew_max.  Sets cells[stub]['lib'] and returns the record."""
    r_um, c_um = wire_rc(nd, layer_rc)
    txy = {t["port"]: tuple(t["xy"]) for t in taps}
    chains = stub_chains(cells, nets, taps)

    def model(ch, first_lib):
        s, tot, smax = slew_in, 0.0, 0.0
        for k, c in enumerate(ch[:-1]):
            nxt = ch[k + 1]
            a = _centre(cells, c, buf_w, row_y)
            b = txy[nxt[5:]] if nxt.startswith("port:") else _centre(cells, nxt, buf_w, row_y)
            L = abs(a[0] - b[0]) + abs(a[1] - b[1])
            cl = tap_load_ff if nxt.startswith("port:") else libs[buf]["cap"]
            d, s = stage(libs[first_lib if k == 0 else buf], s, r_um * L, c_um * L, cl)
            tot, smax = tot + d, max(smax, s)
        return tot, smax
    full = {t["port"]: model(chains[t["port"]], buf) for t in taps}
    by_reg = defaultdict(list)
    for t in taps:
        by_reg[t.get("region")].append(t)
    rec = dict(model="NLDM lumped load + Elmore wire, plan geometry only (12.8 d1); no measured input",
               sizes=list(STUB_SIZES), slew_max_ps=slew_max, slew_in_ps=slew_in, tap_load_ff=tap_load_ff,
               regions={}, hist=defaultdict(int))
    for rk, ts in sorted(by_reg.items(), key=lambda kv: (kv[0] is None, kv[0])):
        target = max(full[t["port"]][0] for t in ts)
        pre, post = [], []
        for t in ts:
            ch = chains[t["port"]]
            best = None
            for lib in STUB_SIZES:
                d, s = model(ch, lib) if lib != buf else full[t["port"]]
                if s > slew_max and lib != buf:
                    continue
                if best is None or abs(d - target) < abs(best[1] - target) - 1e-9:
                    best = (lib, d, s)
            lib, d, s = best
            if lib != buf:
                cells[t["stub"]]["lib"] = lib
            t["stub_lib"] = lib
            t["stub_model_ps"] = round(d, 3)
            rec["hist"][lib] += 1
            pre.append(full[t["port"]][0])
            post.append(d)
        rec["regions"][str(rk)] = dict(taps=len(ts), target_ps=round(target, 3),
                                       model_spread_full_ps=round(max(pre) - min(pre), 3),
                                       model_spread_sized_ps=round(max(post) - min(post), 3))
    rec["hist"] = dict(sorted(rec["hist"].items()))
    return rec


def early_offset_taps(P, taps, plan_tap_early):
    """12.8d: every tap with a declared early offset = one FAIL entry naming the core type to restructure."""
    import schema as S
    core_of = {}
    for tn in {P.parts[t["part"]]["type"] for t in taps}:
        for port, _, _, tp in S.core_taps(P, tn):
            core_of[(tn, port)] = tp.get("budget_owner") or tp.get("name") or tp.get("core") or port
    out = []
    for t in taps:
        e = plan_tap_early.get((t["part"], t["tap"])) or {}
        if t.get("early_ps") or any(float(v or 0) > 0 for v in e.values()):
            tn = P.parts[t["part"]]["type"]
            out.append(dict(part=t["part"], type=tn, tap=t["tap"], port=t["port"],
                            core=core_of.get((tn, t["tap"]), t["tap"]),
                            early_ps={k: round(float(v), 3) for k, v in e.items()} or {"TT": t.get("early_ps")}))
    return out


def summarize_early(rows):
    by = defaultdict(lambda: dict(taps=0, max_early_tt_ps=0.0, types=set()))
    for r in rows:
        b = by[r["core"]]
        b["taps"] += 1
        b["max_early_tt_ps"] = max(b["max_early_tt_ps"], float(r["early_ps"].get("TT") or 0))
        b["types"].add(r["type"])
    return {k: dict(taps=v["taps"], max_early_tt_ps=round(v["max_early_tt_ps"], 2), partition_types=sorted(v["types"]),
                    action="RESTRUCTURE core clock to the die common latency (12.3/12.8b); no early tap")
            for k, v in sorted(by.items())}


# ------------------------------------------------------------------------------------------------ plan errors / sites
class PlanError(Exception):
    """CLOCK-128-R2: the plan cannot host the 12.8 clock structure (fail closed).  rows = [dict(kind, name, ...)];
    cmd_build writes them to <out>/plan_errors.json and exits 2.  Kinds: empty_tree_net, unplaced, no_plan_site,
    site_taken, pg_snap."""

    def __init__(self, rows):
        self.rows = list(rows)
        kinds = defaultdict(int)
        for r in self.rows:
            kinds[r["kind"]] += 1
        super().__init__(f"{len(self.rows)} plan error(s): " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))


SITE_SNAP_UM = 0.5         # COORD 11:26: the only move allowed between a lattice point and its plan site (PG-track snap)
SITES_SCHEMA = "ot_clock_sites/1"


class SiteIndex:
    """reserved die-frame lattice island sites from the master-plan slices (12.2a1 pushdown cells inside partitions).
    take(p) returns the nearest unused site within snap_um of the lattice point p (Manhattan) and marks it used;
    otherwise (None, nearest distance, nearest site) -- the caller records a plan error, never slides."""

    def __init__(self, sites, snap_um=SITE_SNAP_UM, B=200.0):
        self.snap, self.B, self.used = float(snap_um), B, {}
        self.sites = list(sites)
        self.bins = defaultdict(list)
        for k, s in enumerate(self.sites):
            self.bins[(int(s["xy_um"][0] // B), int(s["xy_um"][1] // B))].append(k)

    def nearest(self, p, free=True):
        i, j = int(p[0] // self.B), int(p[1] // self.B)
        best = (float("inf"), None)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for k in self.bins.get((i + di, j + dj), []):
                    if free and k in self.used:
                        continue
                    s = self.sites[k]["xy_um"]
                    d = abs(s[0] - p[0]) + abs(s[1] - p[1])
                    if d < best[0]:
                        best = (d, k)
        return best

    def take(self, p, who):
        d, k = self.nearest(p)
        if k is not None and d <= self.snap + 1e-9:
            self.used[k] = who
            return self.sites[k], d, None
        d_any, k_any = self.nearest(p, free=False)
        err = dict(lattice_um=[round(p[0], 4), round(p[1], 4)],
                   nearest_um=None if k is None else round(d, 4),
                   nearest_site=None if k is None else self.sites[k]["name"])
        if k_any is not None and d_any <= self.snap + 1e-9:   # the right site exists but another cell already took it
            err.update(kind="site_taken", site=self.sites[k_any]["name"], taken_by=self.used.get(k_any))
        else:
            err.update(kind="no_plan_site", detail=f"no reserved plan site within {self.snap} um")
        return None, d, err


def load_plan_sites(path, plan_sha256=None):
    """read an ot_clock_sites/1 file (die frame; clock_plan_sites.py writes it from the master-plan slices).  The
    file must name the same plan (sha256) as the build."""
    import json
    raw = json.loads(Path(path).read_text())
    if raw.get("schema") != SITES_SCHEMA:
        raise ValueError(f"{path}: schema {raw.get('schema')!r} is not {SITES_SCHEMA}")
    if plan_sha256 and raw.get("plan_sha256") and raw["plan_sha256"] != plan_sha256:
        raise ValueError(f"{path}: sites were cut from plan {raw['plan_sha256'][:12]}, build plan is {plan_sha256[:12]}")
    if not raw.get("sites"):
        raise ValueError(f"{path}: no sites")
    return raw


# ------------------------------------------------------------------------------------------------ fixed wires
def fixed_wires(M, cells, nets, buf_w, row_y, off=TREE_OFF_UM, router=None, pin_stack=False, port_on_trunk=False):
    """every tree net (root, H-tree legs/nodes/leaves, split tails, stubs) as a fixed comb pre-route: one trunk on the
    net's dominant axis (M8 horizontal / M9 vertical), offset `off` from the driver pin line, plus one perpendicular
    drop per load, offset `off` from the load pin line.  Returns [dict(name, drv, pins, segs, rc_nodes)].
    router (TrackRouter, CLOCK-128 shield lane): each trunk / drop goes on the nearest PG-aware routing track whose
    clock metal + both VSS shields clear every same-layer shape of another net (die PG grid, mesh straps + shields,
    earlier tree wires + shields); a segment with no legal track within router.max_move is a plan error."""
    txy = {t["port"]: tuple(t["xy"]) for t in M["taps"]}
    root = tuple(M["meta"]["root_um"])

    def xy(p):
        if p.startswith("port:"):
            return root if p == "port:root" else txy[p[5:]]
        return _centre(cells, p, buf_w, row_y)
    empty = [n["name"] for n in nets if not n["loads"]]
    if empty:   # CLOCK-128-R2: the build prunes dead branches by construction; a loadless net here is a plan error
        raise PlanError([dict(kind="empty_tree_net", name=x, detail="tree net without loads") for x in empty])
    if pin_stack:   # CLOCK-128-R7 opt-in: straight pin stacks (the default path below is unchanged)
        return _fixed_wires_stack(M, cells, nets, row_y, off, router, port_on_trunk=port_on_trunk)
    out, errs = [], []

    def track(layer, ideal, a0, a1, name, what):
        if router is None:
            return ideal, DRAWN
        c, mode, e = router.place(layer, ideal, a0, a1, name)
        last_ext[0] = e
        if c is None:
            errs.append(dict(kind="no_clock_track", name=name, detail=f"{what} {layer} ideal {ideal:.3f} span "
                             f"{min(a0, a1):.3f}..{max(a0, a1):.3f}: no legal shielded track within "
                             f"{router.max_move} um (PG / clock / shield clearance)"))
            return ideal, DRAWN
        return c, mode
    mm = router.max_move if router is not None else 0.0
    last_ext = [None]

    def trunk_ext(layer, c, lo, hi, mode, e_res, name):
        """the drawn trunk is shorter than its reservation (span widened by max_move): re-derive its shield tie
        extension on the actual span; the drawn shields must stay inside the reserved ones"""
        if router is None or mode != DRAWN or e_res is None:
            return e_res
        e = router.tie_ext(layer, c, lo, hi)
        if e is None or e > e_res + mm + 1e-6:
            errs.append(dict(kind="shield_tie", name=name, detail=f"trunk {layer} {c:.3f} {lo:.3f}..{hi:.3f}: shield "
                             "tie extension outside the reserved shield footprint"))
            return e_res
        return e
    for n in nets:
        D = xy(n["drv"])
        Ls = [(ld, xy(ld)) for ld in n["loads"]]
        dx = max(abs(p[0] - D[0]) for _, p in Ls)
        dy = max(abs(p[1] - D[1]) for _, p in Ls)
        horiz = dx >= dy
        segs, branches = [], []
        nm = n["name"]
        if horiz:
            # the trunk is reserved over its widest possible extent (drops move <= max_move)
            ty, tm = track("M8", D[1] + off, min([D[0]] + [p[0] + off for _, p in Ls]) - mm,
                           max([D[0]] + [p[0] + off for _, p in Ls]) + mm, nm, "trunk")
            te = last_ext[0]
            xs_, modes, exts = [], [], []
            for ld, p in Ls:
                if abs(p[1] - ty) > 1e-6:
                    bx, bm = track("M9", p[0] + off, ty, p[1], nm, f"drop {ld}")
                    segs.append(("M9", bx, min(ty, p[1]), bx, max(ty, p[1])))
                    modes.append(bm)
                    exts.append(last_ext[0])
                else:
                    bx = p[0] + off
                branches.append((ld, bx, p[1]))
                xs_.append(bx)
            xlo, xhi = min([D[0]] + xs_), max([D[0]] + xs_)
            if xhi > xlo:
                te = trunk_ext("M8", ty, xlo, xhi, tm, te, nm)
                segs.insert(0, ("M8", xlo, ty, xhi, ty))
                modes.insert(0, tm)
                exts.insert(0, te)
            tap0 = (D[0], ty)
        else:
            tx, tm = track("M9", D[0] + off, min([D[1]] + [p[1] + off for _, p in Ls]) - mm,
                           max([D[1]] + [p[1] + off for _, p in Ls]) + mm, nm, "trunk")
            te = last_ext[0]
            ys_, modes, exts = [], [], []
            for ld, p in Ls:
                if abs(p[0] - tx) > 1e-6:
                    by, bm = track("M8", p[1] + off, tx, p[0], nm, f"drop {ld}")
                    segs.append(("M8", min(tx, p[0]), by, max(tx, p[0]), by))
                    modes.append(bm)
                    exts.append(last_ext[0])
                else:
                    by = p[1] + off
                branches.append((ld, p[0], by))
                ys_.append(by)
            ylo, yhi = min([D[1]] + ys_), max([D[1]] + ys_)
            if yhi > ylo:
                te = trunk_ext("M9", tx, ylo, yhi, tm, te, nm)
                segs.insert(0, ("M9", tx, ylo, tx, yhi))
                modes.insert(0, tm)
                exts.insert(0, te)
            tap0 = (tx, D[1])
        out.append(dict(name=nm, drv=n["drv"], loads=n["loads"], horiz=horiz, drv_xy=D, trunk_tap=tap0,
                        branches=branches, segs=segs, **(dict(shield_modes=modes, shield_ext=exts) if router is not None else {}),
                        wire_um=round(sum(abs(s[3] - s[1]) + abs(s[4] - s[2]) for s in segs), 3)))
    if errs:
        raise PlanError(errs)
    return out

# ------------------------------------------------------------------ CLOCK-128-R7: straight pin stacks (opt-in)
# Every clock-cell pin is reached by ONE bar column (rule from CLOCK-128-R6, lanes/CLOCK-128.md 18:03): the M8 end of
# the net (trunk junction or drop end) sits exactly over the pin's M1 bar; there a VIA78 drops into an M7 riser that
# runs along the bar column (M7 is vertical) to the pin row (cell y + row/2, on the bar for R0 and MX), and a straight
# VIA67..VIA12 stack lands on the bar.  Every layer M2..M6 carries one centred rectangle (the via enclosures extended
# along the preferred direction to the LEF minimum area); M7 / M8 are the riser / trunk wires themselves.  So no layer
# steps sideways, every shape is a rectangle (RECTONLY M2-M7), and nothing of the pin access lies on M8 / M9 except
# the planned shielded legs (no M8 pad under a die PG stripe, no M9 drop under one).  The M7 riser is short
# (TREE_OFF_UM + the trunk's track move) and lies inside the partition's island window (die_trial kit --island-sites:
# no M1-M3 OBS, M7 PG cut there), so it needs no shield ("shields cut at the drop end").
#   horizontal trunk (M8 at ty): driver Y and every load A join the trunk at their bar x (junction on the trunk).
#   vertical trunk (M9 at tx): driver = M8 jog (PG-aware track, one track pair off the pin row toward the loads)
#     from the Y bar to tx; load = M8 drop (PG-aware track, one track pair off toward the driver) from tx to the A bar.
PIN_BAR_X = {f"BUFx{k}_ASAP7_75t_R": {"A": 0.027, "Y": yx}
             for k, yx in (("4", 0.348), ("6f", 0.513), ("8", 0.621), ("12f", 0.945), ("16f", 1.161), ("24", 1.593))}
# centred pad half-sizes (x, y) per layer: the larger via enclosure, extended along the preferred direction to the
# LEF AREA (asap7_tech_1x_201209.lef: M2/M3 0.000666, M4/M5 0.002, M6 0.0021875)
STACK_PAD = {"M2": (0.019, 0.009), "M3": (0.009, 0.020), "M4": (0.043, 0.012), "M5": (0.012, 0.043),
             "M6": (0.035, 0.016)}
SHORT_STACK_PAD = {"M7": (0.016, 0.036), "M8": (0.08, 0.08)}
STACK_RISER_MAX_UM = 2.5     # longest M7 riser (TREE_OFF_UM + track move) the island window is sized for


def pin_xy(cells, c, pin, row_y, buf="BUFx24_ASAP7_75t_R"):
    """(x, y) of cell c's pin stack: the M1 bar centre x, the row centre y (R0 / MX)"""
    v = cells[c]
    lib = v.get("lib", buf)
    if lib not in PIN_BAR_X:
        raise PlanError([dict(kind="no_pin_stack", name=c, detail=f"no pin-bar model for {lib}")])
    if v.get("orient", "R0") not in ("R0", "MX", "MY", "R180"):
        raise PlanError([dict(kind="no_pin_stack", name=c, detail=f"orient {v.get('orient')} not modelled")])
    bar = PIN_BAR_X[lib][pin]
    if v.get("orient") in ("MY", "R180"):
        # ASAP7 buffer footprint is the Y-bar x plus the 0.027-um edge margin.
        bar = PIN_BAR_X[lib]["Y"] + PIN_BAR_X[lib]["A"] - bar
    return round(v["x"] + bar, 4), round(v["y"] + row_y / 2, 4)


def _fixed_wires_stack(M, cells, nets, row_y, off, router, port_on_trunk=False):
    txy = {t["port"]: tuple(t["xy"]) for t in M["taps"]}
    root = tuple(M["meta"]["root_um"])
    errs, out, last_ext = [], [], [None]
    port_moves = {}
    mm = router.max_move if router is not None else 0.0

    def port_xy(p):
        return root if p == "port:root" else txy[p[5:]]

    def track(layer, ideal, a0, a1, name, what):
        if router is None:
            last_ext[0] = None
            return ideal, DRAWN
        c, mode, e = router.place(layer, ideal, a0, a1, name)
        last_ext[0] = e
        if c is None:
            errs.append(dict(kind="no_clock_track", name=name, detail=f"{what} {layer} ideal {ideal:.3f}"))
            return ideal, DRAWN
        return c, mode

    def stack(cell, pin, pxy, junction):
        r = abs(junction[1] - pxy[1])
        if r > STACK_RISER_MAX_UM + 1e-9:
            errs.append(dict(kind="no_pin_stack", name=cell, detail=f"{pin} M7 riser {r:.3f} um > "
                             f"STACK_RISER_MAX_UM {STACK_RISER_MAX_UM} (outside the island window)"))
        return dict(cell=cell, pin=pin, xy=list(pxy), riser_from=[pxy[0], junction[1]], riser_um=round(r, 4))

    for n in nets:
        nm = n["name"]
        dcell = not n["drv"].startswith("port:")
        D = pin_xy(cells, n["drv"], "Y", row_y) if dcell else port_xy(n["drv"])
        Ls = [(ld, port_xy(ld) if ld.startswith("port:") else pin_xy(cells, ld, "A", row_y)) for ld in n["loads"]]
        horiz = max(abs(p[0] - D[0]) for _, p in Ls) >= max(abs(p[1] - D[1]) for _, p in Ls)
        segs, modes, exts, branches, stacks = [], [], [], [], []

        def add(seg, mode):
            segs.append(seg)
            modes.append(mode)
            exts.append(last_ext[0])
        if horiz:
            xs_all = [D[0]] + [p[0] + (off if ld.startswith("port:") else 0.0) for ld, p in Ls]
            ty, tm = track("M8", D[1] + off, min(xs_all) - mm, max(xs_all) + mm, nm, "trunk")
            te = last_ext[0]
            xs_ = []
            if dcell:
                stacks.append(stack(n["drv"], "Y", D, (D[0], ty)))
            for ld, p in Ls:
                if ld.startswith("port:") and port_on_trunk:
                    # CLOCK-128-R8 opt-in: the leaf port sits ON the M8 trunk end (no M9 drop, no M8 jog back over
                    # the core OBS); the tap moves to (bx, ty) and is recorded in port_moves
                    bx = round(p[0] + off, 4)
                    port_moves[ld[5:]] = (bx, ty)
                    branches.append((ld, bx, ty))
                    xs_.append(bx)
                    continue
                if ld.startswith("port:"):           # port loads: as the default comb (drop one track pair off)
                    if abs(p[1] - ty) > 1e-6:
                        bx, bm = track("M9", p[0] + off, ty, p[1], nm, f"drop {ld}")
                        add(("M9", bx, min(ty, p[1]), bx, max(ty, p[1])), bm)
                    else:
                        bx = p[0] + off
                    branches.append((ld, bx, p[1]))
                    xs_.append(bx)
                    continue
                stacks.append(stack(ld, "A", p, (p[0], ty)))
                branches.append((ld, p[0], ty))
                xs_.append(p[0])
            xlo, xhi = min([D[0]] + xs_), max([D[0]] + xs_)
            if xhi > xlo:
                if router is not None and tm == DRAWN and te is not None:
                    e2 = router.tie_ext("M8", ty, xlo, xhi)
                    te = e2 if e2 is not None and e2 <= te + mm + 1e-6 else te
                segs.insert(0, ("M8", xlo, ty, xhi, ty))
                modes.insert(0, tm)
                exts.insert(0, te)
            tap0 = (D[0], ty)
        else:
            ys_all = [D[1]] + [p[1] + off for _, p in Ls]
            tx, tm = track("M9", D[0] + off, min(ys_all) - mm, max(ys_all) + mm, nm, "trunk")
            te = last_ext[0]
            yd = D[1]
            if dcell:      # driver jog one track pair off the pin row toward the loads, Y bar -> trunk
                sg = 1.0 if sum(p[1] for _, p in Ls) / len(Ls) >= D[1] else -1.0
                yd, jm = track("M8", D[1] + sg * off, D[0], tx, nm, "driver jog")
                add(("M8", min(D[0], tx), yd, max(D[0], tx), yd), jm)
                stacks.append(stack(n["drv"], "Y", D, (D[0], yd)))
            ys_ = []
            for ld, p in Ls:
                port = ld.startswith("port:")
                if port and abs(p[0] - tx) <= 1e-6:
                    by = p[1] + off
                else:
                    sg = 1.0 if port or D[1] >= p[1] else -1.0     # drop row on the trunk (driver) side
                    by, bm = track("M8", p[1] + sg * off, tx, p[0], nm, f"drop {ld}")
                    add(("M8", min(tx, p[0]), by, max(tx, p[0]), by), bm)
                branches.append((ld, p[0], by))
                ys_.append(by)
                if not port:
                    stacks.append(stack(ld, "A", p, (p[0], by)))
            ylo, yhi = min([yd] + ys_), max([yd] + ys_)
            if yhi > ylo:
                if router is not None and tm == DRAWN and te is not None:
                    e2 = router.tie_ext("M9", tx, ylo, yhi)
                    te = e2 if e2 is not None and e2 <= te + mm + 1e-6 else te
                segs.insert(0, ("M9", tx, ylo, tx, yhi))
                modes.insert(0, tm)
                exts.insert(0, te)
            tap0 = (tx, yd)
        out.append(dict(name=nm, drv=n["drv"], loads=n["loads"], horiz=horiz, drv_xy=list(D), trunk_tap=tap0,
                        branches=branches, segs=segs, pin_stack=True, stacks=stacks,
                        **(dict(shield_modes=modes, shield_ext=exts) if router is not None else {}),
                        wire_um=round(sum(abs(s[3] - s[1]) + abs(s[4] - s[2]) for s in segs), 3)))
    if errs:
        raise PlanError(errs)
    if port_on_trunk:
        for t in M["taps"]:
            if t["port"] in port_moves:
                t["xy_r7"] = list(t["xy"])
                t["xy"] = [round(v, 4) for v in port_moves[t["port"]]]
                t["port_on_trunk"] = True
    return out


# ------------------------------------------------------------------ PG-aware shielded tracks (CLOCK-128 shield lane)
# Every shielded clock segment occupies, on its layer, the clock metal (width w, centre c) plus one VSS shield stripe
# (width w) on each side one NDR space away (centre c +- off, off = w/2 + s + w/2).  Shield stripes run ext = off + w/2
# past each clock-metal end, so a drop's shields always cross its trunk's shields (shield-shield VIA89 tie) and the end
# of a wire is shielded too.  A segment is LEGAL when no same-layer shape of another net is closer than the NDR space
# (edge to edge, along and across): VDD/VDDPHY stripes, other clock nets and other wires' shields.  A VSS shield may
# touch or overlap a VSS grid stripe (same net: the stripe is then also its tie).
def shield_geom(nd):
    hw = nd["width"] / 2
    off = hw + nd["space"] + nd["width"] / 2
    return hw, off, off + nd["width"] / 2


def seg_shapes(layer, c, a0, a1, net, nd, shield, kind="tree", ext=None):
    """[(layer, net, kind, perp_lo, perp_hi, along_lo, along_hi)] of one clock segment centred on c (y for M8, x for M9)
    spanning a0..a1 along its axis, with its two shields when `shield` names the shield net (running `ext` past
    each clock-metal end; default shield_geom)."""
    hw, off, ext0 = shield_geom(nd)
    ext = ext0 if ext is None else ext
    a0, a1 = min(a0, a1), max(a0, a1)
    out = [(layer, net, kind, c - hw, c + hw, a0 - hw, a1 + hw)]
    if shield:
        out += [(layer, shield, "shield", c + s * off - hw, c + s * off + hw, a0 - ext, a1 + ext) for s in (-1, 1)]
    return out


def seg_perp(seg):
    """(layer, x0, y0, x1, y1) centre line -> (layer, centre, along_lo, along_hi)"""
    lay, x0, y0, x1, y1 = seg
    return (lay, y0, min(x0, x1), max(x0, x1)) if lay == "M8" else (lay, x0, min(y0, y1), max(y0, y1))


def pg_shapes(pg_rects):
    """die_infra.pg_rects tuples -> metal shapes (kind pg)"""
    out = []
    for net, lay, x0, y0, x1, y1 in pg_rects:
        if lay == "M8":
            out.append((lay, net, "pg", y0, y1, x0, x1))
        elif lay == "M9":
            out.append((lay, net, "pg", x0, x1, y0, y1))
    return out


class MetalIndex:
    """same-layer special-metal occupancy, binned on the across-axis coordinate"""

    def __init__(self, space, bin_um=1.0):
        self.space, self.B = space, bin_um
        self.shapes = []
        self.bins = {"M8": defaultdict(list), "M9": defaultdict(list)}

    def add(self, s):
        k = len(self.shapes)
        self.shapes.append(s)
        b = self.bins[s[0]]
        for i in range(int(math.floor(s[3] / self.B)), int(math.floor(s[4] / self.B)) + 1):
            b[i].append(k)
        return k

    def hits(self, s, first=False):
        """[(k, 'short'|'spacing')] of indexed shapes of another net closer than the space to shape s"""
        lay, net, _, plo, phi, alo, ahi = s
        sp, eps = self.space, 1e-6
        b, seen, out = self.bins[lay], set(), []
        for i in range(int(math.floor((plo - sp) / self.B)), int(math.floor((phi + sp) / self.B)) + 1):
            for k in b.get(i, ()):
                if k in seen:
                    continue
                seen.add(k)
                t = self.shapes[k]
                if t[1] == net:
                    continue
                gp = max(t[3] - phi, plo - t[4])
                ga = max(t[5] - ahi, alo - t[6])
                if gp < sp - eps and ga < sp - eps:
                    out.append((k, "short" if gp < eps and ga < eps else "spacing"))
                    if first:
                        return out
        return out


VIA_HALF = 0.02     # ASAP7 1x VIA89 cut half-size (asap7_tech_1x_201209.lef RECT -0.02 -0.02 0.02 0.02)
FLANK = "pg"        # shield mode: the two neighbouring die PG stripes are the shields (no drawn stripe)
DRAWN = "drawn"     # shield mode: two drawn VSS stripes, via-tied to the die VSS grid


def flank_gap(nd):
    """max clock-edge to PG-edge gap for a PG stripe to count as a shield: no farther than a drawn shield's far edge"""
    return nd["space"] + nd["width"]


class TrackRouter:
    """legal-by-construction track choice for shielded clock segments: the nearest routing track (actual die-kit
    make_tracks pitch/offset) within max_move of the ideal centre where EITHER (drawn) the clock metal + both drawn VSS
    shields clear every same-layer shape of another net by the NDR space, OR (pg) the clock metal alone clears them and
    a die PG stripe flanks it on both sides along its whole span within flank_gap (the PG stripes are the shields; the
    only option on a PG grid too dense for drawn stripes, e.g. KV M9 0.48 um every 0.864 um).  Chosen segments are
    reserved for the following ones."""

    def __init__(self, nd, shield, tracks, max_move=8.64, space=None, wide_merge_um=None):
        self.nd, self.shield, self.tracks, self.max_move = nd, shield, tracks, max_move
        # CLOCK-128-R8 opt-in: a drawn VSS shield may touch a same-net PG stripe only while the merged VSS shape stays
        # narrower than the layer's wide-metal spacing row (ASAP7 M8/M9 SPACINGTABLE WIDTH 0.49975 -> 0.5 um at
        # PRL >= 1.8 um); None = R7 behaviour (any overlap allowed)
        self.wide_merge_um = wide_merge_um
        self.ix = MetalIndex(nd["space"] if space is None else space)
        self.pg = MetalIndex(self.ix.space)
        self.moves, self.modes = [], defaultdict(int)
        self.vss = {"M8": [], "M9": []}     # shield-net PG stripes: (centre, along_lo, along_hi) per layer
        self.vss_c = {"M8": [], "M9": []}

    def reserve(self, shapes):
        for s in shapes:
            self.ix.add(s)
            if s[2] == "pg":
                self.pg.add(s)
                if s[1] == self.shield:
                    self.vss[s[0]].append(((s[3] + s[4]) / 2, s[5], s[6]))
                    self.vss_c[s[0]] = None

    def tie_ext(self, layer, c, a0, a1):
        """shield end extension past the clock metal so each drawn shield crosses >= 1 perpendicular shield-net grid
        stripe centre (a VIA89 tie, cut half-size VIA_HALF): shield_geom ext, or longer for a short segment; None
        when no grid stripe lies within max_move."""
        import bisect
        P = "M9" if layer == "M8" else "M8"
        if self.vss_c[P] is None:
            self.vss[P].sort()
            self.vss_c[P] = [q[0] for q in self.vss[P]]
        e0 = shield_geom(self.nd)[2]
        lo, hi = min(a0, a1), max(a0, a1)
        cs, rows = self.vss_c[P], self.vss[P]
        best = None
        for q in rows[bisect.bisect_left(cs, lo - e0 - self.max_move):bisect.bisect_right(cs, hi + e0 + self.max_move)]:
            if not (q[1] - 1e-6 <= c <= q[2] + 1e-6):
                continue
            need = max(e0, (lo - q[0]) + VIA_HALF if q[0] < lo else (q[0] - hi) + VIA_HALF if q[0] > hi else e0)
            best = need if best is None else min(best, need)
            if best <= e0:
                break
        if best is None or best > e0 + self.max_move:
            return None
        return round(max(e0, best), 4)

    def place(self, layer, ideal, a0, a1, net):
        """(centre, mode) of the nearest legal track, or (None, None)"""
        tr = self.tracks[layer]
        pitch, offs = tr["pitch_um"], tr["offset_um"]
        k0 = round((ideal - offs) / pitch)
        untied = None     # nearest legal drawn track whose shields cannot reach a grid tie (reported by the tie census)
        for d in range(int(math.ceil(self.max_move / pitch)) + 2):
            ks = [k0] if d == 0 else sorted((k0 - d, k0 + d), key=lambda k: abs(offs + k * pitch - ideal))
            for k in ks:
                c = round(offs + k * pitch, 4)
                if abs(c - ideal) > self.max_move + 1e-9:
                    continue
                e = self.tie_ext(layer, c, a0, a1)
                sh = seg_shapes(layer, c, a0, a1, net, self.nd, self.shield, ext=e)
                if self.ix.hits(sh[0], first=True):
                    continue
                if self.wide_merge_um is not None and any(
                        merged_width(self.pg, s, self.shield) >= self.wide_merge_um - 1e-9 for s in sh[1:]):
                    self.modes[f"{layer}:wide_merge_skip"] += 1
                    continue
                if not any(self.ix.hits(s, first=True) for s in sh[1:]):
                    if e is None:
                        untied = untied or (c, sh)
                        continue
                    mode = DRAWN
                elif flanked(self.pg, sh[0], flank_gap(self.nd)):
                    mode, sh, e = FLANK, sh[:1], None
                else:
                    continue
                return self._take(layer, ideal, c, mode, e, sh)
        if untied is not None:
            self.modes[f"{layer}:untied"] += 1
            return self._take(layer, ideal, untied[0], DRAWN, None, untied[1])
        return None, None, None

    def _take(self, layer, ideal, c, mode, e, sh):
        self.reserve(sh)
        self.moves.append(abs(c - ideal))
        self.modes[f"{layer}:{mode}"] += 1
        return c, mode, e


WIDE_MERGE_UM = 0.49975    # ASAP7 asap7_tech_1x_201209.lef M8/M9 SPACINGTABLE wide row (0.5 um spacing at PRL >= 1.8)


def merged_width(pg_ix, s, net):
    """across-axis width of drawn shield s merged with the same-net PG stripes it touches or overlaps along its span
    (the shape DRT applies the width-dependent spacing table to)"""
    lay, _, _, plo, phi, alo, ahi = s
    eps = 1e-6
    lo, hi, grew = plo, phi, True
    while grew:
        grew = False
        for i in range(int(math.floor((lo - 1) / pg_ix.B)), int(math.floor((hi + 1) / pg_ix.B)) + 1):
            for k in pg_ix.bins[lay].get(i, ()):
                t = pg_ix.shapes[k]
                if t[1] != net or t[6] <= alo or t[5] >= ahi:
                    continue
                if t[3] <= hi + eps and t[4] >= lo - eps and (t[3] < lo - eps or t[4] > hi + eps):
                    lo, hi, grew = min(lo, t[3]), max(hi, t[4]), True
    return hi - lo


def flanked(pg_ix, s, gap):
    """True when PG metal lies on BOTH sides of clock shape s within `gap` (edge to edge) over its whole length"""
    lay, _, _, plo, phi, alo, ahi = s
    eps = 1e-6
    for side in (-1, 1):
        lo_, hi_ = (phi, phi + gap) if side > 0 else (plo - gap, plo)
        iv, seen = [], set()
        for i in range(int(math.floor(lo_ / pg_ix.B)), int(math.floor(hi_ / pg_ix.B)) + 1):
            for k in pg_ix.bins[lay].get(i, ()):
                if k in seen:
                    continue
                seen.add(k)
                t = pg_ix.shapes[k]
                near = t[3] - phi if side > 0 else plo - t[4]
                if -eps <= near <= gap + eps and t[6] > alo and t[5] < ahi:
                    iv.append((t[5], t[6]))
        reach = alo
        for a, b in sorted(iv):
            if a > reach + eps:
                break
            reach = max(reach, b)
        if reach < ahi - eps:
            return False
    return True


def clock_shapes(segs, nd, shield):
    """metal shapes of clock segments [(layer, x0, y0, x1, y1, net, kind[, mode])] with their drawn shields (mode
    'drawn', the default) or none (mode 'pg': the die PG stripes are the shields)"""
    out = []
    for row in segs:
        lay, x0, y0, x1, y1, net, kind = row[:7]
        mode = row[7] if len(row) > 7 else DRAWN
        ext = row[8] if len(row) > 8 else None
        _, c, a0, a1 = seg_perp((lay, x0, y0, x1, y1))
        out += seg_shapes(lay, c, a0, a1, net, nd, shield if mode == DRAWN else None, kind, ext)
    return out


def tree_segs(wires):
    """fixed tree wires -> clock_shapes rows (with each segment's shield mode)"""
    n = lambda w: len(w["segs"])  # noqa: E731
    return [tuple(s_) + (w["name"], "tree", m_, e_) for w in wires
            for s_, m_, e_ in zip(w["segs"], w.get("shield_modes") or [DRAWN] * n(w), w.get("shield_ext") or [None] * n(w))]


def flank_census(pg_rects, segs, nd):
    """pg-mode segments [(layer, x0, y0, x1, y1, net, kind, 'pg')] that are NOT flanked by PG on both sides"""
    ix = MetalIndex(nd["space"])
    for s in pg_shapes(pg_rects):
        ix.add(s)
    bad = []
    for row in segs:
        if len(row) > 7 and row[7] == FLANK:
            s = clock_shapes([row[:7] + (FLANK,)], nd, None)[0]
            if not flanked(ix, s, flank_gap(nd)):
                bad.append(list(row))
    return bad


def metal_census(shapes, space, limit=200):
    """same-layer shorts / spacing violations between different nets among `shapes` (seg_shapes / pg_shapes form);
    PG-PG pairs are the PG generator's and are not counted.  Returns counts by kind pair + the first `limit` rows."""
    ix = MetalIndex(space)
    shorts, spacing, rows = defaultdict(int), defaultdict(int), []
    for s in shapes:
        for k, what in ix.hits(s):
                t = ix.shapes[k]
                if s[2] == "pg" and t[2] == "pg":
                    continue
                key = "-".join(sorted((s[2], t[2])))
                (shorts if what == "short" else spacing)[key] += 1
                if len(rows) < limit:
                    rows.append(dict(what=what, a=list(s), b=list(t)))
        ix.add(s)
    return dict(shorts=sum(shorts.values()), spacing=sum(spacing.values()), shorts_by_kind=dict(shorts),
                spacing_by_kind=dict(spacing), rows=rows, shapes=len(shapes))


def _pin(p, cells, buf, out=False):
    if p.startswith("port:"):
        return f"*P {p[5:]} {'I' if p == 'port:root' else 'O'}", p[5:]
    lib = cells[p].get("lib", buf)
    nm = f"{p}:{'Y' if out else 'A'}"
    return f"*I {nm} {'O' if out else 'I'} *D {lib}", nm


def spef(wires, cells, buf, nd, layer_rc, via_kohm, design="die_combo"):
    """SPEF of the fixed pre-routes (the routed RC IS this geometry): comb trunk + drops, pi sections <= SEG_UM,
    pin via stacks, NDR R (x rf) and C (x cf).  Terminal nodes carry no cap, so restore_clock_spef_caps is a no-op."""
    rc = {L: (r * nd["rf"], c * nd["cf"]) for L, (r, c) in layer_rc.items()}
    L = ["*SPEF \"IEEE 1481-1998\"", f"*DESIGN \"{design}\"", "*DATE \"die_clock_128\"", "*VENDOR \"OpenTallas\"",
         "*PROGRAM \"die_clock_128.py\"", "*VERSION \"1\"", "*DESIGN_FLOW \"PIN_CAP NONE\"", "*DIVIDER /",
         "*DELIMITER :", "*BUS_DELIMITER []", "*T_UNIT 1 PS", "*C_UNIT 1 FF", "*R_UNIT 1 KOHM", "*L_UNIT 1 HENRY", ""]
    for w in wires:
        nm = w["name"]
        caps, res = defaultdict(float), []
        k = [0]

        def nid():
            k[0] += 1
            return f"{nm}:{k[0]}"

        def run(a, b, layer, pa, pb):
            """chain of pi sections between named nodes pa (at a) and pb (at b) along one layer"""
            r, c = rc[layer]
            Lw = abs(b[0] - a[0]) + abs(b[1] - a[1])
            n = max(1, int(math.ceil(Lw / SEG_UM - 1e-9)))
            prev = pa
            for s in range(1, n + 1):
                cur = pb if s == n else nid()
                res.append((prev, cur, r * Lw / n))
                caps[prev] += c * Lw / n / 2
                caps[cur] += c * Lw / n / 2
                prev = cur
        conn = []
        dline, dpin = _pin(w["drv"], cells, buf, out=True)
        conn.append(dline)
        tlay, blay = ("M8", "M9") if w["horiz"] else ("M9", "M8")
        ax = 0 if w["horiz"] else 1
        # trunk breakpoints: driver tap + every drop root
        t0 = w["trunk_tap"]
        pts = {round(t0[ax], 4): nid()}
        dnode = pts[round(t0[ax], 4)]
        res.append((dpin, dnode, via_kohm[tlay]))
        drops = []
        for ld, bx, by in w["branches"]:
            q = round(bx if w["horiz"] else by, 4)
            if q not in pts:
                pts[q] = nid()
            drops.append((ld, q, (bx, by)))
        order = sorted(pts)
        for u, v in zip(order, order[1:]):
            a = (u, t0[1]) if w["horiz"] else (t0[0], u)
            b = (v, t0[1]) if w["horiz"] else (t0[0], v)
            run(a, b, tlay, pts[u], pts[v])
        for ld, q, p in drops:
            line, lpin = _pin(ld, cells, buf)
            conn.append(line)
            root = (q, t0[1]) if w["horiz"] else (t0[0], q)
            if abs(p[0] - root[0]) + abs(p[1] - root[1]) > 1e-6:
                end = nid()
                run(root, p, blay, pts[q], end)
                res.append((end, lpin, via_kohm[blay]))
            else:
                res.append((pts[q], lpin, via_kohm[tlay]))
        tot = sum(caps.values())
        L.append(f"*D_NET {nm} {tot:.6f}")
        L.append("*CONN")
        L += conn
        L.append("*CAP")
        L += [f"{i} {n} {c:.6f}" for i, (n, c) in enumerate(sorted(caps.items()), 1)]
        L.append("*RES")
        L += [f"{i} {a} {b} {r:.6f}" for i, (a, b, r) in enumerate(res, 1)]
        L.append("*END")
        L.append("")
    return "\n".join(L) + "\n"


def combo_tcl(wires, nd, shield):
    """tcl: each fixed tree net becomes a special CLOCK net with its M8/M9 SBoxes, VSS shields both sides and an
    obstruction over metal + shield spacing on that layer (no signal track within the shield spacing)."""
    hw, off, ext = shield_geom(nd)
    ob = hw + 2 * nd["space"] + nd["width"]
    L = [f"set pn [$blk findNet {shield}]", f"if {{$pn eq \"NULL\"}} {{ set pn [odb::dbNet_create $blk {shield}] }}",
         "$pn setSpecial", "$pn setSigType GROUND", "set fsw [odb::dbSWire_create $pn ROUTED]",
         "proc fwnet {nm} { global blk; set n [$blk findNet $nm]; if {$n == \"NULL\"} { error \"missing fixed clock "
         "net $nm\" }; $n setSpecial; $n setSigType CLOCK; foreach it [$n getITerms] { $it setSpecial }; "
         "return [odb::dbSWire_create $n ROUTED] }",
         "proc fw {sw L x0 y0 x1 y1 {sh 1} {ex \"\"}} { global blk l8 l9 fsw; set l [expr {$L == 8 ? $l8 : $l9}]; "
         f"set hw {hw}; set off {off}; set ob {ob}; set ext {ext}; set sw2 {nd['width'] / 2}; "
         "if {$ex ne \"\"} { set ext $ex; if {$ext + $hw > $ob} { set ob [expr {$ext + $hw}] } }; "
         "if {$L == 8} { odb::dbSBox_create $sw $l [um [expr {$x0-$hw}]] [um [expr {$y0-$hw}]] [um [expr {$x1+$hw}]] "
         "[um [expr {$y0+$hw}]] STRIPE; if {$sh} { foreach s {-1 1} { set yy [expr {$y0+$s*$off}]; odb::dbSBox_create $fsw $l "
         "[um [expr {$x0-$ext}]] [um [expr {$yy-$sw2}]] [um [expr {$x1+$ext}]] [um [expr {$yy+$sw2}]] STRIPE } }; "
         "odb::dbObstruction_create $blk $l [um [expr {$x0-$ob}]] [um [expr {$y0-$ob}]] [um [expr {$x1+$ob}]] "
         "[um [expr {$y0+$ob}]] } else { odb::dbSBox_create $sw $l [um [expr {$x0-$hw}]] [um [expr {$y0-$hw}]] "
         "[um [expr {$x0+$hw}]] [um [expr {$y1+$hw}]] STRIPE; if {$sh} { foreach s {-1 1} { set xx [expr {$x0+$s*$off}]; "
         "odb::dbSBox_create $fsw $l [um [expr {$xx-$sw2}]] [um [expr {$y0-$ext}]] [um [expr {$xx+$sw2}]] "
         "[um [expr {$y1+$ext}]] STRIPE } }; odb::dbObstruction_create $blk $l [um [expr {$x0-$ob}]] [um [expr {$y0-$ob}]] "
         "[um [expr {$x0+$ob}]] [um [expr {$y1+$ob}]] } }"]
    nseg = 0
    for w in wires:
        L.append(f"set sw [fwnet {w['name']}]")
        n_ = len(w["segs"])
        for (lay, x0, y0, x1, y1), m_, e_ in zip(w["segs"], w.get("shield_modes") or [DRAWN] * n_,
                                                 w.get("shield_ext") or [None] * n_):
            L.append(f"fw $sw {lay[1]} {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f}" +
                     (" 0" if m_ != DRAWN else f" 1 {e_:.4f}" if e_ is not None else ""))
            nseg += 1
    L.append(f"puts \"OT_FIXED_CLOCK nets {len(wires)} segs {nseg}\"")
    return L


def shield_stripes(segs, nd):
    """the drawn VSS shield stripes of clock segments [(layer, x0, y0, x1, y1)] (centre lines): one stripe on each
    side, one NDR space away, running shield_geom ext past both clock-metal ends (same geometry as combo_tcl / cmd_combo's psw).  Returns
    [(layer, x0, y0, x1, y1)] stripe centre lines (horizontal M8: y0 == y1; vertical M9: x0 == x1)."""
    hw, off, ext0 = shield_geom(nd)
    out = []
    for row in segs:
        lay, x0, y0, x1, y1 = row[:5]
        ext = row[5] if len(row) > 5 and row[5] is not None else ext0
        for s in (-1, 1):
            if lay == "M8":
                out.append(("M8", min(x0, x1) - ext, y0 + s * off, max(x0, x1) + ext, y0 + s * off))
            else:
                out.append(("M9", x0 + s * off, min(y0, y1) - ext, x0 + s * off, max(y0, y1) + ext))
    return out


def pg_grid(P, pg=None):
    """the die PG stripe rules (die.pg.grid + each PHY domain's grid on its own region, core grid cut around it, die
    phase): die_infra.pg_grid -- ONE PG model for the clock, reset and shield tools (HBM-PG 10-26)."""
    import die_infra as DI
    return DI.pg_grid(P, pg)


def shield_ties(stripes, pg_rects, w_shield, net="VSS", tile_um=50.0, tie_pitch_um=34.56):
    """12.7a electrical tie of the clock shields to the die VSS grid (COORD 07:04: no freeze evidence before it).

    stripes: shield centre lines from shield_stripes(); pg_rects: die_infra.pg_rects tuples (net, layer, x0, y0, x1, y1).
      * grid via: a VIA89 wherever a shield stripe crosses a perpendicular `net` stripe of the die grid (M8 shield x
        M9 VSS, M9 shield x M8 VSS), at the crossing centre;
      * shield-shield via: a VIA89 wherever an M8 shield crosses an M9 shield (both `net`), so a short stripe that
        crosses no grid stripe (a drop, a jog) is tied through the shield it meets;
      * a stripe is TIED when its connected shield component holds at least one grid via;
      * a SHORT is a shield stripe footprint overlapping a same-layer PG stripe of another net (VDD, VDDPHY).
    Grid ties are spaced >= tie_pitch_um along a stripe (4 grid pitches at 8.64 um), both stripe ends always tied.
    Returns dict(grid_vias=[(x, y)], shield_vias=[(x, y)], untied=[stripe idx], shorts=[(idx, net)], counts...)."""
    import bisect
    hw = w_shield / 2
    perp = {"M8": "M9", "M9": "M8"}
    # perpendicular grid stripes of `net`, as sorted centre coordinates with their extent along the other axis
    lines = {}
    for L in ("M8", "M9"):
        rows = []
        for r in pg_rects:
            if r[0] != net or r[1] != L:
                continue
            if L == "M9":       # vertical: centre x, extent y
                rows.append(((r[2] + r[4]) / 2, r[3], r[5]))
            else:
                rows.append(((r[3] + r[5]) / 2, r[2], r[4]))
        rows.sort()
        lines[L] = ([q[0] for q in rows], rows)
    same, own = {}, {}
    for L in ("M8", "M9"):
        rows = []
        for r in pg_rects:
            if r[0] == net and r[1] == L:   # a shield touching / overlapping a same-layer `net` stripe is tied by contact
                own.setdefault(L, []).append(((r[2], r[4]) if L == "M9" else (r[3], r[5])) +
                                              ((r[3], r[5]) if L == "M9" else (r[2], r[4])))
            if r[0] == net or r[1] != L:
                continue
            rows.append(((r[2], r[4]) if L == "M9" else (r[3], r[5])) + ((r[3], r[5]) if L == "M9" else (r[2], r[4]))
                        + (r[0],))
        rows.sort()
        same[L] = ([q[0] for q in rows], rows, max([q[1] - q[0] for q in rows] or [0.0]))
        orow = sorted(own.get(L, []))
        own[L] = ([q[0] for q in orow], orow, max([q[1] - q[0] for q in orow] or [0.0]))
    parent = list(range(len(stripes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    grid_vias, shorts, has_grid, used, contact = [], [], set(), set(), set()
    for k, (L, x0, y0, x1, y1) in enumerate(stripes):
        c, a, b = (y0, min(x0, x1), max(x0, x1)) if L == "M8" else (x0, min(y0, y1), max(y0, y1))
        cs, rows = lines[perp[L]]
        hit = [q for q in rows[bisect.bisect_left(cs, a):bisect.bisect_right(cs, b)] if q[1] - 1e-6 <= c <= q[2] + 1e-6]
        keep, last = [], None       # one tie per tie_pitch_um along the stripe, both ends always tied
        for i_, q in enumerate(hit):
            if last is None or q[0] - last >= tie_pitch_um - 1e-6 or i_ == len(hit) - 1:
                keep.append(q)
                last = q[0]
        for q in keep:
            grid_vias.append((q[0], c) if L == "M8" else (c, q[0]))
            used.add((perp[L], round(q[0], 4)))
            has_grid.add(k)
        lo_o, orows, owmax = own[L]
        for q in orows[bisect.bisect_left(lo_o, c - hw - owmax - 1e-6):bisect.bisect_right(lo_o, c + hw + 1e-6)]:
            if q[0] <= c + hw + 1e-6 and q[1] >= c - hw - 1e-6 and q[2] <= b + 1e-6 and q[3] >= a - 1e-6:
                has_grid.add(k)
                contact.add(k)
                used.add((L, round((q[0] + q[1]) / 2, 4)))
                break
        lo_s, srows, wmax = same[L]
        for q in srows[bisect.bisect_left(lo_s, c - hw - wmax):bisect.bisect_right(lo_s, c + hw)]:
            if q[0] < c + hw - 1e-6 and q[1] > c - hw + 1e-6 and q[2] < b - 1e-6 and q[3] > a + 1e-6:
                shorts.append((k, q[4]))
    # shield x shield crossings (M8 x M9), bucketed on a tile grid
    buck = defaultdict(list)
    for k, (L, x0, y0, x1, y1) in enumerate(stripes):
        if L != "M9":
            continue
        for t in range(int(min(y0, y1) // tile_um), int(max(y0, y1) // tile_um) + 1):
            buck[(int(x0 // tile_um), t)].append(k)
    shield_vias = set()
    for k, (L, x0, y0, x1, y1) in enumerate(stripes):
        if L != "M8":
            continue
        ty = int(y0 // tile_um)
        for tx in range(int(min(x0, x1) // tile_um), int(max(x0, x1) // tile_um) + 1):
            for v in buck.get((tx, ty), ()):
                _, vx, vy0, _, vy1 = stripes[v]
                if min(x0, x1) - 1e-6 <= vx <= max(x0, x1) + 1e-6 and min(vy0, vy1) - 1e-6 <= y0 <= max(vy0, vy1) + 1e-6:
                    shield_vias.add((round(vx, 4), round(y0, 4)))
                    parent[find(k)] = find(v)
    tied_roots = {find(k) for k in has_grid}
    untied = [k for k in range(len(stripes)) if find(k) not in tied_roots]
    gv = sorted({(round(x, 4), round(y, 4)) for x, y in grid_vias})
    return dict(grid_vias=gv, shield_vias=sorted(shield_vias), untied=untied, shorts=shorts, used_grid=used,
                stripes=len(stripes), stripes_with_grid_via=len(has_grid), stripes_grid_contact=len(contact), net=net)


def tie_tcl(ties, swire_var):
    """tcl: the VIA89 tie cuts of shield_ties() on the shield special wire `swire_var` (tech via VIA89)."""
    L = ["set v89 [$tech findVia VIA89]", "if {$v89 == \"NULL\"} { error \"tech via VIA89 missing\" }"]
    for x, y in ties["grid_vias"] + ties["shield_vias"]:
        L.append(f"odb::dbSBox_create {swire_var} $v89 [um {x:.4f}] [um {y:.4f}] STRIPE")
    L.append(f"puts \"OT_SHIELD_TIES grid {len(ties['grid_vias'])} shield {len(ties['shield_vias'])} "
             f"untied {len(ties['untied'])} shorts {len(ties['shorts'])}\"")
    return L


def grid_tcl(pg_rects, swire_var, net="VSS", used=None):
    """tcl: the die `net` grid stripes the ties land on, as special wires of the shield net (the die PG grid that the
    kit models as routing obstructions); `used` = set of (layer, centre) to emit, None = all."""
    L = []
    for r in pg_rects:
        if r[0] != net or r[1] not in ("M8", "M9"):
            continue
        c = round((r[2] + r[4]) / 2 if r[1] == "M9" else (r[3] + r[5]) / 2, 4)
        if used is not None and (r[1], c) not in used:
            continue
        L.append(f"odb::dbSBox_create {swire_var} $l{r[1][1]} [um {r[2]:.4f}] [um {r[3]:.4f}] [um {r[4]:.4f}] "
                 f"[um {r[5]:.4f}] STRIPE")
    return L


def tie_record(ties):
    ok = bool(ties["stripes"]) and not ties["untied"] and not ties["shorts"]
    return dict(vss_tied=ok, tie_net=ties["net"], shield_stripes=ties["stripes"],
                stripes_with_grid_via=ties["stripes_with_grid_via"], grid_vias=len(ties["grid_vias"]),
                stripes_grid_contact=ties.get("stripes_grid_contact", 0),
                shield_shield_vias=len(ties["shield_vias"]), untied_stripes=len(ties["untied"]),
                pg_shorts=len(ties["shorts"]), pg_short_nets=sorted({n for _, n in ties["shorts"]}),
                tie_method="VIA89 at every shield x die-VSS-stripe crossing + every M8 x M9 shield crossing; "
                           "tied = shield component holds >= 1 grid via (die_clock_128.shield_ties)")


def shield_record(wires, shield, straps, jogs, ties=None):
    mm = sum(w["wire_um"] for w in wires) / 1e3
    r = dict(net=shield, straps_shielded=straps, jogs_shielded=jogs, fixed_tree_nets=len(wires),
             fixed_tree_mm=round(mm, 1), fixed_tree_segs=sum(len(w["segs"]) for w in wires),
             grt_routed_tree_nets=0, grt_routed_tree_mm=0.0, complete=bool(shield),
             # COORD-REVIEW-20 (2) / COORD 07:04: no freeze evidence may rely on the shields until every shield stripe is
             # via-tied to the die VSS grid (vss_tied).  build records False (geometry only); combo computes the ties
             # (shield_ties) and rewrites this record with the real counts.
             vss_tied=False, freeze_evidence_ok=False,
             method="12.7a: H-tree legs, split tails, stubs and root net pre-routed as fixed special M8/M9 NDR "
                    "wires, VSS stripe both sides, obstruction over the shield spacing (die_clock_128.combo_tcl)")
    if ties is not None:
        r.update(tie_record(ties))
        r["freeze_evidence_ok"] = r["vss_tied"] and bool(shield)
    return r


# ------------------------------------------------------------------------------------------------ balance audit
def structural_audit(M, cells, nets, libs, nd, layer_rc, buf, buf_w, row_y):
    """12.8d: the tree is balanced by construction.  No measurement is read and no cell is added; the plan RC model
    gives each branching net's sibling-subtree imbalance (latest driver arrival below each load) per level."""
    r_um, c_um = wire_rc(nd, layer_rc)
    by_drv = {n["drv"]: n for n in nets}
    txy = {t["port"]: tuple(t["xy"]) for t in M["taps"]}

    def xy(p):
        if p.startswith("port:"):
            return tuple(M["meta"]["root_um"]) if p == "port:root" else txy[p[5:]]
        return _centre(cells, p, buf_w, row_y)
    arr = {}
    import sys
    sys.setrecursionlimit(100000)

    def walk(c, t, s):
        n = by_drv.get(c)
        kind = cells[c]["kind"] if c in cells else None
        if kind == "drv" or n is None:
            arr[c] = t
            return
        if kind == "stub":
            return
        a = xy(c)
        cl = 0.0
        for ld in n["loads"]:
            b = xy(ld)
            cl += c_um * (abs(a[0] - b[0]) + abs(a[1] - b[1])) + (libs[buf]["cap"] if not ld.startswith("port:") else 0)
        for ld in n["loads"]:
            b = xy(ld)
            Lw = abs(a[0] - b[0]) + abs(a[1] - b[1])
            d = _bilin(libs[buf]["delay"], s, cl) + r_um * Lw * (c_um * Lw / 2 + libs[buf]["cap"])
            so = _bilin(libs[buf]["trans"], s, cl)
            if not ld.startswith("port:"):
                walk(ld, t + d, so)
    root = by_drv["port:root"]["loads"][0]
    walk(root, 0.0, MESH_SLEW_PS)
    memo = {}

    def sub(c):
        if c in memo:
            return memo[c]
        if c in arr:
            v = (arr[c], arr[c])
        elif c not in by_drv or (c in cells and cells[c]["kind"] == "stub"):
            v = None
        else:
            vs = [sub(x) for x in by_drv[c]["loads"] if not x.startswith("port:")]
            vs = [x for x in vs if x]
            v = (min(x[0] for x in vs), max(x[1] for x in vs)) if vs else None
        memo[c] = v
        return v
    lvl = defaultdict(float)
    worst = []
    for n in nets:
        ld = [x for x in n["loads"] if not x.startswith("port:") and cells[x]["kind"] in ("node", "rep", "drv")]
        vs = [sub(x) for x in ld]
        vs = [v for v in vs if v]
        if len(vs) < 2:
            continue
        imb = max(v[1] for v in vs) - min(v[1] for v in vs)
        lv = n.get("level", 0)
        lvl[lv] = max(lvl[lv], imb)
        worst.append((imb, n["name"]))
    regs = defaultdict(list)
    for dv in M["drivers"].values():
        for c in dv["cells"]:
            if c in arr:
                regs[dv.get("region")].append(arr[c])
    return dict(method="plan RC model only (NLDM lumped + Elmore), no measurement read, no cell added (12.8d)",
                level_sibling_imbalance_max_ps={str(k): round(v, 3) for k, v in sorted(lvl.items())},
                worst_nets=[[round(a, 3), b] for a, b in sorted(worst, reverse=True)[:10]],
                region_driver_arrival_spread_ps={str(k): round(max(v) - min(v), 3) for k, v in regs.items()})


# ------------------------------------------------------------------------------------------------------- report
def gate(M, P, pairs, late, early, rng, regd, mesh_stubs, tree_D, early_rows):
    """12.4b gate number + INFO numbers + residual by cause, for one corner.  `late`/`early` are RAW tap arrivals
    (no offset add-back).  CPPR credit = range at the last common H-tree/tree node: region root for same-region pairs
    (every tap of one mesh is fed by every driver of the mesh), die root otherwise."""
    import die_clock as DC
    reg = {t["port"]: t.get("region") for t in M["taps"]}
    stub_of = {t["port"]: t["stub"] for t in M["taps"]}
    tags = {g["k"]: g["tag"] for g in (M["meta"].get("regions") or [])}

    def common(pa, pb):
        c = tags.get(reg[pa], "h") if regd and reg[pa] == reg[pb] else "h"
        while c not in rng and len(c) > 1:
            c = c[:-1]
        return rng.get(c, 0.0)

    def mesh_range(p):
        s = mesh_stubs.get(stub_of[p])
        return max(0.0, s["late"] - s["early"]) if s else 0.0
    off_ports = {r["port"] for r in early_rows}
    g_all, g_plain, g_core, info = [], [], [], []
    for x_ in pairs:
        pa, pb = x_[0], x_[1]
        v = DC.pair_clock_damage(late[pa], early[pa], late[pb], early[pb], common(pa, pb))["max_damage_ps"]
        g_all.append((v, pa, pb))
        (g_core if (pa in off_ports or pb in off_ports) else g_plain).append(v)
        mn = min(mesh_range(pa), mesh_range(pb)) if reg[pa] == reg[pb] else common(pa, pb)
        info.append(DC.pair_clock_damage(late[pa], early[pa], late[pb], early[pb], max(mn, common(pa, pb)))["max_damage_ps"])
    gmax = max([v for v, _, _ in g_all] or [0.0])
    # residual by cause, per region (max - min of late arrivals at each stage)
    res = {}
    byreg = defaultdict(list)
    for t in M["taps"]:
        byreg[t.get("region")].append(t)
    drv_reg = defaultdict(list)
    for dv in M["drivers"].values():
        drv_reg[dv.get("region")] += [tree_D[c][0] for c in dv["cells"] if c in tree_D]
    for rk, ts in byreg.items():
        ins = [mesh_stubs[t["stub"]]["late"] for t in ts if t["stub"] in mesh_stubs]
        st = [late[t["port"]] - mesh_stubs[t["stub"]]["late"] for t in ts if t["stub"] in mesh_stubs and t["port"] in late]
        plain = [late[t["port"]] for t in ts if t["port"] in late and t["port"] not in off_ports]
        res[str(rk)] = dict(
            tree_imbalance_ps=round(max(drv_reg[rk]) - min(drv_reg[rk]), 2) if drv_reg[rk] else None,
            mesh_spread_ps=round(max(ins) - min(ins), 2) if ins else None,
            stub_spread_ps=round(max(st) - min(st), 2) if st else None,
            plain_tap_spread_ps=round(max(plain) - min(plain), 2) if plain else None)
    core = dict(early_offset_taps=len(early_rows),
                max_declared_early_ps=round(max([float(r["early_ps"].get("TT") or 0) for r in early_rows] or [0]), 2),
                pairs_with_core_tap=len(g_core), core_pair_max_ps=round(max(g_core or [0]), 2))
    fails = []
    if early_rows:
        fails.append(f"{len(early_rows)} taps with a declared early offset (12.8d: restructure the core types, "
                     f"see early_offset_cores)")
    if gmax > DC.GATE_PS:
        fails.append(f"related-pair {gmax:.2f} ps > {DC.GATE_PS} (CPPR at last common tree node)")
    return dict(rule="12.8 / 12.4b", gate_ps=DC.GATE_PS, related_pair_max_ps=round(gmax, 2),
                pairs=len(g_all), pairs_over_80=sum(1 for v, _, _ in g_all if v > DC.GATE_PS),
                plain_pair_max_ps=round(max(g_plain or [0]), 2),
                info_mesh_node_cppr_max_ps=round(max(info or [0]), 2),
                info_note="mesh-node CPPR credit (min stub-input early/late range) is INFO only (12.4b)",
                residual=dict(core_latency=core, by_region=res),
                worst=[[round(v, 2), a, b] for v, a, b in sorted(g_all, reverse=True)[:10]],
                verdict="FAIL" if fails else "PASS", fails=fails)


def stage_depths(nets):
    """{cell: buffer stages from the die root port up to and including the cell} over nets.json nets (drv may be one
    name or a list for a multi-driver mesh net: the deepest driver counts)"""
    by_load = defaultdict(list)
    for n in nets:
        for d in (n["drv"] if isinstance(n["drv"], list) else [n["drv"]]):
            for ld in n["loads"]:
                by_load[ld].append(d)
    memo = {}

    def depth(c, seen=()):
        if c.startswith("port:"):
            return 0 if not by_load.get(c) else max(depth(d, seen + (c,)) for d in by_load[c])
        if c in memo:
            return memo[c]
        if c in seen or not by_load.get(c):
            raise ValueError(f"stage_depths: {c} has no driver path to the root")
        memo[c] = 1 + max(depth(d, seen + (c,)) for d in by_load[c])
        return memo[c]
    out = {}
    for n in nets:
        for c in [n["drv"]] if not isinstance(n["drv"], list) else n["drv"]:
            if not c.startswith("port:"):
                out[c] = depth(c)
        for c in n["loads"]:
            if not c.startswith("port:"):
                out[c] = depth(c)
    return out, by_load


def aocv_fold_fields(M, nets, place, nodes_arr):
    """CLK-AOCV table-mode inputs (opt-in, die_clock_mesh report --aocv-fold): per tap 'stages_from_root' (buffers
    from the die root up to the cell driving the tap) + 'xy_um'; per CPPR node ('h' = die root node ckm_n0, else the
    region root ckm_n<l>_<tag>) 'node_stages', 'node_xy_um' and the node cell's output arrival 'node_late_ps' /
    'node_early_ps' (tree STA at this corner)."""
    dep, by_load = stage_depths(nets)
    taps = {}
    for t in M["taps"]:
        drv = by_load.get(f"port:{t['port']}")
        if not drv:
            raise ValueError(f"aocv_fold_fields: tap {t['port']} has no driving clock net")
        taps[t["port"]] = dict(stages_from_root=max(dep[d] for d in drv), xy_um=[round(v, 4) for v in t["xy"]])
    nodes = {}
    for name, (late, early, _) in nodes_arr.items():
        m_ = re.match(r"ckm_n\d+_(\w+)$", name)       # lattice / H-tree node cells: ckm_n<level>_<tag>
        tag = "h" if name == "ckm_n0" else (m_.group(1) if m_ else None)
        if tag is None or name not in dep:
            continue
        v = place[name]
        nodes[tag] = dict(stages=dep[name], xy=[round(v["x"], 4), round(v["y"], 4)], late=round(late, 3),
                          early=round(early, 3))
    return taps, nodes


def write_tap_arrivals(path, M, corner, arr, rng, regd, fold=None):
    """12.4a v4.3 export for die STA: per-tap PROPAGATED arrivals on routed RC (late/early 50 %, slew) at this corner
    plus the last-common-tree-node range for CPPR.  `spine_late` / `spine_early` = {part: {tap_port: ps}} (the die_sta
    spine layout: set_clock_latency -source -late / -early per tap port).  fold (opt-in, aocv_fold_fields output) adds
    the CLK-AOCV fields; None = the file is unchanged."""
    import json
    tags = {g["k"]: g["tag"] for g in (M["meta"].get("regions") or [])}
    late, early, rows = defaultdict(dict), defaultdict(dict), []
    for t in M["taps"]:
        if t["port"] not in arr:
            continue
        lv, ev, sv = arr[t["port"]]
        late[t["part"]][t["tap"]] = round(lv, 3)
        early[t["part"]][t["tap"]] = round(ev, 3)
        node = tags.get(t.get("region"), "h") if regd else "h"
        rows.append(dict(part=t["part"], tap=t["tap"], port=t["port"], late_ps=round(lv, 3), early_ps=round(ev, 3),
                         slew_ps=round(sv, 3), region=t.get("region"), cppr_node=node,
                         **(fold[0][t["port"]] if fold else {})))
    out = dict(corner=corner, basis="routed RC (fixed-geometry tree SPEF + mesh transient + stub STA), raw (no offsets)",
               cppr="credit only at the last common tree node: region root (same region) else die root 'h'",
               cppr_node_range_ps={k: round(v, 3) for k, v in rng.items() if k == "h" or k in tags.values()},
               spine_late=late, spine_early=early, taps=rows)
    if fold:
        used = {"h"} | {r["cppr_node"] for r in rows}
        miss = sorted(used - set(fold[1]))
        if miss:
            raise ValueError(f"write_tap_arrivals --aocv-fold: no tree arrival for CPPR node(s) {miss}")
        nd = {k: v for k, v in fold[1].items() if k in used}
        out.update(node_stages={k: v["stages"] for k, v in nd.items()},
                   node_xy_um={k: v["xy"] for k, v in nd.items()},
                   node_late_ps={k: v["late"] for k, v in nd.items()},
                   node_early_ps={k: v["early"] for k, v in nd.items()},
                   aocv_fold="CLK-AOCV opt-in: stages = buffers from the die root up to and including the cell "
                             "(tap: its driving cell, node: the node cell); node_*_ps = node cell output arrival")
    Path(path).write_text(json.dumps(out) + "\n")
    return out
