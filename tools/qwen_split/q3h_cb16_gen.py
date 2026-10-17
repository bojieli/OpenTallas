#!/usr/bin/env python3
"""q3h C_B16 replicated cluster generator (Q-DIEPLAN3-CB, 2026-10-16).

One hardened master qfd_c_b16 = one 4 x 4 reduction block (16 A0 ROM-leaf tiles, 457.92 x 1166.4) with
  * the four column corridor words (516 b, the qfd_xcol head's N / S corridor word, unchanged format) entering on the S
    face and leaving on the N face (registered feed-through to the far cluster of the same column group);
  * one qfd_xcst_n (the closed die master, unchanged RTL) per tile on its column's relay run (the tap / x hold);
  * the block's exact morton reduction tree (the tiles' own node adders, any nk tile may host any node) with registered
    relays so every hop is <= 373 um pin to pin, legs aligned by construction (static schedule, no flow control);
  * the block word rs (514 b) leaving on the N face; one regional clock root ck; a pipelined equal-depth reset tree.

    q3h_cb16_gen.py anneal   OUT_HOSTS.json [--seeds N]     search the node -> host assignment (min rs latency, then relay bits)
    q3h_cb16_gen.py gen      [--hosts H.json] [--root R]    write RTL, contract, kit spec, latency header, plan PNG

Exactness: the tree is the reference ot_qwen_me_array_w12 morton pair tree over the 16 logical K-slices of the block
(slice m = morton(local col, local row) = tile_id[3:0]); a node's leg a is always the lower-index subtree, so the
arithmetic graph is identical to every die block of today (tools/qwen_split/test_tree_hosts.py ordered_ast form).
Which tile hosts which node is free (the node adder is the same RTL in every nk tile), as the die's _root_spread /
_east_mirror re-hosting already relies on.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_ARCH = ROOT / "results/arch/qwen_split_compute_1014/q3h"
OUT_RTL = ROOT / "rtl/physical/q3h"
HOP = 360.0            # planning hop; the contract limit is 373 um pin to pin (xcst m5d o+s 378.7 ps x 0.9 reach)
LIMIT = 373.0
TW, TH = 457.92, 1166.4
CW, GAP, STRIP = 64.8, 129.6, 64.8
T_CW = 64.8            # centre (tap) corridor: two column runs; the two rows' stations are staggered in y
EDGE_W = 32.4          # L / R edge strips (Q-DIEPLAN3 19:40: outline 2090.88 = the A0 column pitch 522.72 x 4)
WIDE = {"L": EDGE_W, "R": EDGE_W}
STAGGER = {1: -56.0, 2: 56.0}   # y offset of the col-1 / col-2 station centres from the tap centre (stacked in T)
NOTE_T = ("corridors A / T / B are 64.8 um and the L / R edge strips 32.4 um (outline 2090.88 x 5184, the A0 column "
          "pitch); the stations are soft logic (qfd_xcst_n RTL flattened into the cluster): col-1 / col-2 stations "
          "stacked in T at -/+56 um from the tap centre, col-0 / col-3 stations in the 32.4-um edge strips")
DW, BW = 516, 514      # corridor word, tree / block word
IBW = 3 * 18 + 13 * 24 + 13   # 379
# columns: L | col0 MY | A | col1 R0 | T | col2 MY | B | col3 R0 | R
CORR, COLX = {}, {}
_x = 0.0
for _n in ["L", 0, "A", 1, "T", 2, "B", 3, "R"]:
    if isinstance(_n, str):
        w = WIDE.get(_n, CW)
        CORR[_n] = (_x, _x + w)
        _x += w
    else:
        COLX[_n] = (_x, _x + TW)
        _x += TW
WIDTH = round(_x, 4)
ROWY = {r: STRIP + r * (TH + GAP) for r in range(4)}
HEIGHT = round(STRIP + 4 * TH + 3 * GAP + STRIP, 4)
COL_ORIENT = {0: "MY", 1: "R0", 2: "MY", 3: "R0"}
CHANNELS = [(0.0, STRIP)] + [(ROWY[r] + TH, ROWY[r + 1]) for r in range(3)] + [(HEIGHT - STRIP, HEIGHT)]
GAPS = CHANNELS[1:4]   # tree legs cross only in the internal row gaps; the S / N strips keep the pin fan-in / fan-out
# A0 parent pins (results/arch/qwen_romleaf_1552/parent_nk_pins.json, R0 local): W face tree bands, E face tap / straps
PIN_Y0 = {"n_a": 61.644, "n_b": 162.252, "t_out": 262.764, "n_y": 363.276}
PITCH = 0.192
TAP_Y = (437.196, 485.868)
RST_Y = 435.708
W_FACE_CORR = {0: "A", 1: "A", 2: "B", 3: "B"}
E_FACE_CORR = {0: "L", 1: "T", 2: "T", 3: "R"}
SPARE_DEFAULT = (2, 0)


def ccx(name: str) -> float:
    lo, hi = CORR[name]
    return (lo + hi) / 2


def run_x(c: int) -> float:
    """x of column c's corridor run (stations + relays)."""
    lo, hi = CORR[E_FACE_CORR[c]]
    if E_FACE_CORR[c] == "T":
        return lo + T_CW / 4 if c == 1 else hi - T_CW / 4   # two run lanes in T
    return (lo + hi) / 2


def wface_x(c):
    lo, hi = COLX[c]
    return hi if COL_ORIENT[c] == "MY" else lo


def eface_x(c):
    lo, hi = COLX[c]
    return lo if COL_ORIENT[c] == "MY" else hi


def pin(c, r, port, bit=None):
    yl = PIN_Y0[port] + (PITCH * 256.5 if bit is None else PITCH * bit)
    return (wface_x(c), ROWY[r] + yl)


def plen(p):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(p, p[1:]))


def poly(src, scorr, dst, dcorr, chans=None):
    """Route: vertical in corridors, horizontal only in channels (tree legs: the internal row gaps)."""
    (xs, ys), (xd, yd) = src, dst
    xcs = ccx(scorr) if scorr in CORR else xs
    xcd = ccx(dcorr) if dcorr in CORR else xd
    if scorr == dcorr:
        return [(xs, ys), (xcs, ys), (xcs, yd), (xd, yd)]
    best = None
    for lo, hi in (GAPS if chans is None else chans):
        yc = (lo + hi) / 2
        p = [(xs, ys), (xcs, ys), (xcs, yc), (xcd, yc), (xcd, yd), (xd, yd)]
        if best is None or plen(p) < plen(best):
            best = p
    return best


def along(p, f):
    """Point at arc-length fraction f of polyline p."""
    L = plen(p) * f
    for a, b in zip(p, p[1:]):
        s = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if L <= s or b is p[-1]:
            t = 0 if s == 0 else min(1.0, L / s)
            return (round(a[0] + (b[0] - a[0]) * t, 3), round(a[1] + (b[1] - a[1]) * t, 3))
        L -= s
    return p[-1]


def relays(d):
    return max(0, math.ceil(d / HOP) - 1)


# ------------------------------------------------------------------ down runs (one per column, identical in y)
TAP_C = 0.5 * sum(TAP_Y)


def down_chain():
    pts = [("entry", STRIP / 2)]
    targets = [("xcst%d" % r, ROWY[r] + TAP_C) for r in range(4)] + [("exit", HEIGHT - STRIP / 2)]
    y, nrel = pts[0][1], 0
    for name, ty in targets:
        d = ty - y
        k = relays(d)
        for i in range(1, k + 1):
            pts.append(("rly%d" % nrel, round(y + d * i / (k + 1), 3)))
            nrel += 1
        pts.append((name, round(ty, 3)))
        y = ty
    return pts


CHAIN = down_chain()


def chain_for(c):
    """Column c's run: the same register sequence as CHAIN (equal stage counts in every column), anchors moved by the
    column's station stagger, relays re-spread evenly between anchors."""
    dy = STAGGER.get(c, 0.0)
    anchors = {n: (y + dy if n.startswith("xcst") else y) for n, y in CHAIN if not n.startswith("rly")}
    out, pend, prev = [], [], None
    for n, y in CHAIN:
        if n.startswith("rly"):
            pend.append(n)
            continue
        ya = anchors[n]
        for i, rn in enumerate(pend):
            out.append((rn, round(prev + (ya - prev) * (i + 1) / (len(pend) + 1), 3)))
        pend = []
        out.append((n, round(ya, 3)))
        prev = ya
    return out
STAGE = {n: i + 1 for i, (n, _) in enumerate(CHAIN)}   # registers from the bc pin through n (xcst: its t_q / b_q)


