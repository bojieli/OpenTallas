#!/usr/bin/env python3
"""RESET-RELAY-GEN-1530 (FABLE-CLOSURE-1515 lever 1, die-agnostic): reset / start legs of one bound type as a PLAN DELTA,
from the bound module and a placed geometry dump of the newest kit of that type (geom_dump.tcl, AUTO-GEOM format).

Rule: every reset sink has a position, and the leg into it is a hop (<= --reach, default 300 um, the hop cap).  The
reset tree (reset_tree.py) already bounds relay-to-relay hops; the legs it does not see are:

  form R  a soft sub-instance (or bank) of the bound module takes its reset from the leaf alias `rst_n` (= the one tap
          rst_n_t<c> nearest the outline centre) or from a far tap, so the last leg tap -> its placed flops spans the
          type (QC A4 cbx/cbn/cbf u_rrl_* -> u_u_fab_u_x_*.u_st.g_seg counters, 17-36 buffers; KV pv u_rrl_417 -> banks).
          Fix: reset.inst_taps {tap, sinks, port}: the instance port moves to the existing equal-depth tap with the
          smallest worst leg to that instance's placed reset sinks.  Every tap releases on the same cycle: 0 cycles,
          0 flops (reset_port_relays.apply_inst_taps at bind and kit-rtl).  If no tap is within --reach the instance is
          listed under needs_local_tap with its sink centre (reset.local_taps_um, applied with --local-taps; a new tap
          is a tree terminal of the same depth K, so still 0 release cycles, but it needs a re-bind).
  form L  a module-local relay (ot_rst_relay u_rstr / u_rr, g_rsreg, rst_q ...) is in no tree row and has no site, so GPL
          drops it at either end of its two legs (S81 lepe u_u_land.u_rstr at (1430.9, 8.1), 1,300 um from land; leaf
          u_vp.u_rr).  Fix: (a) its flops are seated FIRM at the L1 centre of their fanout (plan relay_sites, kit_istations
          RELAY_TCL); (b) when it is fed by a signal register (not the tree) and the leg source -> centre is over --reach,
          a sink-side relay_depth row {inst, port, side sink, D = ceil(L / reach) - 1} adds D equal-pitch stages on that
          port (KIT-RD-1, D DECLARED cycles; reset release only: rst_n is held >= 64 clocks, owner 10-29); relay_mid.tcl
          spreads u_y_xd_* stages between their now fixed ends (--stage-sites seats them on the line instead).  A
          replicated relay (REGIONS copies) seats each copy at its own fanout, the synchroniser at the copies' centre.  When the relay is tree fed, form R moves its instance to the tap
          nearest the seated relay instead (0 cycles).
          COORD 11-21: the relay is walked as a TREE bottom-up; a flop whose targets no one point reaches is SPLIT into one
          copy per k_cover cluster (relay_split, register duplication, 0 cycles); the entry chain is equal-depth stages
          (straight to the entry centre, then one branch per entry copy).  Flattened bound relays (u_u_vp_u_rr) and crr
          relay flops (u_u_crr_vsw) are groups too.  Stage sites are written by default (relay_mid left them bunched).
  form F  a reset FORWARD: a relay-stage register (ot_dp_dly / ot_dp_st / crr bit) that carries a reset and feeds a local
          relay, a crr flop or a hard-macro reset pin (geom_dump MR pin XY; KV hub_Eo face register -> core reset pin,
          S81 leaf t60 u_lpad_leafdn_i0.q[0] -> u_u_crr_vsw).  Same tree rule on that one flop, entry stages as a
          relay_depth sink row on the BITS of its own input port -- only when every bound use of the bit is a reset use.
  split   a first synchroniser stage fed by a top-level pin is never split (listed).

  python3 -I reset_leg_plan.py PLAN TYPE BOUND_SV GEOM OUT_PLAN REPORT.json [--reach 300] [--local-taps]
          [--stage-sites [--stage-key FMT]] [--no-sites]

Positions are the PLACED ones of GEOM (the newest placed kit of the type); the bound module is the one that kit was
built from (its rtl/<type>_bound.sv).  The plan delta is opt-in per type and additive; every other plan byte is kept.
Nothing is a gate: the report lists every leg over --reach before and after.  PRECHECK may read report.legs_over.
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import reset_consumers as RC  # noqa: E402
import reset_port_relays as PR  # noqa: E402

REACH_UM = 300.0
MAX_D = 16                        # schema relay_depth.D maximum (COORD 11-21: reset release legs may take > 4 stages;
                                  # rst_n is held >= 64 clocks, owner 10-29, so the release depth is free)
LOCAL = re.compile(r"^(?P<g>(?:.*?[./])?(?:u_rstr|u_rr|u_rst_relay\w*|u_rrelay\w*|g_rsreg(?:\[\d+\])?|rst_q))(?=[./\[$]|$)")
# a flattened bound-level relay instance (S81 leaf u_u_vp_u_rr) and a clock-landing reset relay flop (u_u_crr_vsw)
FLAT_LOCAL = re.compile(r"^(?P<g>u_\w*?_(?:u_rstr|u_rr|u_rst_relay\w*|u_rrelay\w*))(?=[./\[$]|$)")
RELAY_FLOP = re.compile(r"^(?P<g>(?:u_\w*?)?u_crr\w*)(?=[./])")
DATA_RELAY_MOD = re.compile(r"^(?:ot_dp_dly|ot_dp_dly_keep|ot_dp_st|ot_s81sl_crr)$")
TREE_CELL = re.compile(r"^(?:u_rrl_\d+|u_srl_\d+|u_rst_root|u_rst_in|u_rsync_t\d+|u_cland_reset\w*)(?:[./_]|$)")
# stage flop name of a relay_depth sink row (RD-LEAF-1122): the strict bind emits the stages of a plan row itself, instance
# u_y_xd_<leaf>_<port>_<k>_<s> (bind.py emit_lp; k = 0 for a reset port, one depth group), Yosys flop <inst>.q.  kit_relay_depth
# only stages rows the bind never saw (u_y_xd_<leaf>_<port>_k<row>_<s>); a D28 plan row is always bound, so the sites follow the
# bind form.  sid = the row's leaf name (bind_leaf), never the bound instance name.
STAGE_KEY = "u_y_xd_{sid}_{port}_0_{s}.q"


def bind_leaf(inst):
    """RD-LEAF-1122 (OPUS-FIX-KV-HUB-R6: D28 hub_Eo/Wo strict bind 'relay_depth ... matched no internal sink'): a relay_depth
    row names the sink by its bind leaf name, the as-built rel name that bind.py matches with sv_id(rel) and instantiates as
    u_<rel>.  The bound text this tool reads carries the instance name u_<rel>, so one leading 'u_' is dropped."""
    if not inst.startswith("u_"):
        raise ValueError(f"bound instance {inst!r} does not carry bind's u_ prefix: cannot name its leaf")
    return inst[2:]
# stage flop of a reset_pin_relay row (hard core nested below the bound instance; the RTL stage is a 1-bit ot_dp_dly chain
# named u_rst_pin_relay_<port> inside the module that holds the core, Yosys flop <inst>.u_rst_pin_relay_<port>.g_r.r[s])
NESTED_KEY = "{inst}.u_rst_pin_relay_{port}.g_r.r[{s}]"


class LegError(ValueError):
    pass


def l1(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def centre(pts):
    """L1 minimax centre (minimises the worst leg to the points)"""
    us = [p[0] + p[1] for p in pts]
    vs = [p[0] - p[1] for p in pts]
    u, v = (min(us) + max(us)) / 2, (min(vs) + max(vs)) / 2
    return ((u + v) / 2, (u - v) / 2)


def k_cover(items, reach):
    """[(key, xy)] -> clusters, each within `reach` (L1) of its own minimax centre.  In u = x + y, v = x - y an L1 ball is a
    square of side 2 * reach: strips of width 2 * reach in u, each cut greedily in v (deterministic, no seeds)"""
    side = 2 * reach
    uv = sorted(((xy[0] + xy[1], xy[0] - xy[1], k, xy) for k, xy in items))
    out, i = [], 0
    while i < len(uv):
        j = i
        while j < len(uv) and uv[j][0] <= uv[i][0] + side + 1e-9:
            j += 1
        strip = sorted(uv[i:j], key=lambda r: (r[1], r[2]))
        m = 0
        while m < len(strip):
            n = m
            while n < len(strip) and strip[n][1] <= strip[m][1] + side + 1e-9:
                n += 1
            out.append([(r[2], r[3]) for r in strip[m:n]])
            m = n
        i = j
    return out


def sv_id(s):
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s if s and not s[0].isdigit() else "n" + s


def key(nm):
    """plan relay_sites key of a dump cell name: bound prefix and Yosys cell suffix dropped"""
    return re.sub(r"^u_bound[./]", "", re.sub(r"\$_[A-Za-z0-9_]*$", "", nm.replace("\\", "")))


def top_inst(k):
    return re.split(r"[./]", k, maxsplit=1)[0]


class Geo:
    """placed netlist view: reset fanout / launch tracing through buffers and inverters only"""

    def __init__(self, D):
        self.D = D
        self.name = {c: key(v[6]) for c, v in D.cells.items()}
        self.kind = {c: v[0] for c, v in D.cells.items()}
        self.mrst = getattr(D, "extra", {}).get("macro_rst_xy", {})
        self.mrp = getattr(D, "extra", {}).get("macro_rst_pin", {})

    def sxy(self, c):
        """a sink's XY: a hard macro's reset pins (geom_dump MR) when dumped, else the cell centre"""
        if self.kind.get(c) == "M" and self.mrst.get(c):
            return centre(self.mrst[c])
        return self.xy(c)

    def xy(self, c):
        v = self.D.cells[c]
        return ((v[2] + v[4]) / 2, (v[3] + v[5]) / 2)

    def fanout(self, cells):
        """sequential / macro cells (and top pins) whose data or reset input is driven by `cells` through BUF/INV only"""
        out, seen, front = set(), set(cells), list(cells)
        while front:
            nf = []
            for u in front:
                for n in self.D.drives.get(u, []):
                    for s in self.D.nets[n][2]:
                        if s[0] == "p" or s[2]:
                            continue
                        c = s[1]
                        if c in seen:
                            continue
                        seen.add(c)
                        k = self.kind.get(c)
                        if k in ("S", "M"):
                            out.add(c)
                        elif k == "B":
                            nf.append(c)
            front = nf
        return out

    def sources(self, cells):
        """launch cells / pins feeding `cells` from outside the set, through BUF/INV only"""
        out, seen, front = set(), set(cells), list(cells)
        while front:
            nf = []
            for u in front:
                for n, is_clk in self.D.cell_in.get(u, []):
                    if is_clk:
                        continue
                    d = self.D.nets[n][1]
                    if d is None:
                        continue
                    if d[0] == "p":
                        out.add(("p", d[1]))
                        continue
                    c = d[1]
                    if c in seen:
                        continue
                    seen.add(c)
                    k = self.kind.get(c)
                    if k in ("S", "M"):
                        out.add(("i", c))
                    elif k == "B":
                        nf.append(c)
            front = nf
        return out

    def pxy(self, r):
        if r[0] == "p":
            p = self.D.pin_by_k[r[1]]
            return (float(p["x"]), float(p["y"]))
        return self.xy(r[1])


def tap_cells(G, sv):
    """{tap index: dump cell id of the relay flop driving rst_n_t<i>} from the bound module's tree instances"""
    by_name = defaultdict(list)
    for c, nm in G.name.items():
        if G.kind[c] == "S":
            by_name[top_inst(nm)].append(c)
    out = {}
    for inst, c in RC._calls(sv).items():
        q = c["ports"].get("q", (None,))[0]
        m = re.fullmatch(r"rst_n_t(\d+)", q or "")
        if m and by_name.get(inst):
            out[int(m.group(1))] = by_name[inst][0]
    return out


