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
def fixed_wires(M, cells, nets, buf_w, row_y, off=TREE_OFF_UM):
    """every tree net (root, H-tree legs/nodes/leaves, split tails, stubs) as a fixed comb pre-route: one trunk on the
    net's dominant axis (M8 horizontal / M9 vertical), offset `off` from the driver pin line, plus one perpendicular
    drop per load, offset `off` from the load pin line.  Returns [dict(name, drv, pins, segs, rc_nodes)]."""
    txy = {t["port"]: tuple(t["xy"]) for t in M["taps"]}
    root = tuple(M["meta"]["root_um"])

    def xy(p):
        if p.startswith("port:"):
            return root if p == "port:root" else txy[p[5:]]
        return _centre(cells, p, buf_w, row_y)
    empty = [n["name"] for n in nets if not n["loads"]]
    if empty:   # CLOCK-128-R2: the build prunes dead branches by construction; a loadless net here is a plan error
        raise PlanError([dict(kind="empty_tree_net", name=x, detail="tree net without loads") for x in empty])
    out = []
    for n in nets:
        D = xy(n["drv"])
        Ls = [(ld, xy(ld)) for ld in n["loads"]]
        dx = max(abs(p[0] - D[0]) for _, p in Ls)
        dy = max(abs(p[1] - D[1]) for _, p in Ls)
        horiz = dx >= dy
        segs, branches = [], []
        if horiz:
            ty = D[1] + off
            xlo, xhi = min([D[0]] + [p[0] + off for _, p in Ls]), max([D[0]] + [p[0] + off for _, p in Ls])
            if xhi > xlo:
                segs.append(("M8", xlo, ty, xhi, ty))
            for ld, p in Ls:
                branches.append((ld, p[0] + off, p[1]))
                if abs(p[1] - ty) > 1e-6:
                    segs.append(("M9", p[0] + off, min(ty, p[1]), p[0] + off, max(ty, p[1])))
            tap0 = (D[0], ty)
        else:
            tx = D[0] + off
            ylo, yhi = min([D[1]] + [p[1] + off for _, p in Ls]), max([D[1]] + [p[1] + off for _, p in Ls])
            if yhi > ylo:
                segs.append(("M9", tx, ylo, tx, yhi))
            for ld, p in Ls:
                branches.append((ld, p[0], p[1] + off))
                if abs(p[0] - tx) > 1e-6:
                    segs.append(("M8", min(tx, p[0]), p[1] + off, max(tx, p[0]), p[1] + off))
            tap0 = (tx, D[1])
        out.append(dict(name=n["name"], drv=n["drv"], loads=n["loads"], horiz=horiz, drv_xy=D, trunk_tap=tap0,
                        branches=branches, segs=segs,
                        wire_um=round(sum(abs(s[3] - s[1]) + abs(s[4] - s[2]) for s in segs), 3)))
    return out


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
    hw = nd["width"] / 2
    off = hw + nd["space"] + nd["width"] / 2
    ob = hw + 2 * nd["space"] + nd["width"]
    L = [f"set pn [$blk findNet {shield}]", f"if {{$pn eq \"NULL\"}} {{ set pn [odb::dbNet_create $blk {shield}] }}",
         "$pn setSpecial", "$pn setSigType GROUND", "set fsw [odb::dbSWire_create $pn ROUTED]",
         "proc fwnet {nm} { global blk; set n [$blk findNet $nm]; if {$n == \"NULL\"} { error \"missing fixed clock "
         "net $nm\" }; $n setSpecial; $n setSigType CLOCK; foreach it [$n getITerms] { $it setSpecial }; "
         "return [odb::dbSWire_create $n ROUTED] }",
         "proc fw {sw L x0 y0 x1 y1} { global blk l8 l9 fsw; set l [expr {$L == 8 ? $l8 : $l9}]; "
         f"set hw {hw}; set off {off}; set ob {ob}; set sw2 {nd['width'] / 2}; "
         "if {$L == 8} { odb::dbSBox_create $sw $l [um [expr {$x0-$hw}]] [um [expr {$y0-$hw}]] [um [expr {$x1+$hw}]] "
         "[um [expr {$y0+$hw}]] STRIPE; foreach s {-1 1} { set yy [expr {$y0+$s*$off}]; odb::dbSBox_create $fsw $l "
         "[um [expr {$x0-$hw}]] [um [expr {$yy-$sw2}]] [um [expr {$x1+$hw}]] [um [expr {$yy+$sw2}]] STRIPE }; "
         "odb::dbObstruction_create $blk $l [um [expr {$x0-$ob}]] [um [expr {$y0-$ob}]] [um [expr {$x1+$ob}]] "
         "[um [expr {$y0+$ob}]] } else { odb::dbSBox_create $sw $l [um [expr {$x0-$hw}]] [um [expr {$y0-$hw}]] "
         "[um [expr {$x0+$hw}]] [um [expr {$y1+$hw}]] STRIPE; foreach s {-1 1} { set xx [expr {$x0+$s*$off}]; "
         "odb::dbSBox_create $fsw $l [um [expr {$xx-$sw2}]] [um [expr {$y0-$hw}]] [um [expr {$xx+$sw2}]] "
         "[um [expr {$y1+$hw}]] STRIPE }; odb::dbObstruction_create $blk $l [um [expr {$x0-$ob}]] [um [expr {$y0-$ob}]] "
         "[um [expr {$x0+$ob}]] [um [expr {$y1+$ob}]] } }"]
    nseg = 0
    for w in wires:
        L.append(f"set sw [fwnet {w['name']}]")
        for lay, x0, y0, x1, y1 in w["segs"]:
            L.append(f"fw $sw {lay[1]} {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f}")
            nseg += 1
    L.append(f"puts \"OT_FIXED_CLOCK nets {len(wires)} segs {nseg}\"")
    return L