def tap_time(r):
    return STAGE["xcst%d" % r]


# ------------------------------------------------------------------ up tree
def morton(c, r):
    return (c & 1) | ((r & 1) << 1) | (((c >> 1) & 1) << 2) | (((r >> 1) & 1) << 3)


LEAVES = sorted(((c, r) for c in range(4) for r in range(4)), key=lambda s: morton(*s))
NODES = [(l, i) for l in range(1, 5) for i in range(16 >> l)]


def children(l, i):
    if l == 1:
        return [("leaf", LEAVES[2 * i]), ("leaf", LEAVES[2 * i + 1])]
    return [("node", (l - 1, 2 * i)), ("node", (l - 1, 2 * i + 1))]


RS_SPAN = BW / 3.0


def rs_pin_x(z):
    """Centre of the rs pin range on the S face for a run that comes down corridor z (Q-DIEPLAN3 19:55: rs on S)."""
    if z == "T":
        return run_x(2) + 10.0 + DW / 3.0 + 8.0 + RS_SPAN / 2      # just E of bc2's range
    return ccx(z)


def rs_route(root):
    """rs: root n_y -> down a corridor (its own, or T through the nearest row gap) to the S strip -> its pin range."""
    c, r = root
    src = pin(c, r, "n_y")
    X = W_FACE_CORR[c]
    best = None
    for z in ("T", X):
        xp = rs_pin_x(z)
        if z == X:
            p = [src, (ccx(X), src[1]), (ccx(X), STRIP / 2), (xp, STRIP / 2)]
        else:
            p = None
            for lo, hi in GAPS:
                yg = (lo + hi) / 2
                q = [src, (ccx(X), src[1]), (ccx(X), yg), (ccx(z), yg), (ccx(z), STRIP / 2), (xp, STRIP / 2)]
                if p is None or plen(q) < plen(p):
                    p = q
        key = (relays(plen(p)), 0 if z == "T" else 1, plen(p))
        if best is None or key < best[0]:
            best = (key, p, z)
    return best[1], best[2]


def evaluate(host, detail=False):
    t, legs = {}, []
    for (l, i) in NODES:
        hc, hr = host[(l, i)]
        arr = []
        for side, (kind, ref) in zip("ab", children(l, i)):
            if kind == "leaf":
                c, r = ref
                ts, src, sname = tap_time(r), pin(c, r, "t_out"), ("t_out", (c, r))
            else:
                c, r = host[ref]
                ts, src, sname = t[ref], pin(c, r, "n_y"), ("n_y", (c, r))
            dst = pin(hc, hr, "n_a" if side == "a" else "n_b")
            p = poly(src, W_FACE_CORR[c], dst, W_FACE_CORR[hc])
            d = plen(p)
            arr.append(dict(side=side, src=sname, ts=ts, d=d, kmin=relays(d), poly=p))
        a = max(x["ts"] + 1 + x["kmin"] for x in arr)
        for x in arr:
            x["k"] = a - x["ts"] - 1
            legs.append(dict(node=(l, i), host=(hc, hr), **x))
        t[(l, i)] = a
    root = host[(4, 0)]
    p, rz = rs_route(root)
    k = relays(plen(p))
    rs_t = t[(4, 0)] + 1 + k
    bits = sum(x["k"] for x in legs) * BW + (k + 1) * BW
    if detail:
        return rs_t, bits, legs, dict(root=root, d=plen(p), k=k, poly=p, corridor=rz), t
    return rs_t, bits


CUT_TARGET = 0.55