def consumers(sv):
    """{(inst, port): tree net} for every emitted non-tree instance input on a generated-tree reset net"""
    out = {}
    for inst, c in RC._calls(sv).items():
        if c["module"].startswith(PR.TREE_CELLS):
            continue
        for port, (expr, _lo, _hi) in c["ports"].items():
            if port in ("q", "rst_o") or not PR.TREE_NET.match(expr):
                continue
            out[(inst, port)] = expr
    return out


def local_groups(G):
    """{group key: [cell ids]} of module-local relay flops (not the kit tree)"""
    gs = defaultdict(list)
    for c, nm in G.name.items():
        if G.kind[c] != "S" or TREE_CELL.match(nm):
            continue
        m = LOCAL.match(nm)
        if m and re.search(r"[./]", m.group("g")):
            gs[m.group("g")].append(c)
            continue
        m = FLAT_LOCAL.match(nm) or RELAY_FLOP.match(nm)
        if m:
            gs[m.group("g")].append(c)
    return dict(gs)


_MEMO = {}


def calls(sv):
    k = ("calls", id(sv))
    if k not in _MEMO:
        _MEMO[k] = (sv, RC._calls(sv))
    return _MEMO[k][1]


def _widths(sv):
    k = ("w", id(sv))
    if k in _MEMO:
        return _MEMO[k][1]
    w = {}
    for m in re.finditer(r"^\s*(?:input|output)?\s*(?:wire|reg|logic)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*([A-Za-z_]\w*)\s*[;,]",
                         sv, re.M):
        w[m.group(3)] = abs(int(m.group(1)) - int(m.group(2))) + 1 if m.group(1) else 1
    _MEMO[k] = (sv, w)
    return w


