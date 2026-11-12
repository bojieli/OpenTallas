#!/usr/bin/env python3
"""INSERTION-BALANCE routed check (REACH-FIX-2 with DIE-PROTO-2, COORD 11-12): the balanced die_clock.py tree routed in
the die combo GRT, with its balance pads kept.

die_clock balances by WIRE PADS that exist only in its SPEF (serpentine on the die route) plus snake delay stages
(BUF + SNAKE_UM wire at the driver).  A router that sees only the cells loses them (HEAD g5p: 5.73 m of pads on 54,955
branches; placed root->tap Manhattan 14.8-20.0 mm).  So the routed RC of a branch is GRT geometry + its pad:

  prep  RUN OUT          OUT/ctree.v (module ctree, the expanded netlist incl. snakes), OUT/ctree_ck89.tcl (every
                         cell at its die_clock site, snakes at their driver, root + t_* pins at their xy, M9) and
                         OUT/tree.json: the clock dir mk_combo_kv.py takes beside a die_trial signal kit
  pads  RUN SPEF OUT_DIR SPEF = ot_clk_die_ctree.py build output (routed GRT RC of the clock nets, module die_ctree):
                         every branch's pad length (die_clock expand_pads: branch length - its geometric hop) is
                         added as a series NDR ladder (die_clock layer_rc) at its load pin -> OUT_DIR/ctree.spef +
                         ctree.v (die_ctree) + pad_demand.json (pad um per 100-um gcell, M8/M9: the serpentines must
                         fit beside the tree); then `die_clock.py sta OUT_DIR` times it and dieclock_arrivals.py
                         exports it for die_sta_related.
"""
import argparse
import json
import math
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_clock as DC  # noqa: E402

SEG_UM = 50.0


def expanded(run):
    T = DC.load_tree(run)
    pads = {(k, int(b)): float(v) for k, b, v in json.loads((Path(run) / "pads.json").read_text())}
    E, st = DC.expand_pads(T, pads)
    return T, E, st


def placed_hops(run, E):
    """{(net, branch): Manhattan um driver -> load} on the die_clock sites (ports: root at the root node, taps at
    their xy): what a router can realise of each branch; the rest of its electrical length is pad"""
    tree = json.loads((Path(run) / "tree.json").read_text())
    pxy = {"port:" + t["port"]: tuple(t["xy"]) for t in tree["taps"]}
    rc = E.cells.get(tree.get("root_node")) or {}
    pxy["port:root"] = (rc.get("x", 0.0), rc.get("y", 0.0))

    def xy(c):
        if c in pxy:
            return pxy[c]
        k = E.cells[c]
        return (k["x"], k["y"])
    out = {}
    for n in E.nets:
        d = xy(n["drv"] if not n["drv"].startswith("port:") else n["drv"])
        for bi, (L, layer, load, geo) in enumerate(n["branches"]):
            q = xy(load)
            out[(n["name"], bi)] = abs(d[0] - q[0]) + abs(d[1] - q[1])
    return out


def cmd_prep(a):
    run, out = Path(a.run), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.no_pads:      # realize flow: the physical tree only; balance comes from placed delay cells (realize)
        T = DC.load_tree(run)
        E, st = DC.expand_pads(T, {})
    else:
        T, E, st = expanded(run)
    DC.write_verilog(E, out / "ctree_die.v")
    v = (out / "ctree_die.v").read_text()
    v2, n = re.subn(r"\bmodule\s+die_ctree\b", "module ctree", v, count=1)
    if n != 1:
        raise SystemExit("prep: module die_ctree not found in the expanded netlist")
    (out / "ctree.v").write_text(v2)
    tree = json.loads((run / "tree.json").read_text())
    shutil.copy(run / "tree.json", out / "tree.json")
    root = E.cells.get(tree.get("root_node"), None)
    lines = []
    rx, ry = (root["x"], root["y"]) if root else tuple(tree["meta"]["root_um"])
    lines.append("place_pin -pin_name root -layer M9 -location {%.3f %.3f} -pin_size {0.04 0.32}" % (rx, ry))
    for t in tree["taps"]:
        lines.append("place_pin -pin_name %s -layer M9 -location {%.3f %.3f} -pin_size {0.04 0.32}"
                     % (t["port"], t["xy"][0], t["xy"][1]))
    for name, c in sorted(E.cells.items()):
        lines.append("place_inst -name %s -location {%.3f %.3f} -status PLACED" % (name, c["x"], c["y"]))
    (out / "ctree_ck89.tcl").write_text("\n".join(lines) + "\n")
    print(json.dumps(dict(mode="prep", cells=len(E.cells), snakes=st, taps=len(tree["taps"]), out=str(out))))
    return 0