def vcut_over(legs, rsx):
    """Bits above CUT_TARGET x (M3 + M5 tracks) at the worst 20-um bin of the tree corridors A / B."""
    over = 0.0
    for cor in ("A", "B"):
        lo, hi = CORR[cor]
        xc = (lo + hi) / 2
        cap = CUT_TARGET * ((hi - lo) / 0.048 + (hi - lo) / 0.036)
        bins = {}
        for p in [x["poly"] for x in legs] + [rsx["poly"]]:
            for a, b in zip(p, p[1:]):
                if abs(a[0] - xc) < 1e-6 and abs(b[0] - xc) < 1e-6 and abs(a[1] - b[1]) > 1e-6:
                    for k in range(int(min(a[1], b[1]) // 20), int(max(a[1], b[1]) // 20) + 1):
                        bins[k] = bins.get(k, 0) + BW
        if bins:
            over += max(0.0, max(bins.values()) - cap)
    return over


def anneal(seed=1, iters=80000):
    rnd = random.Random(seed)
    slots = [(c, r) for c in range(4) for r in range(4)]
    perm = slots[:]
    rnd.shuffle(perm)
    host = {n: perm[j] for j, n in enumerate(NODES)}
    spare = perm[15]

    def cost(h):
        a, b, legs, rsx, _ = evaluate(h, True)
        return a * 1e6 + vcut_over(legs, rsx) * 1e3 + b
    cur = cost(host)
    best = (cur, dict(host), spare)
    for it in range(iters):
        T = 2e6 * (1 - it / iters) + 1
        h, sp = dict(host), spare
        n1 = rnd.choice(NODES)
        if rnd.random() < 0.2:
            h[n1], sp = sp, h[n1]
        else:
            n2 = rnd.choice(NODES)
            h[n1], h[n2] = h[n2], h[n1]
        c = cost(h)
        if c < cur or rnd.random() < math.exp(-(c - cur) / T):
            host, spare, cur = h, sp, c
            if c < best[0]:
                best = (c, dict(h), sp)
    return best


def load_hosts(path):
    d = json.loads(Path(path).read_text())
    host = {tuple(int(v) for v in k.split("_")): tuple(h) for k, h in d["host"].items()}
    return host, tuple(d["spare"])


def ordered_ast(host):
    """The arithmetic graph in logical slice ids (morton) -- must equal the reference pair tree."""
    def ex(l, i):
        if l == 0:
            return morton(*LEAVES[i])
        return (ex(l - 1, 2 * i), ex(l - 1, 2 * i + 1))
    return ex(4, 0)


# ------------------------------------------------------------------ reset tree (1 b, equal depth to every leaf)
def reset_tree():
    """Pin register at the S face (T), runs to the L / T / R corridors, a tap register at each row's tile rst_n y,
    a pad run to the common depth.  Returns nodes [(name, parent, (x, y))], leaves {row-corridor: name}, depth."""
    root = (ccx("T"), STRIP / 2)
    nodes = [("rst_pin", None, root)]
    leaves = {}
    for cor in ["L", "T", "R"]:
        x = ccx(cor)
        prev, pp = "rst_pin", root
        # horizontal in the S strip first (L / R), then up the corridor; a tap register at each row
        pts = []
        if cor != "T":
            pts.append(((x, STRIP / 2), None))
        for r in range(4):
            pts.append(((x, ROWY[r] + RST_Y), r))
        for (tx, ty), r in pts:
            d = abs(tx - pp[0]) + abs(ty - pp[1])
            k = relays(d)
            for i in range(1, k + 1):
                nm = f"rst_{cor}_{len(nodes)}"
                pt = (round(pp[0] + (tx - pp[0]) * i / (k + 1), 3), round(pp[1] + (ty - pp[1]) * i / (k + 1), 3))
                nodes.append((nm, prev, pt))
                prev = nm
            nm = f"rst_{cor}_r{r}" if r is not None else f"rst_{cor}_corner"
            nodes.append((nm, prev, (round(tx, 3), round(ty, 3))))
            prev, pp = nm, (tx, ty)
            if r is not None:
                leaves[(cor, r)] = nm
    depth = {}
    for nm, par, _ in nodes:
        depth[nm] = 1 if par is None else depth[par] + 1
    D = max(depth[v] for v in leaves.values())
    return nodes, leaves, depth, D


# ------------------------------------------------------------------ RTL
def sname(c, r):
    return f"{c}_{r}"


NK_CLOCKS = (["ck"] + [f"ck_rp{i}" for i in range(10)] + [f"ck_tx{i}" for i in range(8)] + ["ck_rs", "ck_rn"] +
             [f"ck_fa{i}" for i in range(5)] + [f"ck_lsl{i}" for i in range(8)] + ["ck_node"])
NL_CLOCKS = [c for c in NK_CLOCKS if c not in ("ck_fa0", "ck_fa1", "ck_fa3", "ck_node")]


def gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD):
    hosts = {h: n for n, h in host.items()}
    L = []
    w = L.append
    w("`timescale 1ns/1ps")
    w("// GENERATED by tools/qwen_split/q3h_cb16_gen.py -- do not edit.  q3h C_B16 cluster fabric (Q-DIEPLAN3-CB 2026-10-16):")
    w("// every register of the cluster outside the tiles: the four column corridor runs (entry / relays / qfd_xcst_n / exit),")
    w("// the morton reduction tree's relay runs, the rs pin register run and the equal-depth reset tree.  Positions: the")
    w("// contract (results/arch/qwen_split_compute_1014/q3h/cluster_contract.json).  Static schedule: no ready / credit.")
    w("// MUT (bench only, default 0 = the design): 1 = one extra relay on leg a of node (2,0) (misaligned leg);")
    w("//   2 = leaves of nodes (1,0).a and (1,2).a exchanged (wrong pairing, same timing); 3 = one extra relay on column 2's")
    w("//   corridor run before its row-1 station (that column's tiles get go one edge late).")
    w("module qfd_c_b16_fabric #(parameter integer MUT = 0) (")
    ports = ["    input  wire ck", "    input  wire rst_n", "    input  wire far"]
    for c in range(4):
        ports += [f"    input  wire [{DW-1}:0] bc{c}", f"    output wire [{DW-1}:0] bco{c}"]
    ports += [f"    output wire [{BW-1}:0] rs"]
    for c in range(4):
        for r in range(4):
            s = sname(c, r)
            ports += [f"    output wire [{DW-9}:0] tap_{s}", f"    output wire trst_{s}", f"    input  wire [{BW-1}:0] t_out_{s}"]
            if (c, r) != spare:
                ports += [f"    output wire [{BW-1}:0] n_a_{s}", f"    output wire [{BW-1}:0] n_b_{s}",
                          f"    input  wire [{BW-1}:0] n_y_{s}"]
    w(",\n".join(ports))
    w(");")
    w("    wire far_n = ~far;   // static strap complement (sidx of the far cluster = 7 - local row)")
    # reset tree
    w("    // ---- reset: pin register + runs; every tile / station sees rst_n exactly %d edges after the pin" % RD)
    for nm, par, (x, y) in rnodes:
        src = "rst_n" if par is None else f"{par}_q"
        w(f"    wire {nm}_q;  qfd_q3h_stn #(.W(1), .N(1)) u_{nm} (.ck(ck), .d({src}), .q({nm}_q));   // ({x}, {y})")
    for (cor, r), nm in sorted(rleaves.items()):
        pad = RD - rdepth[nm]
        w(f"    wire rstl_{cor}_{r};  qfd_q3h_run #(.W(1), .D({pad})) u_rpad_{cor}_{r} (.ck(ck), .d({nm}_q), .q(rstl_{cor}_{r}));")
    for c in range(4):
        for r in range(4):
            w(f"    assign trst_{sname(c, r)} = rstl_{E_FACE_CORR[c]}_{r};")
    # down runs
    w("    // ---- column corridor runs {tag 8, xl 128, ib %d, go}: entry pin register, relays, a qfd_xcst_n per row, exit" % IBW)
    for c in range(4):
        prev = f"bc{c}"
        for nm, y in chain_for(c):
            if nm.startswith("xcst"):
                r = int(nm[4:])
                s = sname(c, r)
                cin = prev
                if c == 2 and r == 1:
                    w(f"    wire [{DW-1}:0] dm3_{c};  qfd_q3h_run #(.W({DW}), .D(MUT == 3 ? 1 : 0)) u_dm3_{c} (.ck(ck), .d({prev}), .q(dm3_{c}));")
                    cin = f"dm3_{c}"
                # sidx = near: local row r; far: 7 - r  (the x-slice pooled pair (N s, S 7-s) = same slot, blocks 2 apart)
                b1 = "far_n" if (r >> 1) & 1 else "far"
                b0 = "far_n" if r & 1 else "far"
                w(f"    wire [{DW-1}:0] dn{c}_{nm};")
                w(f"    qfd_xcst_n u_x_{s} (.ck(ck), .rst_n(rstl_{E_FACE_CORR[c]}_{r}), .sidx({{far, {b1}, {b0}}}), .b_d({cin}),"
                  f" .a_d(dn{c}_{nm}), .tap_d(tap_{s}), .tie_hi(), .tie_lo());   // ({run_x(c)}, {y})")
            else:
                w(f"    wire [{DW-1}:0] dn{c}_{nm};  qfd_q3h_stn #(.W({DW}), .N(1)) u_dn{c}_{nm} (.ck(ck), .d({prev}), .q(dn{c}_{nm}));   // ({run_x(c)}, {y})")
            prev = f"dn{c}_{nm}"
        w(f"    assign bco{c} = {prev};")
    # up tree
    w("    // ---- morton reduction tree: leg runs (k relays each; legs of one node arrive on the same edge)")
    for x in legs:
        (l, i), side, (hc, hr) = x["node"], x["side"], x["host"]
        kind, (sc, sr) = x["src"]
        src = f"{kind}_{sname(sc, sr)}"
        if MUT_SWAP and (l, i, side) in MUT_SWAP:
            alt = MUT_SWAP[(l, i, side)]
            src = f"(MUT == 2 ? {alt} : {src})"
        k = x["k"]
        kexpr = f"(MUT == 1 ? {k + 1} : {k})" if (l, i, side) == (2, 0, "a") else str(k)
        pts = [along(x["poly"], j / (k + 1)) for j in range(1, k + 1)]
        w(f"    // node ({l},{i}).{side} on tile ({hc},{hr}) <- {kind}({sc},{sr}): {x['d']:.1f} um, {k} relays, hop <= {x['d'] / (k + 1):.1f} um; relays at {pts}")
        w(f"    qfd_q3h_run #(.W({BW}), .D({kexpr})) u_leg_{l}_{i}{side} (.ck(ck), .d({src}), .q(n_{side}_{sname(hc, hr)}));")
    rc, rr = host[(4, 0)]
    k = rsx["k"]
    pts = [along(rsx["poly"], j / (k + 1)) for j in range(1, k + 2)]
    w(f"    // block word rs: root n_y ({rc},{rr}) -> {k} relays + the rs pin register at the N face: {rsx['d']:.1f} um; at {pts}")
    w(f"    qfd_q3h_run #(.W({BW}), .D({k + 1})) u_rs (.ck(ck), .d(n_y_{sname(rc, rr)}), .q(rs));")
    w("endmodule")
    return "\n".join(L) + "\n"


MUT_SWAP = {}


def gen_cluster(host, spare):
    L = []
    w = L.append
    w("`timescale 1ns/1ps")
    w("// GENERATED by tools/qwen_split/q3h_cb16_gen.py -- do not edit.  qfd_c_b16: the q3h replicated cluster (Q-DIEPLAN3-CB")
    w("// 2026-10-16) = one 4 x 4 reduction block: 16 A0 ROM-leaf tiles (hard children; nk = node host, one nl), the fabric")
    w("// (qfd_c_b16_fabric: corridor runs with qfd_xcst_n stations, reduction relays, reset tree).  One master, placed 24x")
    w("// W (R0 / MX) and 24x E (MY / R180).  Straps: cid = the block index (tile_id[15:4]), far = 1 for the far band")
    w("// (bands 0 / 3), wired by the die to this instance's own tie_hi / tie_lo.  tile_id[3:0] = morton(local col, local")
    w("// row) = the slot's logical K-slice, from the tile's own tie_hi / tie_lo straps (no literal in the netlist).")
    w("// Every tile clock entry is driven by the cluster's regional root ck (the cluster CTS balances to each entry).")
    w("module qfd_c_b16 (")
    ports = ["    input  wire ck", "    input  wire rst_n", "    input  wire far", "    input  wire [11:0] cid"]
    for c in range(4):
        ports += [f"    input  wire [{DW-1}:0] bc{c}", f"    output wire [{DW-1}:0] bco{c}"]
    ports += [f"    output wire [{BW-1}:0] rs", "    output wire tie_hi", "    output wire tie_lo"]
    w(",\n".join(ports))
    w(");")
    w("    (* keep = \"true\" *) wire tie_hi_w = 1'b1;")
    w("    (* keep = \"true\" *) wire tie_lo_w = 1'b0;")
    w("    assign tie_hi = tie_hi_w;")
    w("    assign tie_lo = tie_lo_w;")
    conn = []
    for c in range(4):
        for r in range(4):
            s = sname(c, r)
            w(f"    wire [{DW-9}:0] tap_{s};  wire trst_{s};  wire [{BW-1}:0] t_out_{s};  wire th_{s}, tl_{s};")
            conn += [f".tap_{s}(tap_{s})", f".trst_{s}(trst_{s})", f".t_out_{s}(t_out_{s})"]
            if (c, r) != spare:
                w(f"    wire [{BW-1}:0] n_a_{s}, n_b_{s}, n_y_{s};")
                conn += [f".n_a_{s}(n_a_{s})", f".n_b_{s}(n_b_{s})", f".n_y_{s}(n_y_{s})"]
    conn = [".ck(ck)", ".rst_n(rst_n)", ".far(far)"] + [f".bc{c}(bc{c})" for c in range(4)] + \
           [f".bco{c}(bco{c})" for c in range(4)] + [".rs(rs)"] + conn
    w("    qfd_c_b16_fabric u_fab (\n        " + ",\n        ".join(conn) + ");")
    for c in range(4):
        for r in range(4):
            s = sname(c, r)
            m = morton(c, r)
            bits = ", ".join(f"th_{s}" if (m >> b) & 1 else f"tl_{s}" for b in (3, 2, 1, 0))
            nk = (c, r) != spare
            mod = "qfd_tile_nk_rp2_romleaf" if nk else "qfd_tile_nl_rp2_romleaf"
            clk = NK_CLOCKS if nk else NL_CLOCKS
            pc = [f".{k}(ck)" for k in clk] + [f".rst_n(trst_{s})", f".tile_id({{cid, {bits}}})", f".tie_hi(th_{s})",
                                                f".tie_lo(tl_{s})", f".tap(tap_{s})", f".t_out(t_out_{s})"]
            if nk:
                pc += [f".n_a(n_a_{s})", f".n_b(n_b_{s})", f".n_y(n_y_{s})"]
            w(f"    // slot ({c},{r}) {COL_ORIENT[c]} at ({COLX[c][0]}, {ROWY[r]}), K-slice {m}")
            w(f"    {mod} u_t_{s} (\n        " + ",\n        ".join(pc) + ");")
    w("endmodule")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ cuts
def cuts(legs, rsx):
    """Peak bits crossing any 10-um bin of each corridor (vertical runs) / channel (horizontal runs)."""
    vert = {k: {} for k in CORR}
    hor = {i: {} for i in range(len(CHANNELS))}

    def add_v(cor, y0, y1, n):
        for b in range(int(min(y0, y1) // 10), int(max(y0, y1) // 10) + 1):
            vert[cor][b] = vert[cor].get(b, 0) + n

    def add_h(ch, x0, x1, n):
        for b in range(int(min(x0, x1) // 10), int(max(x0, x1) // 10) + 1):
            hor[ch][b] = hor[ch].get(b, 0) + n

    def which_corr(x):
        for k, (lo, hi) in CORR.items():
            if lo - 1e-6 <= x <= hi + 1e-6:
                return k

    def which_ch(y):
        for i, (lo, hi) in enumerate(CHANNELS):
            if lo - 1e-6 <= y <= hi + 1e-6:
                return i
    for c in range(4):
        add_v(E_FACE_CORR[c], STRIP / 2, HEIGHT - STRIP / 2, DW)
    for p, n in [(x["poly"], BW) for x in legs] + [(rsx["poly"], BW)]:
        for a, b in zip(p, p[1:]):
            if abs(a[0] - b[0]) < 1e-6 and abs(a[1] - b[1]) > 1e-6:
                cor = which_corr(a[0])
                if cor:
                    add_v(cor, a[1], b[1], n)
            elif abs(a[1] - b[1]) < 1e-6 and abs(a[0] - b[0]) > 70:
                ch = which_ch(a[1])
                if ch is not None:
                    add_h(ch, a[0], b[0], n)
    out = {}
    for k, (lo, hi) in CORR.items():
        w = hi - lo
        cap5 = w / 0.048
        cap35 = w / 0.048 + w / 0.036
        pk = max(vert[k].values()) if vert[k] else 0
        out["corridor_" + k] = dict(width_um=w, peak_bits=pk, tracks_M5=int(cap5), tracks_M3_M5=int(cap35),
                                    cut_M5=round(pk / cap5, 3), cut_M3_M5=round(pk / cap35, 3))
    for i, (lo, hi) in enumerate(CHANNELS):
        h = hi - lo
        cap = h / 0.048 + h / 0.064
        pk = max(hor[i].values()) if hor[i] else 0
        out[f"channel_{i}_y{lo:.1f}"] = dict(height_um=h, peak_bits=pk, tracks_M4_M6=int(cap), cut_M4_M6=round(pk / cap, 3))
    return out


# ------------------------------------------------------------------ pins / contract / kit
def pin_plan(host, rsx):
    """Cluster ports: face, layer, [lo, hi] along the face (um from the face's W / S end), pins/um."""
    pins = []

    def add(name, bits, face, layer, lo, hi, note=""):
        span = hi - lo
        dens = bits / span if span > 0 else None
        pins.append(dict(port=name, bits=bits, face=face, layer=layer, range_um=[round(lo, 3), round(hi, 3)],
                         pins_per_um=None if dens is None else round(dens, 3), note=note))
    span = DW / 3.0
    for c in range(4):
        x = run_x(c)
        if c == 1:      # the two centre runs share T: col 1's pins extend W of its run, col 2's E of its run
            lo = x - 10.0 - span
        elif c == 2:
            lo = x + 10.0
        else:
            lo = min(max(x - span / 2, 4.32), WIDTH - 4.32 - span)
        add(f"bc{c}", DW, "S", "M5", lo, lo + span, f"column word of local column {c} (corridor {E_FACE_CORR[c]})")
        add(f"bco{c}", DW, "N", "M5", lo, lo + span, f"feed-through of local column {c} to the far cluster")
    rx = rsx["poly"][-1][0]
    span_rs = BW / 3.0
    lo = rx - span_rs / 2
    add("rs", BW, "S", "M5", lo, lo + span_rs, "block word {fault, valid, 512} (was bword); S face (Q-DIEPLAN3 19:55)")
    xt = ccx("T")
    # S face strap / control island at the T corridor centre: between bc1 and bc2's ranges
    b1 = next(p for p in pins if p["port"] == "bc1")["range_um"][1]
    b2 = next(p for p in pins if p["port"] == "bc2")["range_um"][0]
    xs = (b1 + b2) / 2
    add("ck", 1, "S", "M5", xs - 0.15, xs + 0.15, "regional clock root entry (die trunk, neighbour-matched / F1)")
    add("rst_n", 1, "S", "M5", xs + 2.0, xs + 2.3)
    add("far", 1, "S", "M5", xs + 3.0, xs + 3.3, "strap: 1 = far band (0 / 3)")
    add("cid", 12, "S", "M5", xs - 9.0, xs - 3.0, "strap: block index = tile_id[15:4]")
    add("tie_hi", 1, "S", "M5", xs + 4.0, xs + 4.3)
    add("tie_lo", 1, "S", "M5", xs + 5.0, xs + 5.3)
    for p in pins:
        if p["pins_per_um"] and p["pins_per_um"] > 6.0:
            raise SystemExit(f"pin density over 6/um: {p}")
    # overlap check per face
    for f in "NS":
        rs_ = sorted((p["range_um"] for p in pins if p["face"] == f))
        for a, b in zip(rs_, rs_[1:]):
            if b[0] < a[1]:
                raise SystemExit(f"pin overlap on {f}: {a} {b}")
    return pins


def gen_tb(host, spare):
    """The fabric exactness bench top (rtl/test/tb_q3h_cb16_fabric.sv): real fabric + real qfd_xcst_n + real node leaves."""
    L = []
    w = L.append
    w("`timescale 1ns/1ps")
    w("// GENERATED by tools/qwen_split/q3h_cb16_gen.py -- do not edit.  q3h C_B16 fabric exactness bench (Q-DIEPLAN3-CB):")
    w("//   broadcast: every tile takes go / ib at its compiled edge and its own TDM x line (sidx near r / far 7 - r);")
    w("//   reduction: rs = the reference morton pair-tree FP32 sum of the 16 K-slices (gold.hex, numpy float32 RNE) at the")
    w("//   compiled edge, no fault; feed-through bco carries go at its compiled edge.  +FAR=0/1.  MUT 1..3 must FAIL.")
    w("module tb #(parameter integer MUT = 0);")
    w('    `include "q3h_cb16_lat.svh"')
    w('    `include "q3h_cb16_tbdefs.svh"')
    w("    localparam integer NOPS = 4, TLD = 5, LN = 10, T_TILE = TLD + 3;")
    w("    localparam integer LAT_RS = Q3H_LAT_RS_FABRIC + T_TILE + 4 * LN;")
    w("    reg ck = 1'b0;")
    w("    always #0.5 ck = ~ck;")
    w("    integer cyc = 0;")
    w("    always @(posedge ck) cyc <= cyc + 1;")
    w("    integer errors = 0, rseen = 0, o, e, c;")
    w("    reg fault_seen = 1'b0, far = 1'b0, rst_n = 1'b0;")
    w("    integer t_go [0:NOPS-1];")
    w("    integer bseen [0:3];")
    w("    reg [511:0] gold [0:NOPS-1];")
    w("    reg [515:0] bcw [0:3];")
    w("    initial begin")
    w("        if ($test$plusargs(\"FAR\")) far = 1'b1;")
    w("        for (o = 0; o < NOPS; o = o + 1) t_go[o] = 90 + 48 * o;")
    w("        for (c = 0; c < 4; c = c + 1) begin bcw[c] = 516'd0; bseen[c] = 0; end")
    w("        $readmemh(\"gold.hex\", gold);")
    w("    end")
    w("    always @(negedge ck) begin")
    w("        rst_n <= (cyc >= 40);")
    w("        for (c = 0; c < 4; c = c + 1) bcw[c] <= 516'd0;")
    w("        for (o = 0; o < NOPS; o = o + 1)")
    w("            for (e = 0; e < 4; e = e + 1)")
    w("                if (cyc == t_go[o] - 3 + e)")
    w("                    for (c = 0; c < 4; c = c + 1)")
    w("                        bcw[c] <= {1'b1, 3'(e + 4), 1'b1, 3'(e), `Q3H_LINE(o, c, e + 4), `Q3H_LINE(o, c, e), `Q3H_IB(o), (e == 3) ? 1'b1 : 1'b0};")
    w("    end")
    w("    wire [515:0] bco0, bco1, bco2, bco3;")
    w("    wire [513:0] rs;")
    decl, conn = [], []
    for c in range(4):
        for r in range(4):
            s = sname(c, r)
            decl.append(f"    wire [507:0] tap_{s}; wire trst_{s}; wire [513:0] t_out_{s};")
            conn += [f".tap_{s}(tap_{s})", f".trst_{s}(trst_{s})", f".t_out_{s}(t_out_{s})"]
            if (c, r) != spare:
                decl.append(f"    wire [513:0] n_a_{s}, n_b_{s}, n_y_{s};")
                conn += [f".n_a_{s}(n_a_{s})", f".n_b_{s}(n_b_{s})", f".n_y_{s}(n_y_{s})"]
    L += decl
    conn = [".ck(ck)", ".rst_n(rst_n)", ".far(far)"] + [f".bc{c}(bcw[{c}])" for c in range(4)] + \
           [f".bco{c}(bco{c})" for c in range(4)] + [".rs(rs)"] + conn
    w("    qfd_c_b16_fabric #(.MUT(MUT)) u_fab (\n        " + ",\n        ".join(conn) + ");")
    for c in range(4):
        for r in range(4):
            s = sname(c, r)
            h = (c, r) != spare
            na = f"n_a_{s}" if h else "514'd0"
            nb = f"n_b_{s}" if h else "514'd0"
            ny = f"n_y_{s}" if h else ""
            w(f"    tb_q3h_tile_face #(.C({c}), .R({r}), .K({morton(c, r)}), .HOST({int(h)}), .TLD(TLD), .LAT(Q3H_LAT_TAP{r}), .NOPS(NOPS))"
              f" u_f_{s} (.ck(ck), .rst_n(trst_{s}), .tap(tap_{s}), .t_out(t_out_{s}), .n_a({na}), .n_b({nb}), .n_y({ny}));")
    w("    wire [3:0] bgo = {bco3[0], bco2[0], bco1[0], bco0[0]};")
    w("    always @(negedge ck) begin")
    w("        for (c = 0; c < 4; c = c + 1)")
    w("            if (bgo[c] === 1'b1) begin")
    w("                if (bseen[c] >= NOPS || cyc != t_go[bseen[c]] + Q3H_LAT_BCO) begin")
    w("                    $display(\"FAIL bco%0d go at cycle %0d\", c, cyc); errors = errors + 1;")
    w("                end")
    w("                bseen[c] = bseen[c] + 1;")
    w("            end")
    w("        if (rs[512] === 1'b1) begin")
    w("            if (rseen >= NOPS) begin $display(\"FAIL extra rs word at cycle %0d\", cyc); errors = errors + 1; end")
    w("            else begin")
    w("                $display(\"RS op %0d cycle %0d latency %0d (compiled %0d) fault %b match %0d\", rseen, cyc, cyc - t_go[rseen], LAT_RS, rs[513], rs[511:0] === gold[rseen]);")
    w("                if (cyc != t_go[rseen] + LAT_RS) begin $display(\"FAIL rs latency\"); errors = errors + 1; end")
    w("                if (rs[513] !== 1'b0) begin $display(\"FAIL rs fault bit\"); errors = errors + 1; end")
    w("                if (rs[511:0] !== gold[rseen]) begin $display(\"FAIL rs data op %0d: %h expected %h\", rseen, rs[511:0], gold[rseen]); errors = errors + 1; end")
    w("            end")
    w("            rseen = rseen + 1;")
    w("        end")
    w("        if (cyc == t_go[NOPS-1] + LAT_RS + 60) begin")
    w("            if (rseen != NOPS) begin $display(\"FAIL saw %0d rs words, expected %0d\", rseen, NOPS); errors = errors + 1; end")
    w("            for (c = 0; c < 4; c = c + 1) if (bseen[c] != NOPS) begin $display(\"FAIL bco%0d saw %0d gos\", c, bseen[c]); errors = errors + 1; end")
    gs = " + ".join(f"(u_f_{sname(c, r)}.gseen != NOPS)" for c in range(4) for r in range(4))
    w(f"            errors = errors + {gs};")
    w("            if (errors == 0) $display(\"Q3H_CB16_PASS MUT %0d FAR %0d ops %0d tap %0d/%0d/%0d/%0d bco %0d rs %0d\", MUT, far, NOPS, Q3H_LAT_TAP0, Q3H_LAT_TAP1, Q3H_LAT_TAP2, Q3H_LAT_TAP3, Q3H_LAT_BCO, LAT_RS);")
    w("            else $display(\"Q3H_CB16_FAIL MUT %0d FAR %0d errors %0d\", MUT, far, errors);")
    w("            $finish;")
    w("        end")
    w("    end")
    w("endmodule")
    return "\n".join(L) + "\n"


KIT = ROOT / "physical/ref_tile/qfd_c_b16"
A0_NK_VIEW = "physical/ref_tile/qfd_tile_nk_romleaf_a0/views/qfd_tile_nk_rp2_romleaf"
A0_NL_VIEW = "physical/ref_tile/qfd_tile_nl_romleaf_a0/views/qfd_tile_nl_rp2_romleaf"
A0_SOURCES = ["rtl/physical/ot_qwen_rom_tile_die.sv", "rtl/hdc/kv/ot_qwen_kv_land_merge.sv", "rtl/hdc/ot_hdc_fpu.sv",
              "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_sfu.sv",
              "rtl/hdc/ot_hdc_matvec.sv", "rtl/hdc/ot_qwen_me_array_w12.sv", "rtl/hdc/ot_qwen_rom_tile_w12.sv",
              "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_prefix.sv",
              "rtl/hdc/ot_qwen_w12_matvec.sv", "rtl/hdc/ot_qwen_w12_arith.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
              "rtl/hdc/ot_hdc_fp32_add_lat_nr.sv", "rtl/physical/ot_qwen_rom_tile_nk.sv"]


def gen_kit(contract, host, spare, legs, rsx, rnodes):
    """Provisional ref_tile kit for the hardened cluster.  The tile children have no closed view yet (A0 parent gate3
    in GRT repair, Q-ROMPARENT), so tools/ref_tile/ref_tile.py gen cannot run: it reads every child LEF.  This writes the
    spec (the input of ref_tile.py gen), the pin plan, the relay / station site plan and a floorplan record; kit.env /
    place.tcl / pdn.tcl / SDCs come from ref_tile.py gen once the views exist.  NO route is submitted."""
    KIT.mkdir(parents=True, exist_ok=True)
    pins = contract["ports"]
    faces = {"N": [], "S": [], "E": [], "W": []}
    for p_ in pins:
        if p_["port"] not in faces[p_["face"]]:
            faces[p_["face"]].append(p_["port"])
    children = []
    for c in range(4):
        for r in range(4):
            nk = (c, r) != spare
            children.append(dict(view=A0_NK_VIEW if nk else A0_NL_VIEW, count=1, inst=f"u_t_{sname(c, r)}",
                                 at=[round(COLX[c][0], 3), round(ROWY[r], 3)], orient=COL_ORIENT[c], at_exact=True))
    spec = dict(
        name="qfd_c_b16", top="qfd_c_b16", kind="cluster",
        provisional=True,
        gating="A0 tile views (qfd_tile_nk_romleaf_a0 / qfd_tile_nl_romleaf_a0) not closed; layer contract for a cluster "
               "of clusters (A0 is itself a cluster: PG M7, signals to M7) needs a grant -- see the contract gating list",
        sources=A0_SOURCES + ["rtl/lib/ot_rst_relay.sv", "rtl/physical/ot_qwen_tile_node.sv", "rtl/physical/ot_qwen_tile_lsl_fp1.sv",
                              "rtl/physical/ot_qwen_tile_romleaf.sv", "rtl/physical/qfd_tile_nk_rp2_45.sv",
                              "rtl/physical/qfd_tile_nl_rp2_45.sv", "rtl/physical/qfd_tile_nk_rp2_romleaf.sv",
                              "rtl/physical/qfd_tile_nl_rp2_romleaf.sv",
                              "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv", "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv",
                              "rtl/physical/q3h/qfd_q3h_stn.sv", "rtl/physical/q3h/qfd_c_b16_fabric.sv", "rtl/physical/q3h/qfd_c_b16.sv"],
        defines=["OT_QWEN_LSL_FP1"], params={},
        clock_port="ck", clock_ports=["ck"], reset_ports=["rst_n"],
        outline=dict(w=WIDTH, h=HEIGHT, exact=True),
        child_lattice_um=0.108,
        children=children, macros=[],
        pins=faces,
        pin_ranges={p_["port"]: p_["range_um"] for p_ in pins},
        pin_layers={p_["port"]: p_["layer"] for p_ in pins},
        route=dict(pd=0.5, threads=16, peak_ram_gb=256, pin_v="M5", pin_h="M4 M6", hold_margin_ns=0.03, macro_halo_um=5.4),
        recipe=3, keep_pin_regs=True, io_flop_at_pins={"cols": 8}, inhold=True, outhold=True,
        hold_pad={"cell": "HB2xp67_ASAP7_75t_R"},
        relay_sites="physical/ref_tile/qfd_c_b16/relay_sites.json",
        structural_change="q3h replicated cluster: one 4 x 4 reduction block (16 A0 tiles) hardened once, placed 48x; "
                          "the die top routes only inter-cluster relays (bc / bco / rs).",
        slot_change_request="Q-DIEPLAN3 19:40 outline 2090.88 x 5184 (array_grid.json); rs on the S face (19:55)",
        job=dict(owner="Claude:Q-DIEPLAN3-CB", branch="claude/q3h-cb-1016", tag="cb16a", purpose="q3h C_B16 cluster",
                 submit=False))
    sites = dict(schema="opentallas.q3h.relay_sites.v1",
                 note="soft registers of qfd_c_b16_fabric and their planned (x, y) (um, master frame); a placement hook "
                      "pins each register group to a <= 20-um box around its site (hop <= 373 um pin to pin)",
                 down_runs={str(c): [dict(inst=(f"u_fab.u_x_{sname(c, int(n[4:]))}" if n.startswith("xcst") else f"u_fab.u_dn{c}_{n}"),
                                          at=[round(run_x(c), 3), y]) for n, y in chain_for(c)] for c in range(4)},
                 tree=[dict(inst=f"u_fab.u_leg_{x['node'][0]}_{x['node'][1]}{x['side']}.g_run.g_s[{j}].u_s",
                            at=list(along(x["poly"], (j + 1) / (x["k"] + 1)))) for x in legs for j in range(x["k"])],
                 rs=[dict(inst=f"u_fab.u_rs.g_run.g_s[{j}].u_s", at=list(along(rsx["poly"], (j + 1) / (rsx["k"] + 1))))
                     for j in range(rsx["k"] + 1)],
                 reset=[dict(inst=f"u_fab.u_{n}", at=list(xy)) for n, _, xy in rnodes])
    fp = dict(schema="opentallas.ref_tile.floorplan.v1", name="qfd_c_b16", top="qfd_c_b16", kind="cluster",
              provisional=True, die=[0, 0, WIDTH, HEIGHT], core=[2.16, 2.16, WIDTH - 2.16, HEIGHT - 2.16],
              why="contract outline (Q-DIEPLAN3 array_grid.json: 2090.88 x 5184)",
              blocks=[dict(inst=ch["inst"], view=ch["view"], rect=[ch["at"][0], ch["at"][1], ch["at"][0] + TW, ch["at"][1] + TH],
                           orient=ch["orient"]) for ch in children],
              channels=dict(corridors=contract["geometry"]["corridors"], gaps=contract["geometry"]["channels"]),
              pins=faces, clock_port="ck",
              findings=[["BLOCK", "child_views", "A0 tile views not closed (Q-ROMPARENT gate3 GRT repair)", "wait; no route"],
                        ["BLOCK", "layer_contract", "A0 is a cluster (PG M7, signals M2-M7); a cluster parent needs its PG one "
                         "layer above (M8), which the ref_tile contract reserves for the die", "owner / Q-DIEPLAN3 grant"],
                        ["WARN", "corridor_cut", "corridor A peak %d b over 64.8 um = %.2f of M3+M5 tracks at the row-0 pin band "
                         "(guidance; GRT overflow 0 is the gate)" % (contract["cuts"]["corridor_A"]["peak_bits"],
                                                                     contract["cuts"]["corridor_A"]["cut_M3_M5"]), "measure in GRT"]])
    (KIT / "spec.json").write_text(json.dumps(spec, indent=1) + "\n")
    (ROOT / "tools/ref_tile/specs_q3h").mkdir(parents=True, exist_ok=True)
    (ROOT / "tools/ref_tile/specs_q3h/qfd_c_b16.json").write_text(json.dumps(spec, indent=1) + "\n")
    (KIT / "relay_sites.json").write_text(json.dumps(sites, indent=1) + "\n")
    (KIT / "floorplan.json").write_text(json.dumps(fp, indent=1) + "\n")
    (KIT / "pins.json").write_text(json.dumps(dict(schema="opentallas.q3h.cluster_pins.v1", outline=[WIDTH, HEIGHT],
                                                   rule="<= 6 pins/um per face; N / S pins on M5 (cluster signals <= M6)",
                                                   ports=pins), indent=1) + "\n")
    env = ["# PROVISIONAL q3h C_B16 kit (written by tools/qwen_split/q3h_cb16_gen.py, NOT by ref_tile.py gen).",
           "# Regenerate with: python3 tools/ref_tile/ref_tile.py gen tools/ref_tile/specs_q3h/qfd_c_b16.json  once the A0",
           "# tile views exist (gating).  Do not submit a route from this file.",
           "TOP=qfd_c_b16", "SRCS='" + " ".join(spec["sources"]) + "'", "PARAMS=()", f"FW={WIDTH}", f"FH={HEIGHT}",
           "PINS=(" + " ".join("--pin-region '^(%s)(\\[|$)=%s:%g-%g'" % (p_["port"], FACES_ORFS[p_["face"]], p_["range_um"][0], p_["range_um"][1]) for p_ in pins) + ")",
           "CLKPORT=ck", "PD=0.5", "NC=16", "PIN_H='M4 M6'", "PIN_V='M5'", "STAGES=pnr", "RLAYERS='M2 M6'",
           "ROUTE_PERIOD_NS=0.77", "KIT=/src/physical/ref_tile/qfd_c_b16",
           "MACROS=(" + A0_NK_VIEW + " " + A0_NL_VIEW + ")", "RECIPE=3", "PROVISIONAL=1"]
    (KIT / "kit.env").write_text("\n".join(env) + "\n")


FACES_ORFS = {"N": "top", "S": "bottom", "E": "right", "W": "left"}


def plot(path, host, spare, legs, rsx, rnodes, pins):
    """Geometry inspection figure (owner rule: inspect cluster layouts): tiles, corridors, stations, relay sites, legs."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(7.5, 17))
    for c in range(4):
        for r in range(4):
            x0, y0 = COLX[c][0], ROWY[r]
            nk = (c, r) != spare
            ax.add_patch(Rectangle((x0, y0), TW, TH, fc="#dfe8f5" if nk else "#f3e3c8", ec="#555", lw=0.6))
            hs = [f"{l},{i}" for (l, i), h in host.items() if h == (c, r)]
            ax.text(x0 + TW / 2, y0 + TH / 2, f"({c},{r}) {COL_ORIENT[c]}\nK{morton(c, r)}\n" + ("node " + hs[0] if hs else "nl"),
                    ha="center", va="center", fontsize=7)
            wx = wface_x(c)
            ax.plot([wx, wx], [y0 + PIN_Y0["n_a"], y0 + PIN_Y0["n_y"] + 98.5], color="#2a6", lw=2.5)
            ex = eface_x(c)
            ax.plot([ex, ex], [y0 + TAP_Y[0], y0 + TAP_Y[1]], color="#c33", lw=2.5)
    for c in range(4):
        ch = chain_for(c)
        ax.plot([run_x(c)] * len(ch), [y for _, y in ch], color="#c33", lw=0.8)
        for n, y in ch:
            if n.startswith("xcst"):
                ax.add_patch(Rectangle((run_x(c) - 8, y - 26), 16, 52, fc="#c33", ec="none"))
            else:
                ax.plot(run_x(c), y, "s", color="#c33", ms=2.5)
    for x in legs + [rsx]:
        p = x["poly"]
        col = "#06c" if x is not rsx else "#a0a"
        ax.plot([q[0] for q in p], [q[1] for q in p], color=col, lw=0.7, alpha=0.8)
        k = x["k"]
        for j in range(1, k + 1 + (1 if x is rsx else 0)):
            q = along(p, j / (k + 1))
            ax.plot(q[0], q[1], "o", color=col, ms=2.5)
    for n, par, (x, y) in rnodes:
        ax.plot(x, y, ".", color="#888", ms=2)
    for p_ in pins:
        lo, hi = p_["range_um"]
        y = 0 if p_["face"] == "S" else HEIGHT
        ax.plot([lo, hi], [y, y], lw=4, color={"rs": "#a0a"}.get(p_["port"], "#c33" if p_["port"].startswith("bc") else "#333"))
        ax.text((lo + hi) / 2, y + (-60 if p_["face"] == "S" else 25), p_["port"], ha="center", fontsize=6)
    ax.set_xlim(-60, WIDTH + 60)
    ax.set_ylim(-140, HEIGHT + 100)
    ax.set_aspect("equal")
    ax.set_title(f"qfd_c_b16 {WIDTH} x {HEIGHT} um: red = corridor runs / xcst / taps, green = tree pin bands,\n"
                 f"blue = tree legs + relays, purple = rs (S face), grey = reset tree", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("anneal")
    a1.add_argument("out")
    a1.add_argument("--seeds", type=int, default=16)
    a2 = sub.add_parser("gen")
    a2.add_argument("--hosts", default=str(OUT_ARCH / "cb16_hosts.json"))
    a2.add_argument("--contract-copy", default="/home/ubuntu/artifacts/qdieplan3-1016/q3h/cluster_contract.json")
    a = ap.parse_args()
    if a.cmd == "anneal":
        res = sorted((anneal(s) for s in range(a.seeds)), key=lambda r: r[0])
        c, host, spare = res[0]
        Path(a.out).write_text(json.dumps(dict(host={"%d_%d" % k: list(v) for k, v in host.items()}, spare=list(spare),
                                                   cost=c), indent=1) + "\n")
        return
    host, spare = load_hosts(a.hosts)
    assert len(set(host.values())) == 15 and spare not in host.values()
    rs_t, bits, legs, rsx, t = evaluate(host, True)
    # exactness of the arithmetic graph (pure structure: legs a / b = lower / upper morton halves)
    ref = ordered_ast(host)
    # bench mutant 2: exchange the leaf sources of (1,0).a and (1,2).a (both row 0: same edge, different pairing)
    la = next(x for x in legs if x["node"] == (1, 0) and x["side"] == "a")
    lb = next(x for x in legs if x["node"] == (1, 2) and x["side"] == "a")
    MUT_SWAP[(1, 0, "a")] = "t_out_%s" % sname(*lb["src"][1])
    MUT_SWAP[(1, 2, "a")] = "t_out_%s" % sname(*la["src"][1])
    rnodes, rleaves, rdepth, RD = reset_tree()
    OUT_RTL.mkdir(parents=True, exist_ok=True)
    OUT_ARCH.mkdir(parents=True, exist_ok=True)
    (OUT_RTL / "qfd_c_b16_fabric.sv").write_text(gen_fabric(host, spare, legs, rsx, rnodes, rleaves, rdepth, RD))
    (OUT_RTL / "qfd_c_b16.sv").write_text(gen_cluster(host, spare))
    (ROOT / "rtl/test/tb_q3h_cb16_fabric.sv").write_text(gen_tb(host, spare))
    # latency header for the bench (cycles from the bc pin edge of go)
    hdr = ["// GENERATED by tools/qwen_split/q3h_cb16_gen.py: compiled fixed latencies of qfd_c_b16_fabric (edges)",
           f"localparam integer Q3H_LAT_TAP0 = {tap_time(0)};", f"localparam integer Q3H_LAT_TAP1 = {tap_time(1)};",
           f"localparam integer Q3H_LAT_TAP2 = {tap_time(2)};", f"localparam integer Q3H_LAT_TAP3 = {tap_time(3)};",
           f"localparam integer Q3H_LAT_BCO = {STAGE['exit']};",
           f"localparam integer Q3H_LAT_RS_FABRIC = {rs_t};   // + tile (tap pin -> t_out pin) + 4 x node face latency",
           f"localparam integer Q3H_RST_DEPTH = {RD};",
           "localparam [3:0] Q3H_SPARE_C = %d, Q3H_SPARE_R = %d;" % spare]
    (ROOT / "rtl/test/q3h_cb16_lat.svh").write_text("\n".join(hdr) + "\n")
    pins = pin_plan(host, rsx)
    hops = [x["d"] / (x["k"] + 1) for x in legs] + [rsx["d"] / (rsx["k"] + 1)]
    dhops = [b[1] - a[1] for c in range(4) for a, b in zip(chain_for(c), chain_for(c)[1:])]
    rhops = []
    by = {n: p for n, _, p in rnodes}
    for n, par, p in rnodes:
        if par:
            q = by[par]
            rhops.append(abs(p[0] - q[0]) + abs(p[1] - q[1]))
    # hop from the last down relay / xcst to the tile tap: station W/E face to the tile E face, |dy| <= tap band
    tap_hop = max(abs(run_x(c) - eface_x(c)) + abs(STAGGER.get(c, 0.0)) for c in range(4)) + 24.4 + 26.0
    cut = cuts(legs, rsx)
    contract = dict(
        schema="opentallas.qwen.q3h.cluster_contract.v1",
        provisional=True,
        master="qfd_c_b16",
        unit="C_B16",
        owner="Q-DIEPLAN3-CB (claude/q3h-cb-1016)",
        generator="tools/qwen_split/q3h_cb16_gen.py",
        rtl=["rtl/physical/q3h/qfd_c_b16.sv", "rtl/physical/q3h/qfd_c_b16_fabric.sv", "rtl/physical/q3h/qfd_q3h_stn.sv",
             "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice_slots.sv (qfd_xcst_n, unchanged)",
             "qfd_tile_nk_rp2_romleaf / qfd_tile_nl_rp2_romleaf (origin/codex/romleaf-native-1621, A0 parent RPH 3)"],
        outline_um=dict(w=WIDTH, h=HEIGHT, area_mm2=round(WIDTH * HEIGHT / 1e6, 4),
                        note="includes 64.8-um S / N strips (pin + entry / exit registers) and the internal row gaps; "
                             "clusters may abut; " + NOTE_T),
        placement_on_die=dict(
            W_half="bands 0-1 (S of the head gap) MX, bands 2-3 R0: the master S face (bc, ck, straps) faces the head gap "
                   "for the near band (1 / 2); the far band (0 / 3) takes bc from the near cluster's bco across the band gap",
            E_half="MY (bands 2-3) / R180 (bands 0-1): local column 0 is the column farthest from the spine",
            local_column_of_die_column="W: lc = c % 4; E: lc = 3 - c % 4",
            straps=dict(cid="block index b = (die col // 4) * 4 + die row // 4 (today's ref_tile_id block); tile_id = 16 b + morton(lc, lr)",
                        far="1 for bands 0 and 3"),
            die_head_tids="column head of die column c (unchanged qfd_xcol, NH 8): N station k: k<4 -> 16*cid(band 2) + "
                          "morton(lc, k); k>=4 -> 16*cid(band 3) + morton(lc, 7-k).  S station k: k<4 -> 16*cid(band 1) + "
                          "morton(lc, k); k>=4 -> 16*cid(band 0) + morton(lc, 7-k).  Pooled pair (N s, S 7-s) = same slot, "
                          "blocks 2 apart: the same id relation as today (rows s / s+8)."),
        geometry=dict(
            corridors={k: [round(v[0], 3), round(v[1], 3)] for k, v in CORR.items()},
            columns={str(c): dict(x=[round(COLX[c][0], 3), round(COLX[c][1], 3)], orient=COL_ORIENT[c],
                                  tree_face_corridor=W_FACE_CORR[c], tap_face_corridor=E_FACE_CORR[c]) for c in range(4)},
            rows={str(r): dict(y=[round(ROWY[r], 3), round(ROWY[r] + TH, 3)], orient="R0") for r in range(4)},
            channels=[[round(a, 3), round(b, 3)] for a, b in CHANNELS],
            rule="vertical runs in corridors, horizontal runs only in channels (tiles cap M7, cluster PG M7, signals <= M6)"),
        children=dict(
            tiles=[dict(inst=f"u_t_{sname(c, r)}", slot=[c, r], master=("qfd_tile_nl_rp2_romleaf" if (c, r) == spare else "qfd_tile_nk_rp2_romleaf"),
                        view=("qfd_tile_nl_romleaf_a0 (pending)" if (c, r) == spare else "qfd_tile_nk_romleaf_a0 (pending)"),
                        at=[round(COLX[c][0], 3), round(ROWY[r], 3)], orient=COL_ORIENT[c], k_slice=morton(c, r),
                        hosts=[f"({l},{i})" for (l, i), h in host.items() if h == (c, r)]) for c in range(4) for r in range(4)],
            stations=[dict(inst=f"u_fab.u_x_{sname(c, r)}", master="qfd_xcst_n (soft: RTL flattened into the cluster)",
                           centre=[round(run_x(c), 3), round(ROWY[r] + TAP_C + STAGGER.get(c, 0.0), 3)],
                           sidx="near: %d, far: %d" % (r, 7 - r)) for c in range(4) for r in range(4)],
            relays=dict(down_run={str(c): [dict(name=n, y=y) for n, y in chain_for(c) if not n.startswith("xcst")] for c in range(4)},
                        down_run_x={str(c): run_x(c) for c in range(4)},
                        tree_legs=[dict(node=list(x["node"]), side=x["side"], host=list(x["host"]), src=[x["src"][0], list(x["src"][1])],
                                        um=round(x["d"], 1), relays=x["k"], min_relays=x["kmin"],
                                        at=[along(x["poly"], j / (x["k"] + 1)) for j in range(1, x["k"] + 1)]) for x in legs],
                        rs=dict(root=list(host[(4, 0)]), um=round(rsx["d"], 1), relays=rsx["k"], exit_register=True,
                                at=[along(rsx["poly"], j / (rsx["k"] + 1)) for j in range(1, rsx["k"] + 2)])),
            reset=dict(depth_edges=RD, nodes=[dict(name=n, parent=p, at=list(xy)) for n, p, xy in rnodes],
                       note="1-b equal-depth tree: every tile rst_n and every station rst_n %d edges after the pin" % RD),
            clock=dict(entry="ck, S face at the T corridor centre", roots=1,
                       sinks="all 36 (nk) / 32 (nl) tile clock entries + every station / relay flop; the cluster CTS balances "
                             "to each tile entry with that entry's measured insertion (A0 view)")),
        tree=dict(order="reference morton pair tree over K-slices morton(lc, lr); leg a = lower half",
                  ast=json.loads(json.dumps(ref)),
                  hosts={f"{l}_{i}": list(h) for (l, i), h in host.items()}, nl_slot=list(spare)),
        ports=pins,
        latency_edges=dict(
            bc_to_tap={f"row{r}": tap_time(r) for r in range(4)},
            bc_to_bco=STAGE["exit"],
            bc_to_rs=f"{rs_t} + T_tile + 4 x N_face  (T_tile: tile tap pin -> t_out pin; N_face: n_a pin -> n_y pin of the A0 parent)",
            rs_fabric=rs_t,
            note="all tiles of one row take go on the same edge; rows are a 4-edge wave and the up legs absorb it exactly "
                 "(no balancing pad on the wave); the four bc words of a cluster must arrive on the same edge (die-top)"),
        hops_um=dict(limit=LIMIT, plan=HOP, tree_max=round(max(hops), 1), down_run_max=round(max(dhops), 1),
                     reset_max=round(max(rhops), 1), station_to_tap_max=round(tap_hop, 1),
                     in_cluster_max=round(max(max(hops), max(dhops), max(rhops), tap_hop), 1)),
        relay_flops=dict(tree_and_rs=bits, down_runs=4 * DW * (len(CHAIN) - 4), reset=len(rnodes) + sum(RD - rdepth[v] for v in rleaves.values())),
        cuts=cut,
        unit_choice=dict(
            chosen="C_B16",
            C_B16=dict(inter_cluster_bits=dict(bc=4 * DW, bco=4 * DW, rs=BW, straps=14, ck_rst=2, total=8 * DW + BW + 16),
                       tree_legs_crossing=0, outline_mm=[round(WIDTH / 1000, 3), round(HEIGHT / 1000, 3)],
                       pins_per_um_avg=round((8 * DW + BW + 16) / (2 * (WIDTH + HEIGHT)), 3)),
            C_COL=dict(inter_cluster_bits=dict(corridor_in=2 * DW, tree_legs=11 * BW, total=2 * DW + 11 * BW),
                       tree_legs_crossing="11 per column (8 L1 + 2 L3 + 1 block word): every L1 pair spans two columns",
                       outline_mm=[round((TW + CW) / 1000, 3), round((16 * (TH + GAP) + 691.2) / 1000, 3)],
                       note="spans all four bands and the head gap; a 21-mm tall hardened master; the block tree crosses "
                            "cluster faces at every level except L2 / L4"),
            reason="C_B16 keeps the whole block reduction inside the master (one 514-b word out instead of 11 legs), its "
                   "tree legs never cross a die seam, and it is 5.2 mm tall instead of 21.4 mm"),
        x_slice_finding=(
            "The x slice pools tile pairs (N s, S 7-s) = die rows s and s+8 of one column (blocks 2 apart, same morton "
            "slot): pool needs equal quad q = tile_id mod S/TG, which today holds because ids differ by 32.  A head "
            "inside a C_B16 (16 tiles of ONE block) could never pool (ids differ by < 16 while S/TG >= 32 at SMIN 7), "
            "and production k = 24 / 32 ops (NATIVE_AFFINE fp > 64) pool.  So the qfd_xcol heads (unchanged RTL, 48) stay "
            "at the die top, and the cluster takes the four corridor words; bc (1,567 b) per cluster is NOT used."),
        gating=[
            "A0 tile views (qfd_tile_nk_romleaf_a0 / nl twin; Q-ROMPARENT, gate3 in GRT repair): no cluster route before they close",
            "die-top: 48 qfd_xcol heads re-shaped into the 691-um head gap (RTL unchanged) -- the 1,434-um stack no longer fits a corridor",
            "die-top: the four bc words of one cluster arrive on the same edge (equal-age head tree), far cluster = near + %d" % STAGE["exit"],
            "die-top: tids straps per the formula above (ids follow the slot, not the die row)",
            "tile ports registered at the pin (the A0 parent already samples tap / tile_id / rst_n on ck_fa4 and n_a / n_b on face roots)",
        ],
    )
    s = json.dumps(contract, indent=1) + "\n"
    (OUT_ARCH / "cluster_contract.json").write_text(s)
    if a.contract_copy:
        Path(a.contract_copy).parent.mkdir(parents=True, exist_ok=True)
        Path(a.contract_copy).write_text(s)
    gen_kit(contract, host, spare, legs, rsx, rnodes)
    plot(OUT_ARCH / "cluster_plan.png", host, spare, legs, rsx, rnodes, pins)
    print(json.dumps(dict(rs_fabric=rs_t, relay_bits=bits, hops=contract["hops_um"], cuts={k: v for k, v in cut.items()},
                          reset_depth=RD, tap=contract["latency_edges"]["bc_to_tap"], bco=STAGE["exit"],
                          outline=contract["outline_um"]), indent=1))


if __name__ == "__main__":
    main()