def bit_of(expr, b, W):
    """the wire bit (name or name[i]) that bit b of a connection expression carries; None when not resolvable"""
    e = expr.replace(" ", "")
    if e.startswith("{") and e.endswith("}"):
        for it in reversed(e[1:-1].split(",")):
            n = _item_w(it, W)
            if n is None:
                return None
            if b < n:
                return bit_of(it, b, W)
            b -= n
        return None
    m = re.fullmatch(r"([A-Za-z_]\w*)\[(\d+):(\d+)\]", e)
    if m:
        return f"{m.group(1)}[{min(int(m.group(2)), int(m.group(3))) + b}]"
    if re.fullmatch(r"[A-Za-z_]\w*\[\d+\]", e):
        return e if b == 0 else None
    if re.fullmatch(r"[A-Za-z_]\w*", e):
        return (f"{e}[{b}]" if W.get(e, 1) > 1 else e) if b < W.get(e, 1) else None
    return None


def _item_w(it, W):
    m = re.fullmatch(r"([A-Za-z_]\w*)\[(\d+):(\d+)\]", it)
    if m:
        return abs(int(m.group(2)) - int(m.group(3))) + 1
    if re.fullmatch(r"[A-Za-z_]\w*\[\d+\]", it):
        return 1
    return W.get(it) if re.fullmatch(r"[A-Za-z_]\w*", it) else None


def fwd_entry(sv, key):
    """(instance, input port, bits, wire bit) of the relay-stage flop `key` (<inst>.q[b] / <inst>/q of an ot_dp_dly /
    ot_dp_st / crr instance in the bound module); None when the flop is not such a stage"""
    m = re.fullmatch(r"(?P<i>[A-Za-z_][\w$]*)[./](?P<p>q)(?:\[(?P<b>\d+)\])?", key)
    if not m:
        return None
    c = calls(sv).get(m.group("i"))
    if c is None or not DATA_RELAY_MOD.match(c["module"]) or "d" not in c["ports"] or "q" not in c["ports"]:
        return None
    b = int(m.group("b") or 0)
    W = _widths(sv)
    wb = bit_of(c["ports"]["q"][0], b, W)
    dw = _item_w(c["ports"]["d"][0].replace(" ", ""), W) if not c["ports"]["d"][0].strip().startswith("{") else \
        sum(_item_w(x, W) or 0 for x in c["ports"]["d"][0].replace(" ", "")[1:-1].split(","))
    return m.group("i"), "d", ([b, b] if (dw or 1) > 1 else None), wb


RESET_USE = (r"negedge\s+{t}", r"if\s*\(\s*!\s*{t}\s*\)", r"\.\w*(?:rst|reset)\w*\s*\(\s*{t}\s*\)",
             r"assign\s+\w+\s*=\s*!\s*{t}\s*;", r"^\s*(?:wire|reg|logic)\b")
RELAY_NAME = re.compile(r"crr|rly|_rr\b|rstr|rst_relay|rrelay")


def reset_only(sv, tok):
    """True when every use of the wire bit `tok` in the bound module is a reset use (async reset edge / test, a reset
    port, an inverted reset copy, or the d of a reset relay instance): staging it moves reset release only"""
    if not tok:
        return False
    if "[" not in tok and re.search(rf"^\s*(?:wire|reg|logic)\s*\[\s*0\s*:\s*0\s*\]\s*{re.escape(tok)}\s*;", sv, re.M):
        tok = tok + "[0]"                        # a [0:0] bus (KV face stations): its uses are name[0]
    t = re.escape(tok) + r"(?![\w\[])"
    relay_d = sum(1 for i, c in calls(sv).items() for p, (e, _a, _b) in c["ports"].items()
                  if p == "d" and e.replace(" ", "") in (tok, tok.replace("[0]", "")) and RELAY_NAME.search(c["module"] + " " + i))
    n = ok = 0
    for line in sv.splitlines():
        k = len(re.findall(t, line))
        if not k:
            continue
        n += k
        if any(re.search(p.format(t=t), line) for p in RESET_USE):
            ok += k
    return n > 0 and ok + relay_d >= n