def _units(txt):
    r = re.search(r"^\*R_UNIT\s+([\d.]+)\s+(\w+)", txt, re.M)
    c = re.search(r"^\*C_UNIT\s+([\d.]+)\s+(\w+)", txt, re.M)
    rs = {"OHM": 1e-3, "KOHM": 1.0}[r.group(2).upper()] * float(r.group(1)) if r else 1.0     # -> kohm
    cs = {"FF": 1.0, "PF": 1e3}[c.group(2).upper()] * float(c.group(1)) if c else 1.0         # -> fF
    return rs, cs


def cmd_pads(a):
    run, out = Path(a.run), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.no_pads:      # routed tree only (realize flow): just the --route-ndr pricing, no wire pads
        T = DC.load_tree(run)
        E, st = DC.expand_pads(T, {})
    else:
        T, E, st = expanded(run)
    txt = Path(a.spef).read_text()
    rs, cs = _units(txt)
    # name map (*NAME_MAP) -> resolve '*123' tokens
    nm = {}
    m = re.search(r"^\*NAME_MAP\s*\n(.*?)(?=^\*PORTS|^\*D_NET)", txt, re.M | re.S)
    if m:
        for ln in m.group(1).splitlines():
            f = ln.split()
            if len(f) == 2:
                nm[f[0]] = f[1]

    def res(tok):
        if ":" in tok:
            h, t = tok.rsplit(":", 1)
            return nm.get(h, h) + ":" + t
        return nm.get(tok, tok)

    padb = {}
    demand = defaultdict(float)
    hop = placed_hops(run, E)
    for n in E.nets:
        for bi, (L, layer, load, geo) in enumerate(n["branches"]):
            # pad = electrical length - the placed Manhattan hop the router realises (snakes sit at their driver: 0)
            p = 0.0 if a.no_pads else float(L) - hop[(n["name"], bi)]
            if p > 0.5:
                pin = load[5:] if load.startswith("port:") else load + ":A"
                # the pad's per-um RC = its branch's (die_clock write_spef: layer_rc(layer, geo, leg level))
                rcm = DC.layer_rc(layer, geo, DC.net_leg_level(E, n)) if a.pad_rc == "model" else DC.LAYER_RC[layer]
                padb[(n["name"], pin)] = (p, rcm, float(L))
                c = E.cells.get(n["drv"]) or {}
                if c:
                    demand[(layer, int(c["x"] // 100), int(c["y"] // 100))] += p
    bynet = defaultdict(list)
    for k, v in padb.items():
        bynet[k[0]].append((k, v))
    # --route-ndr: the routed geometry priced at die_clock's wire width (2W2S NDR; 4W on hops > WIDE_UM): OpenROAD
    # estimate_parasitics prices every clock wire at the 1x setRC width, which the die_clock tree was not sized for
    ndr = {}
    if a.route_ndr:
        for n in E.nets:
            lay, geo = max(((b[1], float(b[3])) for b in n["branches"]), key=lambda x: x[1])
            r, c = DC.layer_rc(lay, geo, DC.net_leg_level(E, n))
            r0, c0 = DC.LAYER_RC[lay]
            ndr[n["name"]] = (r / r0, c / c0)
    blocks = re.split(r"(?m)^(?=\*D_NET )", txt)
    outb, hit = [], 0
    for b in blocks:
        mh = re.match(r"\*D_NET\s+(\S+)\s+([\d.eE+-]+)", b)
        if not mh:
            outb.append(b)
            continue
        net = res(mh.group(1))
        if net in ndr:
            fr, fc = ndr[net]
            b = re.sub(r"(?ms)(^\*RES\s*\n)(.*?)(?=^\*END)", lambda q: q.group(1) + "\n".join(
                (" ".join(x.split()[:3] + ["%.6f" % (float(x.split()[3]) * fr)]) if len(x.split()) == 4 else x)
                for x in q.group(2).splitlines()) + "\n", b, count=1)
            b = re.sub(r"(?ms)(^\*CAP\s*\n)(.*?)(?=^\*RES)", lambda q: q.group(1) + "\n".join(
                (" ".join(x.split()[:2] + ["%.6f" % (float(x.split()[2]) * fc)]) if len(x.split()) == 3 else x)
                for x in q.group(2).splitlines()) + "\n", b, count=1)
        pins = bynet.get(net, [])
        if not pins:
            outb.append(b)
            continue
        cap_lines, res_lines = [], []
        body = b
        add_c = 0.0
        pidx = 0
        for (nn, pin), (p, (r, c), L) in pins:
            k = max(1, int(math.ceil(p / SEG_UM)))
            seg = p / k
            pidx += 1                                        # SPEF internal nodes must be net:number
            hit += 1
            # every resistor end on the load pin moves to the pad entry node (pin tokens may be name-mapped)
            sec = re.search(r"\*RES\s*\n(.*?)(?=^\*END)", body, re.M | re.S)
            if sec is None:
                raise SystemExit("pads: net %s has no *RES section" % net)
            # the pad is spliced IN FRONT OF the last resistor into the load pin (the pin via / pin stub stays at
            # the pin, as in die_clock write_spef), as pi sections of SEG_UM: X -pad- Y -via- pin
            rl, last = [], None
            for ln in sec.group(1).splitlines():
                f = ln.split()
                if len(f) == 4 and last is None and (res(f[1]) == pin or res(f[2]) == pin):
                    last = (f[2] if res(f[1]) == pin else f[1], float(f[3]))
                    continue
                rl.append(ln)
            if last is None:
                raise SystemExit("pads: net %s has no resistor into %s" % (net, pin))
            prev = last[0]
            for j in range(k):
                nxt = "%s:%d" % (net, 900000 + 1000 * (pidx - 1) + j)
                rl.append("0 %s %s %.6f" % (prev, nxt, r * seg / rs))
                cap_lines.append("0 %s %.6f" % (prev, c * seg / cs / 2))
                cap_lines.append("0 %s %.6f" % (nxt, c * seg / cs / 2))
                prev = nxt
            rl.append("0 %s %s %.6f" % (prev, pin, last[1]))
            add_c += c * p / cs
            body = body[:sec.start(1)] + "\n".join(rl) + "\n" + body[sec.end(1):]
        body = re.sub(r"(?m)^(\*CAP\s*\n)", lambda q: q.group(1) + "\n".join(cap_lines) + "\n", body, count=1)
        body = body.replace(mh.group(0), "*D_NET %s %.6f" % (mh.group(1), float(mh.group(2)) + add_c), 1)
        # renumber the *CAP / *RES entries of this net
        def renum(sec_name, s):
            mm = re.search(r"(\*%s\s*\n)(.*?)(?=^\*[A-Z])" % sec_name, s, re.M | re.S)
            if not mm:
                return s
            ls = [ln.split(None, 1) for ln in mm.group(2).splitlines() if ln.strip()]
            new = "\n".join("%d %s" % (i + 1, x[1]) for i, x in enumerate(ls)) + "\n"
            return s[:mm.start(2)] + new + s[mm.end(2):]
        body = renum("RES", renum("CAP", body))
        outb.append(body)
    (out / "ctree.spef").write_text("".join(outb))
    if a.no_pads:
        DC.write_verilog(E, out / "ctree.v")          # the physical (no-snake) netlist the SPEF belongs to
    else:
        shutil.copy(run / "ctree.v", out / "ctree.v")
    shutil.copy(run / "tree.json", out / "tree.json")
    tot = sum(v[0] for v in padb.values())
    top = sorted(demand.items(), key=lambda kv: -kv[1])[:20]
    (out / "pad_demand.json").write_text(json.dumps(dict(
        pad_um=round(tot, 1), branches=len(padb), nets_patched=hit, gcell_um=100,
        top=[[l, x * 100, y * 100, round(v, 1)] for (l, x, y), v in top]), indent=1) + "\n")
    print(json.dumps(dict(mode="pads", branches=len(padb), patched=hit, pad_um=round(tot, 1),
                          max_gcell_pad_um=round(top[0][1], 1) if top else 0.0)))
    if not a.no_pads and hit != len(padb):
        return 1
    return 0


CELL_RE = re.compile(r"^\s*(\w+)\s+(\w+)\s*\((.*)\);\s*$")


def type_rects(plan):
    """partition outlines (x0, y0, x1, y1, part, type) of a die plan json; R90/R270 swap w/h"""
    raw = json.loads(Path(plan).read_text())
    ty = raw["partition_types"]
    out = []
    for p in raw["partitions"]:
        w, h = ty[p["type"]]["outline_um"][:2]
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        x, y = p["origin_um"]
        out.append((x, y, x + w, y + h, p["name"], p["type"]))
    return out


class ChannelSites:
    """legal delay-cell sites = outside every partition outline (die channels).  snap(x, y) -> nearest channel point
    (Manhattan), searched as the 4 points just past each containing outline's edges (abutted outlines chain on), to depth 24,
    pruned by the best distance found."""
    EPS = 0.54

    def __init__(self, rects, grid=50.0):
        self.rects, self.grid, self.bins = rects, grid, defaultdict(list)
        for i, r in enumerate(rects):
            for gx in range(int(r[0] // grid), int(r[2] // grid) + 1):
                for gy in range(int(r[1] // grid), int(r[3] // grid) + 1):
                    self.bins[(gx, gy)].append(i)

    def inside(self, x, y):
        for i in self.bins.get((int(x // self.grid), int(y // self.grid)), ()):
            r = self.rects[i]
            if r[0] < x < r[2] and r[1] < y < r[3]:
                return r
        return None

    def snap(self, x, y):
        if self.inside(x, y) is None:
            return x, y, 0.0
        best, front, seen = None, [(x, y)], set()
        for _ in range(24):
            nxt = []
            for px, py in front:
                r = self.inside(px, py)
                if r is None:
                    d = abs(px - x) + abs(py - y)
                    if best is None or d < best[2]:
                        best = (px, py, d)
                    continue
                for q in ((r[0] - self.EPS, py), (r[2] + self.EPS, py), (px, r[1] - self.EPS), (px, r[3] + self.EPS)):
                    k = (round(q[0], 2), round(q[1], 2))
                    if k not in seen and (best is None or abs(q[0] - x) + abs(q[1] - y) < best[2]):
                        seen.add(k)
                        nxt.append(q)
            front = nxt
            if not front:
                break
        if best is None:
            raise ValueError("no channel site near (%.1f, %.1f)" % (x, y))
        return best


def cmd_realize(a):
    """balance realized as PLACED DELAY CELLS (CTS-style), from measured (routed) arrivals: on every branch point the
    faster kids get k = round(deficit / step) delay buffers in series (placed at the branch point), where deficit =
    slowest sibling subtree max - this kid's subtree max (late, --corner arrivals of ARR).  Netlist edits only add
    cells in front of a load; every existing cell and site is kept, so the step can iterate route -> STA -> realize.
    -> OUT/ctree.v (module ctree), OUT/ctree_ck89.tcl, OUT/tree.json, OUT/realize.json"""
    src, out = Path(a.clkdir), Path(a.out)
    if a.sites == "channel" and not a.plan:
        raise SystemExit("realize --sites channel needs --plan (partition outlines)")
    out.mkdir(parents=True, exist_ok=True)
    lines = (src / "ctree.v").read_text().splitlines()
    cells, ports = {}, set()
    for ln in lines:
        m = CELL_RE.match(ln)
        if m and m.group(1) not in ("module",):
            pins = dict(re.findall(r"\.(\w+)\((\w+)\)", m.group(3)))
            cells[m.group(2)] = (m.group(1), pins.get("A"), pins.get("Y"))
        mo = re.match(r"\s*output\s+(.*);", ln)
        if mo:
            ports |= {x.strip() for x in mo.group(1).split(",")}
    loads = defaultdict(list)
    drv = {}
    for i, (c, A, Y) in cells.items():
        if A:
            loads[A].append(i)
        if Y:
            drv[Y] = i
    arr, narr = {}, {}
    for ln in Path(a.arr).read_text().splitlines():
        f = ln.split()
        if len(f) >= 3 and f[0] == "T":
            arr[f[1]] = float(f[2])
        elif len(f) >= 3 and f[0] == "N":
            narr[f[1]] = float(f[2])
    gens = [int(m.group(1)) for m in (re.match(r"dlyg(\d+)_", c) for c in cells) if m]
    gen = 1 + max(gens, default=0)
    # step: the measured delay of one inserted cell (consecutive chain cells of earlier generations), else --step-ps
    dd = []
    for c in cells:
        m = re.match(r"(dlyg\d+_\d+_)(\d+)$", c)
        if m and int(m.group(2)) > 0:
            q = m.group(1) + str(int(m.group(2)) - 1)
            if c in narr and q in narr:
                dd.append(narr[c] - narr[q])
    step = sorted(dd)[len(dd) // 2] if dd and a.step_ps <= 0 else (a.step_ps if a.step_ps > 0 else 15.0)
    kids = defaultdict(list)          # inst -> [inst | port]
    for net, d in drv.items():
        kids[d] += [x for x in loads.get(net, []) if cells[x][2]]       # dummies (no Y) carry no tap
        if net in ports:
            kids[d].append("port:" + net)
    sub = {}

    def smax(u):
        if u in sub:
            return sub[u]
        if u.startswith("port:"):
            v = arr.get(u[5:])
        else:
            vs = [x for x in (smax(k) for k in kids.get(u, [])) if x is not None]
            v = max(vs) if vs else None
        sub[u] = v
        return v
    sys.setrecursionlimit(100000)
    root = loads["root"][0]
    smax(root)
    place = {}
    for ln in (src / "ctree_ck89.tcl").read_text().splitlines():
        m = re.match(r"place_inst -name (\S+) -location \{([\d.\-]+) ([\d.\-]+)\}", ln)
        if m:
            place[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    ins = []                                           # (parent inst, kid, k)
    stack = [root]
    while stack:
        u = stack.pop()
        ks = [k for k in kids.get(u, []) if sub.get(k) is not None]
        if len(ks) > 1:
            m = max(sub[k] for k in ks)
            for k in ks:
                n = int(math.floor((m - sub[k]) / step + 0.5))
                if n >= 1:
                    ins.append((u, k, n))
        stack += [k for k in ks if not k.startswith("port:")]
    new_cells, edits, z = [], {}, 0
    sites = ChannelSites(type_rects(a.plan)) if a.sites == "channel" else None
    moved = []
    for u, k, n in ins:
        net = cells[u][2]
        names = ["dlyg%d_%d_%d" % (gen, z, j) for j in range(n)]
        z += 1
        x, y = place.get(u, (0.0, 0.0))
        if sites is not None:                           # never inside a type: nearest die-channel point
            x, y, d = sites.snap(x, y)
            moved.append(d)
        src_net = net
        if k.startswith("port:"):                       # u drives the port net itself: u -> chain -> port
            src_net = "w_dlyg%din%d" % (gen, z)
            edits[u] = (net, src_net)
        prev = src_net
        for j, nm in enumerate(names):
            o = (k[5:] if k.startswith("port:") else "w_" + nm) if j == n - 1 else "w_" + nm
            new_cells.append((nm, prev, o, x, y))
            prev = o
        if not k.startswith("port:"):
            edits.setdefault(("load", k), (net, prev))
    # rewrite
    outl, wires = [], set()
    for ln in lines:
        m = CELL_RE.match(ln)
        if m and m.group(2) in cells:
            i = m.group(2)
            body = m.group(3)
            if ("load", i) in edits:
                o, nn = edits[("load", i)]
                body = re.sub(r"\.A\(%s\)" % re.escape(o), ".A(%s)" % nn, body)
            if i in edits:
                o, nn = edits[i]
                body = re.sub(r"\.Y\(%s\)" % re.escape(o), ".Y(%s)" % nn, body)
                wires.add(nn)
            ln = "  %s %s (%s);" % (m.group(1), i, body)
        if ln.strip() == "endmodule":
            for w in sorted(wires | {c[2] for c in new_cells if c[2] not in ports}):
                outl.append("  wire %s;" % w)
            for nm, A, Y, x, y in new_cells:
                outl.append("  %s %s (.A(%s), .Y(%s));" % (a.cell, nm, A, Y))
        outl.append(ln)
    v = "\n".join(outl) + "\n"
    v = re.sub(r"\bmodule\s+die_ctree\b", "module ctree", v, count=1)
    (out / "ctree.v").write_text(v)
    tcl = (src / "ctree_ck89.tcl").read_text().rstrip("\n").splitlines()
    tcl += ["place_inst -name %s -location {%.3f %.3f} -status PLACED" % (nm, x, y) for nm, A, Y, x, y in new_cells]
    (out / "ctree_ck89.tcl").write_text("\n".join(tcl) + "\n")
    if (src / "tree.json").is_file():
        shutil.copy(src / "tree.json", out / "tree.json")
    t = [v_ for k_, v_ in arr.items() if k_ in ports]
    rep = dict(mode="realize", arr=str(a.arr), generation=gen, step_ps=round(step, 2), step_measured=len(dd), cell=a.cell, taps=len(t),
               spread_in_ps=round(max(t) - min(t), 1) if t else None, branches=len(ins),
               delay_cells=len(new_cells), cells_before=len(cells), sites=a.sites)
    if sites is not None:
        mv = sorted(moved)
        rep.update(chains_moved=sum(1 for d in mv if d > 0), move_um_p50=round(mv[len(mv) // 2], 1) if mv else 0.0,
                   move_um_max=round(mv[-1], 1) if mv else 0.0,
                   cells_inside_types=sum(1 for c in new_cells if sites.inside(c[3], c[4]) is not None))
    (out / "realize.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(rep))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("prep")
    p.add_argument("run")
    p.add_argument("out")
    p.add_argument("--no-pads", action="store_true", help="physical tree only (realize flow)")
    p = sp.add_parser("realize")
    p.add_argument("clkdir", help="clock dir of the routed run (ctree.v module ctree, ctree_ck89.tcl)")
    p.add_argument("arr", help="routed arrivals (combo arr_<C>.txt or die_clock sta arr)")
    p.add_argument("out")
    p.add_argument("--step-ps", type=float, default=0.0,
                   help="delay per inserted cell; 0 (default) = measured on earlier generations' chains, else 15")
    p.add_argument("--cell", default="HB4xp67_ASAP7_75t_R",
                   help="delay cell (COORD 11-12: HB4xp67; BUFx24 rejected)")
    p.add_argument("--sites", choices=("branch", "channel"), default="channel",
                   help="channel (default) = never inside a partition outline (needs --plan); branch = at the branch point")
    p.add_argument("--plan", help="die plan json (partition outlines) for --sites channel")
    p = sp.add_parser("pads")
    p.add_argument("run")
    p.add_argument("spef")
    p.add_argument("out")
    p.add_argument("--pad-rc", choices=("model", "1x"), default="model",
                   help="pad wire RC per um: model = die_clock's NDR branch RC (default; exact vs die_clock SPEF), "
                        "1x = ASAP7 setRC M8/M9 as the combo GRT estimate prices routed clock wire")
    p.add_argument("--no-pads", action="store_true", help="no wire pads (physical tree netlist; with --route-ndr)")
    p.add_argument("--route-ndr", action="store_true",
                   help="scale the routed clock RC to die_clock's NDR width (2W2S R/2 C x1.1; 4W on long hops)")
    a = ap.parse_args(argv)
    return dict(prep=cmd_prep, pads=cmd_pads, realize=cmd_realize)[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