def shield_stripes(segs, nd):
    """the drawn VSS shield stripes of clock segments [(layer, x0, y0, x1, y1)] (centre lines): one stripe on each
    side, one NDR space away, spanning the clock metal (same geometry as combo_tcl / cmd_combo's psw).  Returns
    [(layer, x0, y0, x1, y1)] stripe centre lines (horizontal M8: y0 == y1; vertical M9: x0 == x1)."""
    hw = nd["width"] / 2
    off = hw + nd["space"] + nd["width"] / 2
    out = []
    for lay, x0, y0, x1, y1 in segs:
        for s in (-1, 1):
            if lay == "M8":
                out.append(("M8", x0 - hw, y0 + s * off, x1 + hw, y0 + s * off))
            else:
                out.append(("M9", x0 + s * off, y0 - hw, x0 + s * off, y1 + hw))
    return out


def pg_grid(P):
    """the die PG stripe rules (die.pg.grid + each PHY domain's grid limited to its rect_um), die_infra.pg_rects form."""
    pg = P.die.get("pg") or {}
    grid = [dict(g) for g in pg.get("grid") or []]
    for dm in pg.get("domains") or []:
        for g in dm.get("grid") or []:
            grid.append(dict(g, rect_um=list(dm["rect_um"])))
    return grid


def shield_ties(stripes, pg_rects, w_shield, net="VSS", tile_um=50.0):
    """12.7a electrical tie of the clock shields to the die VSS grid (COORD 07:04: no freeze evidence before it).

    stripes: shield centre lines from shield_stripes(); pg_rects: die_infra.pg_rects tuples (net, layer, x0, y0, x1, y1).
      * grid via: a VIA89 wherever a shield stripe crosses a perpendicular `net` stripe of the die grid (M8 shield x
        M9 VSS, M9 shield x M8 VSS), at the crossing centre;
      * shield-shield via: a VIA89 wherever an M8 shield crosses an M9 shield (both `net`), so a short stripe that
        crosses no grid stripe (a drop, a jog) is tied through the shield it meets;
      * a stripe is TIED when its connected shield component holds at least one grid via;
      * a SHORT is a shield stripe footprint overlapping a same-layer PG stripe of another net (VDD, VDDPHY).
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
    same = {}
    for L in ("M8", "M9"):
        rows = []
        for r in pg_rects:
            if r[0] == net or r[1] != L:
                continue
            rows.append(((r[2], r[4]) if L == "M9" else (r[3], r[5])) + ((r[3], r[5]) if L == "M9" else (r[2], r[4]))
                        + (r[0],))
        rows.sort()
        same[L] = ([q[0] for q in rows], rows, max([q[1] - q[0] for q in rows] or [0.0]))
    parent = list(range(len(stripes)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    grid_vias, shorts, has_grid, used = [], [], set(), set()
    for k, (L, x0, y0, x1, y1) in enumerate(stripes):
        c, a, b = (y0, min(x0, x1), max(x0, x1)) if L == "M8" else (x0, min(y0, y1), max(y0, y1))
        cs, rows = lines[perp[L]]
        for q in rows[bisect.bisect_left(cs, a):bisect.bisect_right(cs, b)]:
            if q[1] - 1e-6 <= c <= q[2] + 1e-6:
                grid_vias.append((q[0], c) if L == "M8" else (c, q[0]))
                used.add((perp[L], round(q[0], 4)))
                has_grid.add(k)
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
                stripes=len(stripes), stripes_with_grid_via=len(has_grid), net=net)


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


def write_tap_arrivals(path, M, corner, arr, rng, regd):
    """12.4a v4.3 export for die STA: per-tap PROPAGATED arrivals on routed RC (late/early 50 %, slew) at this corner
    plus the last-common-tree-node range for CPPR.  `spine_late` / `spine_early` = {part: {tap_port: ps}} (the die_sta
    spine layout: set_clock_latency -source -late / -early per tap port)."""
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
                         slew_ps=round(sv, 3), region=t.get("region"), cppr_node=node))
    out = dict(corner=corner, basis="routed RC (fixed-geometry tree SPEF + mesh transient + stub STA), raw (no offsets)",
               cppr="credit only at the last common tree node: region root (same region) else die root 'h'",
               cppr_node_range_ps={k: round(v, 3) for k, v in rng.items() if k == "h" or k in tags.values()},
               spine_late=late, spine_early=early, taps=rows)
    Path(path).write_text(json.dumps(out) + "\n")
    return out