def port_into(sv, inst, G, src_cells):
    """the port of bound instance `inst` that carries the group's input: the one connected to the RTL wire of a source
    relay stage (fwd_entry), else the only reset-named port that is not a tree net, else the one whose wire drives toward
    the source"""
    c = calls(sv).get(inst)
    if c is None:
        return None
    wires = set()
    for s_ in src_cells:
        fe = fwd_entry(sv, G.name[s_])
        if fe and fe[3]:
            wires |= {fe[3], fe[3] + "[0]"}
    hit = [p for p, (e, _a, _b) in c["ports"].items() if e.replace(" ", "") in wires]
    if len(hit) == 1:
        return hit[0]
    cand = [p for p, (e, _a, _b) in c["ports"].items() if re.search(r"rst|reset", p) and not PR.TREE_NET.match(e)]
    if len(cand) == 1:
        return cand[0]
    nets = {G.D.nets[n][0].replace("\\", "") for s in src_cells for n in G.D.drives.get(s, [])}
    hit = [p for p in cand if any(re.sub(r"^u_bound[./]", "", n) == c["ports"][p][0].replace(" ", "") for n in nets)]
    return hit[0] if len(hit) == 1 else None


def type_delta(tn, t, sv, D, reach=REACH_UM, local_taps=False, sites=True, stage_key=STAGE_KEY, stage_sites=True, lockup=True):
    """mutates plan type dict t; -> report"""
    G = Geo(D)
    rep = dict(type=tn, reach_um=reach, inst_taps=[], local=[], relay_depth=[], needs_local_tap=[], split=[],
               legs_over_before=0, legs_over_after=0)
    seated = {}                                      # cell id -> new xy (form L seats)
    rs_sites = {}
    rd_rows = list(t.get("relay_depth") or [])
    rs_split = []
    chains = []                                      # (src, [site keys in order], pins) of form M / N stage lines
    # ---- form L: module-local relays (u_rstr / u_rr / g_rsreg / rst_q ...), as the tree of relay flops they are.
    # Bottom-up (flops that drive outside sinks first, their drivers next): each flop's targets are its outside sinks plus
    # the copies of the relay flops it drives.  Targets within --reach of one point: the flop is seated at their L1 centre
    # (kept where it is when its leg is already <= reach).  Targets that no one point reaches: the flop is SPLIT into k
    # copies (relay_split), one per L1 cluster of radius <= reach (k_cover), each seated at its cluster centre: register
    # duplication (same D / clock / reset nets), so every sink keeps the same release depth and cycle, 0 cycles.  A flop fed
    # by a top-level pin (an asynchronous source: a first synchroniser stage) is never split.  The group's entry leg
    # (its source -> its entry flop copies) on a signal-register source gets a relay_depth sink row of D stages.
    drv_pos = {}                                     # sink cell -> XY of the (copy of the) relay flop that now drives it

    def relay_tree(g, cells, form, entry=None):
        cs = set(cells)
        fo = {c: G.fanout([c]) for c in cells}
        ext = {c: fo[c] - cs for c in cells}
        kids = {c: fo[c] & cs - {c} for c in cells}
        if not any(ext.values()):
            return
        par = defaultdict(set)
        for c in cells:
            for k_ in kids[c]:
                par[k_].add(c)
        hgt = {}

        def height(c, path=()):
            if c not in hgt:
                hgt[c] = 0 if c in path else 1 + max((height(k_, path + (c,)) for k_ in kids[c] if k_ not in path), default=-1)
            return hgt[c]
        for c in cells:
            height(c)
        entries = [c for c in cells if not par.get(c)]
        srcs = G.sources(entries or cells)
        tree_fed = any(r[0] == "i" and TREE_CELL.match(G.name[r[1]]) for r in srcs)
        sp = [G.pxy(r) for r in srcs]
        fed_moved = [drv_pos[c] for c in (entries or cells) if c in drv_pos]
        if fed_moved:                            # its source (a reset forward) was seated / split first: from its copies
            sp = sorted(set(fed_moved))
        S = centre(sp) if sp else None
        here = centre([G.xy(c) for c in cells])
        fan = set().union(*ext.values())
        e = dict(group=g, form=form, flops=len(cells), fanout=len(fan), at=[round(v, 1) for v in here],
                 centre=[round(v, 1) for v in centre([G.xy(c) for c in fan])], tree_fed=tree_fed,
                 source=[round(v, 1) for v in S] if S else None)
        copies, over_b, over_a, splits, pend = {}, 0, 0, [], []
        rd_before = len(rd_rows)
        for c in sorted(cells, key=lambda c: (hgt[c], G.name[c])):
            tg = {}
            for s in sorted(ext[c]):
                tg.setdefault(G.name[s], seated.get(s) or G.sxy(s))
            for k_ in sorted(kids[c]):
                for kk, xy in copies.get(k_, ()):
                    tg[kk] = xy
            me = G.xy(c)
            orig = [G.sxy(s) for s in ext[c] | kids[c]]
            if orig and max(l1(me, p) for p in orig) > reach:
                over_b += 1
            if not tg:
                copies[c] = [(G.name[c], me)]
                continue
            pts = list(tg.values())
            C = centre(pts)
            if max(l1(C, p) for p in pts) <= reach + 1e-6:
                copies[c] = [(G.name[c], me)] if max(l1(me, p) for p in pts) <= reach else [(G.name[c], C)]
                over_a += max(l1(copies[c][0][1], p) for p in pts) > reach + 1e-6
                continue
            if c in entries and any(r[0] == "p" for r in srcs):
                copies[c] = [(G.name[c], C)]
                over_a += 1
                rep["split"].append(dict(group=g, flop=G.name[c], unsplit="fed by a top-level pin (first synchroniser stage)"))
                continue
            cl = k_cover(sorted(tg.items()), reach)
            cc = [centre([xy for _k, xy in q]) for q in cl]
            j0 = min(range(len(cl)), key=lambda j: (l1(me, cc[j]), j))
            order = [j0] + [j for j in range(len(cl)) if j != j0]
            copies[c] = [(G.name[c] if n == 0 else f"{G.name[c]}__rs{n}", cc[j]) for n, j in enumerate(order)]
            splits.append(dict(flop=G.name[c], clones=[dict(name=f"{G.name[c]}__rs{n}", sinks=[k for k, _xy in cl[j]])
                                                       for n, j in enumerate(order) if n]))
        # entry leg: source -> entry flop copies
        ent = [xy for c in (entries or cells) for _k, xy in copies[c]]
        in_now = max((l1(G.xy(c), G.pxy(r)) for c in (entries or cells) for r in srcs), default=0.0)
        over_b += in_now > reach and not tree_fed and not fed_moved     # a forward's leg is counted by its form F row
        in_after = max((l1(q, p) for q in ent for p in sp), default=0.0)
        moved = {k: xy for c in cells for k, xy in copies[c] if k != G.name[c] or l1(xy, G.xy(c)) > 1e-6}
        e.update(copies=sum(len(v) for v in copies.values()), split_flops=len(splits), in_leg_um=round(in_now, 1))
        # the entry chain (signal-register source S -> the entry flop copies), all relay_depth stages of one sink row:
        #   Ds straight stages S -> P (P = L1 centre of the entry copies); with more than one entry copy one stage AT P, and
        #   when the copies spread over --reach from P, Lb branch levels: copy n of each level sits on the line P -> entry
        #   copy n (relay_split copies of the stage), so every entry copy sees the same stage count (equal release cycle)
        nodes0 = [(k_, xy) for c in (entries or cells) for k_, xy in copies[c]]
        ent = [xy for _k, xy in nodes0]
        P = centre(ent) if ent else None
        multi = len(ent) > 1
        r_e = max((l1(P, q) for q in ent), default=0.0)
        Lb = max(0, math.ceil(r_e / reach - 1e-9) - 1) if multi else 0
        Ds = max(0, math.ceil(l1(S, P) / reach - 1e-9) - 1) if (S is not None and P is not None) else 0
        Dn = Ds + (1 + Lb if multi else 0)
        bits = None
        if not tree_fed and S is not None and Dn > 0 and in_after > reach:
            if entry:
                inst, port, bits = entry
            else:
                inst = top_inst(g)
                port = port_into(sv, inst, G, [r[1] for r in srcs if r[0] == "i"])
            if port is None:
                e["relay_depth"] = "unresolved port"
            elif Dn > MAX_D:
                e["relay_depth"] = f"needs D {Dn} > {MAX_D}"
            else:
                k = len(rd_rows)
                row = dict(inst=bind_leaf(inst), port=port, side="sink", D=Dn, path_um=round(in_after, 1),
                           note=f"RESET-RELAY-GEN-1530 form {form}: {g} fed from {e['source']}, seated at its fanout"
                                + (f", stage at the entry centre + {Lb} branch level(s) x {len(ent)}" if multi else ""))
                if bits:
                    row["bits"] = bits
                row.update(lockup=True) if lockup else None
                rd_rows.append(row)
                rep["relay_depth"].append(dict(row, over_cap=False))
                skey = [stage_key.format(sid=sv_id(bind_leaf(inst)), port=port, k=k, s=s_) for s_ in range(Dn)]
                if stage_sites or multi:
                    for s_ in range(Ds):
                        f = (s_ + 1) / (Ds + 1)
                        rs_sites[skey[s_]] = [round(S[0] + (P[0] - S[0]) * f, 3), round(S[1] + (P[1] - S[1]) * f, 3)]
                hops = [l1(S, P) / (Ds + 1)] if Ds or not multi else [l1(S, P)]
                if multi:
                    rs_sites[skey[Ds]] = [round(P[0], 3), round(P[1], 3)]
                    prev = [P] * len(ent)
                    for li in range(1, Lb + 1):
                        s_ = Ds + li
                        names = [skey[s_] if n == 0 else f"{skey[s_]}__rs{n}" for n in range(len(ent))]
                        pos = [(P[0] + (q[0] - P[0]) * li / (Lb + 1), P[1] + (q[1] - P[1]) * li / (Lb + 1)) for q in ent]
                        for nm, xy in zip(names, pos):
                            rs_sites[nm] = [round(xy[0], 3), round(xy[1], 3)]
                        hops += [l1(a_, b_) for a_, b_ in zip(prev, pos)]
                        prev = pos
                        # copy n drives copy n of the next level (or entry copy n after the last level)
                        nxt = ([f"{skey[s_ + 1]}__rs{n}" if n else skey[s_ + 1] for n in range(len(ent))] if li < Lb
                               else [k_ for k_, _xy in nodes0])
                        pend.append(dict(flop=skey[s_], clones=[dict(name=names[n], sinks=[nxt[n]])
                                                                for n in range(1, len(ent))]))
                    hops += [l1(a_, b_) for a_, b_ in zip(prev, ent)]
                in_after = max(hops)
        over_a += in_after > reach + 1e-6 and not tree_fed
        rep["legs_over_before"] += over_b
        rep["legs_over_after"] += over_a
        for c in cells:                          # who drives each outside sink now (form L reads it for forwards)
            cl_ = next((x for x in splits if x["flop"] == G.name[c]), None)
            idx = {k_: n + 1 for n, x in enumerate(cl_["clones"]) for k_ in x["sinks"]} if cl_ else {}
            for s in ext[c]:
                drv_pos[s] = copies[c][idx.get(G.name[s], 0)][1]
        if not moved and not e.get("relay_depth") and not pend and len(rd_rows) == rd_before:
            return
        for c in cells:
            if copies[c][0][0] in moved:
                seated[c] = copies[c][0][1]
        if sites:
            for k_, xy in moved.items():
                rs_sites[k_] = [round(xy[0], 3), round(xy[1], 3)]
        rs_split.extend(splits + pend[::-1])
        e.update(seated=len(moved), in_leg_after_um=round(in_after, 1), legs_over_before=over_b, legs_over_after=over_a)
        rep["local"].append(e)

    # ---- form F: reset FORWARDS.  A signal register that carries a reset (an S81 lane-pad bit leafdn_i0_q[0], a KV face
    # register into a hard-core reset pin) and drives a local relay, a crr relay flop or a hard-macro reset pin: the same
    # tree rule on that one flop (seat at its fanout, split per cluster), its entry chain as relay_depth stages on the bits
    # of its own input port -- only when every use of that bit is a reset use (reset_only), else seated / split only.
    lg = local_groups(G)
    in_g = {c for cs_ in lg.values() for c in cs_}
    cand = set()
    probe = [cs_ for cs_ in lg.values()] + [[c] for c in G.mrst]
    for cs_ in probe:
        for r in G.sources(cs_):
            c = r[1] if r[0] == "i" else None
            if c is not None and G.kind.get(c) == "S" and c not in in_g and not TREE_CELL.match(G.name[c]) \
                    and not G.name[c].startswith("u_y_xd_"):
                cand.add(c)
    for c in sorted(cand, key=lambda c: G.name[c]):
        fe = fwd_entry(sv, G.name[c])
        if fe is None or not reset_only(sv, fe[3]):
            continue                             # not a reset-only relay stage: a data register keeps its placement
        relay_tree(G.name[c], [c], "F", entry=fe[:3])
    # ---- form L: module-local relays (and crr relay flops), after the forwards that feed them
    for g, cells in sorted(lg.items()):
        relay_tree(g, cells, "L")
    # ---- form M: a reset forward into a HARD-CORE reset pin (KV hub_Eo u_bin_i_host_die_rst_n -> u_astk_EN, -747 ps).
    # The leg ends at the core's reset pins (geom_dump MR); when it is over --reach every reset-named port of the core on
    # that wire gets a relay_depth sink row of D = ceil(L / reach) - 1 stages, sited evenly on the line (reset release
    # only: the other sinks of the bit, e.g. an outward forward lane, keep their latency).
    cl_ = calls(sv)
    nested = []
    for m in sorted(G.mrst):
        inst = G.name[m]
        c = cl_.get(inst)
        if c is None:
            if re.search(r"[./]", inst):             # form N: a hard core nested below a bound instance (any depth)
                nested.append(m)
            continue
        rports = {p: e.replace(" ", "") for p, (e, _a, _b) in c["ports"].items() if re.search(r"rst|reset", p, re.I)}
        if not rports:
            continue
        pins = G.mrst[m]
        T = centre(pins)
        for r in sorted(G.sources([m])):
            if r[0] != "i" or G.kind.get(r[1]) != "S":
                continue
            fe = fwd_entry(sv, G.name[r[1]])
            if not fe or not fe[3]:
                continue
            ports = sorted(p for p, e in rports.items() if e in (fe[3], fe[3] + "[0]"))
            if not ports:
                continue
            src = drv_pos.get(m) or seated.get(r[1]) or G.xy(r[1])
            L = max(l1(src, q) for q in pins)
            if L <= reach:
                continue
            rep["legs_over_before"] += 1

            def worst(D_):                       # every hop of D_ even stages src -> T, then the last stage -> each pin
                last_ = (src[0] + (T[0] - src[0]) * D_ / (D_ + 1), src[1] + (T[1] - src[1]) * D_ / (D_ + 1))
                return max([l1(src, T) / (D_ + 1)] + [l1(last_, q) for q in pins])
            Dn = math.ceil(L / reach - 1e-9) - 1
            while worst(Dn) > reach + 1e-6 and Dn <= MAX_D:
                Dn += 1
            e = dict(group=f"{inst} <- {G.name[r[1]]}", form="M", flops=1, fanout=len(ports), at=[round(v, 1) for v in src],
                     centre=[round(v, 1) for v in T], tree_fed=False, source=[round(v, 1) for v in src], in_leg_um=round(L, 1))
            if Dn > MAX_D:
                e["relay_depth"] = f"needs D {Dn} > {MAX_D}"
                rep["legs_over_after"] += 1
                rep["local"].append(e)
                continue
            for port in ports:
                k = len(rd_rows)
                row = dict(inst=bind_leaf(inst), port=port, side="sink", D=Dn, path_um=round(L, 1),
                           note=f"RESET-RELAY-GEN-1530 form M: {G.name[r[1]]} -> hard-core reset pin {inst}.{port}")
                row.update(lockup=True) if lockup else None
                rd_rows.append(row)
                rep["relay_depth"].append(dict(row, over_cap=False))
                if sites and stage_sites:
                    chains.append((src, [stage_key.format(sid=sv_id(bind_leaf(inst)), port=port, k=k, s=s_) for s_ in range(Dn)], pins))
                    for s_ in range(Dn):
                        f = (s_ + 1) / (Dn + 1)
                        rs_sites[stage_key.format(sid=sv_id(bind_leaf(inst)), port=port, k=k, s=s_)] = [
                            round(src[0] + (T[0] - src[0]) * f, 3), round(src[1] + (T[1] - src[1]) * f, 3)]
            after = worst(Dn)
            rep["legs_over_after"] += after > reach + 1e-6
            e.update(in_leg_after_um=round(after, 1), ports=ports, D=Dn)
            rep["local"].append(e)
    # ---- form N: hard cores NESTED below a bound instance (bk_sel u_core.u_sel.g_q[0].u_q, ...; reset pins 1.0-1.65 mm from the
    # tap).  The leg is the reset source flop (its placed copy / seat) -> every reset-named pin of the core (geom_dump MR);
    # D = ceil(L / reach) - 1, raised until every hop incl. last stage -> each pin is <= reach.  Cores that share a top-level
    # instance get the SAME D (the largest): a nested core group must release together (OPUS-FIX-S81-BKSEL-R4: all 7 +6).
    # Rows go to t.reset_pin_relay (bind has no call to stage: the RTL stage is the consumer's, as in OT_BKSEL_L4 RRD) and
    # the stage sites to relay_sites under nested_key.
    nrows = []
    for m in nested:
        inst = G.name[m]
        pins = G.mrst[m]
        T = centre(pins)
        best = None
        for r in sorted(G.sources([m])):
            if r[0] != "i" or G.kind.get(r[1]) != "S":
                continue
            src = drv_pos.get(m) or seated.get(r[1]) or G.xy(r[1])
            L = max(l1(src, q) for q in pins)
            if best is None or L > best[0]:
                best = (L, src, r[1])
        if best is not None:
            nrows.append((m, inst, pins, T) + best)
    over_grp = {top_inst(x[1]) for x in nrows if x[4] > reach}
    nrows = [x for x in nrows if top_inst(x[1]) in over_grp]     # a group with one long leg: every core gets the stages
    rep["legs_over_before"] += sum(x[4] > reach for x in nrows)
    if nrows:
        def worst_n(src, T, pins, D_):
            last_ = (src[0] + (T[0] - src[0]) * D_ / (D_ + 1), src[1] + (T[1] - src[1]) * D_ / (D_ + 1))
            return max([l1(src, T) / (D_ + 1)] + [l1(last_, q) for q in pins])
        need = {}
        for m, inst, pins, T, L, src, sc in nrows:
            Dn = max(1, math.ceil(L / reach - 1e-9) - 1) if L > reach else 1
            while worst_n(src, T, pins, Dn) > reach + 1e-6 and Dn <= MAX_D:
                Dn += 1
            need[m] = Dn
        grp = defaultdict(int)
        for m, inst, *_ in nrows:
            grp[top_inst(inst)] = max(grp[top_inst(inst)], need[m])
        prows = []
        for m, inst, pins, T, L, src, sc in nrows:
            Dn = min(grp[top_inst(inst)], MAX_D)
            ports = sorted({p for p, _x, _y in G.mrp.get(m, [])}) or ["rst_n"]
            after = worst_n(src, T, pins, Dn)
            e = dict(group=inst, form="N", flops=Dn * len(ports), fanout=len(pins), at=[round(v, 1) for v in src],
                     centre=[round(v, 1) for v in T], tree_fed=False, source=[round(v, 1) for v in src], in_leg_um=round(L, 1),
                     in_leg_after_um=round(after, 1), ports=ports, D=Dn, D_own=need[m], src=G.name[sc])
            if need[m] > MAX_D:
                e["relay_depth"] = f"needs D {need[m]} > {MAX_D}"
            rep["legs_over_after"] += after > reach + 1e-6
            rep["local"].append(e)
            prows.append(dict(inst=inst, ports=ports, D=Dn, path_um=round(L, 1), hop_um=round(after, 1), src=G.name[sc], **({"lockup": True} if lockup else {}),
                              note=f"RESET-RELAY-GEN-R2 form N: {G.name[sc]} -> hard-core reset pins of {inst}"))
            if sites and stage_sites:
                for port in ports:
                    chains.append((src, [NESTED_KEY.format(inst=inst, port=port, s=s_) for s_ in range(Dn)], pins))
                    for s_ in range(Dn):
                        f = (s_ + 1) / (Dn + 1)
                        rs_sites[NESTED_KEY.format(inst=inst, port=port, s=s_)] = [
                            round(src[0] + (T[0] - src[0]) * f, 3), round(src[1] + (T[1] - src[1]) * f, 3)]
        have = [r for r in (t.get("reset_pin_relay") or []) if r["inst"] not in {x["inst"] for x in prows}]
        t["reset_pin_relay"] = have + prows
        rep["reset_pin_relay"] = prows
        rep["added_reset_cycles_nested"] = max(r["D"] for r in prows)
    # ---- form R: tree-fed instances / banks
    taps = tap_cells(G, sv)
    txy = {i: G.xy(c) for i, c in taps.items()}
    leaf = PR.LEAF.findall(sv)
    cons = consumers(sv)
    if txy and len(leaf) == 1 and cons:
        by_inst = defaultdict(list)
        for (inst, port), net in cons.items():
            by_inst[inst].append((port, net))
        sinks_of = defaultdict(set)                  # inst -> placed reset sink cells reached from any tap
        on_tap = {}                                  # sink cell -> the tap that drives it in the PLACED netlist
        for i, c in sorted(taps.items()):
            for s in G.fanout([c]):
                if G.kind.get(s) == "M":         # a hard core: its reset PIN, not the macro centre, is the sink (KIT-RD-1 class);
                    continue                     # cbx proof: u_t30 moved by its centre went -296 -> -763 ps
                ti = top_inst(G.name[s])
                if ti in by_inst:
                    sinks_of[ti].add(s)
                    on_tap.setdefault(s, i)
        rows = defaultdict(list)
        lt = list((t.get("reset") or {}).get("local_taps_um") or [])
        for inst in sorted(by_inst):
            ss = sorted(sinks_of.get(inst, ()))
            pts = [seated.get(s) or G.xy(s) for s in ss]
            if not pts:
                continue
            for port, net in by_inst[inst]:
                m = PR.TREE_NET.match(net)
                cur = int(m.group(1)) if m.group(1) is not None else int(leaf[0])
                if cur not in txy:
                    continue
                # the leg as placed: from the tap each sink really hangs on (reset_taps.tcl re-points FIRM flops itself)
                now = max(l1(txy[on_tap.get(s, cur)], p) for s, p in zip(ss, pts))
                if now <= reach:
                    continue
                rep["legs_over_before"] += 1
                best = min(txy, key=lambda i: (max(l1(txy[i], p) for p in pts), i))
                after = max(l1(txy[best], p) for p in pts)
                e = dict(inst=inst, port=port, sinks=len(pts), tap_rtl=cur,
                         tap_was=sorted({on_tap.get(s, cur) for s in ss}), leg_was_um=round(now, 1), tap=best,
                         leg_um=round(after, 1))
                if after > reach:
                    C = centre(pts)
                    e["centre"] = [round(C[0], 1), round(C[1], 1)]
                    rep["needs_local_tap"].append(e)
                    if local_taps and [round(C[0], 3), round(C[1], 3)] not in lt:
                        lt.append([round(C[0], 3), round(C[1], 3)])
                if best != cur and after < now:
                    rows[(best, port)].append(inst)
                    rep["inst_taps"].append(e)
                rep["legs_over_after"] += min(after, now) > reach
        if rows:
            have = list((t.get("reset") or {}).get("inst_taps") or [])
            taken = {(s, r.get("port", "rst_n")) for r in have for s in r["sinks"]}
            for (tap, port), ss in sorted(rows.items()):
                ss = [s for s in ss if (s, port) not in taken]
                if ss:
                    r = dict(tap=tap, sinks=ss)
                    if port != "rst_n":
                        r["port"] = port
                    have.append(r)
            t.setdefault("reset", {})["inst_taps"] = have
        if local_taps and lt != list((t.get("reset") or {}).get("local_taps_um") or []):
            t.setdefault("reset", {})["local_taps_um"] = lt
    elif cons:
        rep["form_r_skipped"] = "no generated reset-tree leaf alias / no placed tap relay found"
    # ---- legal sites (RESET-RELAY-GEN-R2 11-21, S81-DIE-R4 cl0cd90c0e): every relay / stage site is snapped to the nearest
    # legal site (reset_tree._free: outside the hard cores grown by CLEAR_UM, with a row-high / cell-wide free run), then the
    # form M / N stage lines are re-checked hop by hop
    if rs_sites:
        legalise(G, rs_sites, chains, reach, rep)
    if rd_rows != list(t.get("relay_depth") or []):
        t["relay_depth"] = rd_rows
    if rs_sites:
        merged = dict(t.get("relay_sites") or {})
        merged.update(rs_sites)
        t["relay_sites"] = dict(sorted(merged.items()))
    if rs_split:
        have = [r for r in (t.get("relay_split") or []) if r["flop"] not in {x["flop"] for x in rs_split}]
        t["relay_split"] = have + rs_split
    rep["relay_split"] = rs_split
    rep["relay_sites"] = len(rs_sites)
    rep["added_reset_cycles"] = max([r["D"] for r in rep["relay_depth"]] + [rep.get("added_reset_cycles_nested", 0)], default=0)
    return rep


def legalise(G, rs_sites, chains, reach, rep):
    import reset_tree as RT
    c = RT.CLEAR_UM
    boxes = [(v[2] - c, v[3] - c, v[4] + c, v[5] + c) for k_, v in G.D.cells.items() if v[0] == "M"]
    die = getattr(G.D, "die", None)
    rep["site_snaps"] = []
    if not boxes or not die:
        return
    snapped = {}
    for k_, p in sorted(rs_sites.items()):
        q = RT.push_off((float(p[0]), float(p[1])), boxes, tuple(die))
        if (round(q[0], 3), round(q[1], 3)) != (round(float(p[0]), 3), round(float(p[1]), 3)):
            snapped[k_] = [round(q[0], 3), round(q[1], 3)]
            rep["site_snaps"].append(dict(site=k_, was=[round(float(p[0]), 1), round(float(p[1]), 1)], now=snapped[k_],
                                          moved_um=round(l1(p, q), 1)))
    rs_sites.update(snapped)
    for src, keys, pins in chains:
        if not any(k_ in snapped for k_ in keys):
            continue
        pts = [src] + [tuple(rs_sites[k_]) for k_ in keys]
        hop = max([l1(a, b) for a, b in zip(pts, pts[1:])] + [l1(pts[-1], q) for q in pins])
        was = max([l1(a, b) for a, b in zip(pts, pts[1:])])
        rep.setdefault("snap_hop_um", []).append(dict(first=keys[0], hop_um=round(hop, 1)))
        if hop > reach + 1e-6:
            rep["legs_over_after"] += 1


def dumper(rb, raw):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, indent=1), lambda p: json.dumps(p, indent=2),
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(raw).encode() == rb:
            return f
    return lambda p: json.dumps(p, indent=1, ensure_ascii=False) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for a in ("plan", "type", "bound_sv", "geom", "out_plan", "report"):
        ap.add_argument(a)
    ap.add_argument("--reach", type=float, default=REACH_UM)
    ap.add_argument("--local-taps", action="store_true", help="also write reset.local_taps_um for instances no tap reaches")
    ap.add_argument("--no-sites", action="store_true", help="no relay_sites rows (rows only)")
    ap.add_argument("--stage-key", default=STAGE_KEY)
    ap.add_argument("--no-lockup", dest="lockup", action="store_false",
                    help="same-edge stages (default since 11-21: a lockup latch after every stage; FABLE-CLOSURE-1930)")
    ap.add_argument("--stage-sites", action="store_true", default=True,
                    help="site the relay_depth stages evenly on the source -> relay line (default since 11-21: relay_mid.tcl "
                         "left lepe stages bunched)")
    ap.add_argument("--no-stage-sites", dest="stage_sites", action="store_false")
    a = ap.parse_args(argv)
    import geom_rules
    rb = Path(a.plan).read_bytes()
    raw = json.loads(rb)
    t = raw["partition_types"][a.type]
    rep = type_delta(a.type, t, Path(a.bound_sv).read_text(), geom_rules.Design(a.geom), a.reach, a.local_taps,
                     not a.no_sites, a.stage_key, a.stage_sites, a.lockup)
    Path(a.out_plan).write_text(dumper(rb, raw)(raw))
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"{a.type}: legs over {a.reach:g} um {rep['legs_over_before']} -> {rep['legs_over_after']}; inst_taps "
          f"{len(rep['inst_taps'])}, local relays seated {len(rep['local'])}, relay_depth rows {len(rep['relay_depth'])} "
          f"(+{rep['added_reset_cycles']} reset cycles), needs_local_tap {len(rep['needs_local_tap'])}, relay_split flops "
          f"{len(rep['relay_split'])} (+{sum(len(r['clones']) for r in rep['relay_split'])} copies), unsplit {len(rep['split'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
