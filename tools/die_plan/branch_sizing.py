#!/usr/bin/env python3
"""PATH-S81-PD10 (METHODOLOGY 12.8 c/d1): plan-computed per-branch sizing of the die H-tree above the mesh.

The H-tree keeps its equal stage count per level (COORD ruling PD8).  Re-sited nodes/repeaters (off_core_resite,
lattice b) make legs of one level unequal in length, so their delays differ and the spread builds level by level
(PD9 RCX: L4 82 -> L10 215 ps at the mesh-driver inputs).  This module equalises the modelled subtree delay,
bottom-up, by choosing the master of the leg repeaters of every faster branch (BUFx24 -> smaller BUFx): the
values are computed from PLAN GEOMETRY and LOADS only (cell sites, Manhattan pin-to-pin wire, liberty NLDM),
deterministically, before the build is written (12.8 d1).  The wire R/C per um of the model is calibrated ONCE,
globally (two scalars), against a routed RCX of the same tree form (PD9 me1), never per branch.

Model (same as die_clock_128.size_stubs): per net, NLDM delay/slew at the lumped load (wire C of every branch +
load pin caps) plus Elmore of each star branch; slew = sqrt(s^2 + (2.2 Elmore)^2).

Bottom-up: P(n) = mean modelled delay from node n's output to the endpoint inputs (mesh drivers / band roots) in its
subtree.  For every leg e = (parent node p -> child node n) at level L, T(e) = leg delay (p's net branch, the leg
repeaters, n's cell) + P(n).  target_L = max T(e) at full size over level L; every leg takes the repeater-size option
whose T is closest to target_L with every modelled stage slew <= slew_max.  Levels without leg repeaters (n_seg 1)
keep their cells (no knob); their imbalance is carried into P of the parent and corrected one level up.
"""
import math
import re
from collections import defaultdict

import die_clock_128 as C128

SIZES = ("BUFx24_ASAP7_75t_R", "BUFx16f_ASAP7_75t_R", "BUFx12f_ASAP7_75t_R", "BUFx10_ASAP7_75t_R",
         "BUFx8_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx5_ASAP7_75t_R", "BUFx4_ASAP7_75t_R", "BUFx3_ASAP7_75t_R")
REP_RE = re.compile(r"^ckm_r(\d+)_(h[01]*)_(\d+)$")
NODE_RE = re.compile(r"^ckm_n(\d+)(?:_(h[01]*))?$")


def tree_nets(nets):
    """driver cell -> net for the die tree above the mesh (root, H-tree levels, band trees), not stubs/mesh."""
    out = {}
    for n in nets:
        lv = n.get("level")
        if lv is None or lv == 99 or isinstance(n["drv"], list):
            continue
        out[n["drv"]] = n
    return out


class Model:
    def __init__(self, cells, nets, libs, r_um, c_um, buf, buf_w, row_y, widths, slew_root=40.0):
        self.cells, self.libs, self.r, self.c, self.buf = cells, libs, r_um, c_um, buf
        self.bw, self.row_y, self.widths, self.slew_root = buf_w, row_y, widths, slew_root
        self.by_drv = tree_nets(nets)
        self.parent = {ld: d for d, n in self.by_drv.items() for ld in n["loads"]}
        self.lib = {}

    def master(self, c):
        return self.lib.get(c) or self.cells[c].get("lib", self.buf)

    def centre(self, c):
        v = self.cells[c]
        return v["x"] + self.widths.get(self.master(c), self.bw) / 2, v["y"] + self.row_y / 2

    def cin(self, c):
        if c.startswith("port:"):
            return 3.0
        m = self.master(c)
        return self.libs[m]["cap"] if m in self.libs else self.libs[self.buf]["cap"]

    def net_eval(self, d, slew_in):
        """(cell delay, {load: (elmore, slew at load)}) for the net driven by cell d."""
        n = self.by_drv.get(d)
        if n is None:
            return None
        a = self.centre(d)
        br, ctot = [], 0.0
        for ld in n["loads"]:
            if ld.startswith("port:"):
                continue
            b = self.centre(ld)
            L = abs(a[0] - b[0]) + abs(a[1] - b[1])
            br.append((ld, L))
            ctot += self.c * L + self.cin(ld)
        lib = self.libs[self.master(d)]
        dc = C128._bilin(lib["delay"], slew_in, ctot)
        sc = C128._bilin(lib["trans"], slew_in, ctot)
        out = {}
        for ld, L in br:
            el = self.r * L * (self.c * L / 2 + self.cin(ld))
            out[ld] = (el, math.sqrt(sc * sc + (2.2 * el) ** 2))
        return dc, out

    def forward(self, root_cell="ckm_n0"):
        """arrival at every tree cell input (A) and output (Y); slews; from the root cell input at t=0."""
        arr_in, arr_out, slew_in, slew_max = {root_cell: 0.0}, {}, {root_cell: self.slew_root}, {}
        st = [root_cell]
        while st:
            d = st.pop()
            e = self.net_eval(d, slew_in[d])
            if e is None:
                continue
            dc, br = e
            arr_out[d] = arr_in[d] + dc
            for ld, (el, s) in br.items():
                arr_in[ld], slew_in[ld] = arr_out[d] + el, s
                st.append(ld)
        return arr_in, arr_out, slew_in


def legs_of(cells):
    """{(level, tag): [rep cells in order]} and {(level, tag): node cell} from the plan's cell names."""
    reps, nodes = defaultdict(list), {}
    for c in cells:
        m = REP_RE.match(c)
        if m:
            reps[(int(m.group(1)), m.group(2))].append((int(m.group(3)), c))
            continue
        m = NODE_RE.match(c)
        if m:
            nodes[(int(m.group(1)), m.group(2) or "h")] = c
    return {k: [c for _, c in sorted(v)] for k, v in reps.items()}, nodes


def endpoints_below(M, n):
    out, st = [], [n]
    while st:
        d = st.pop()
        net = M.by_drv.get(d)
        if net is None:
            out.append(d)
            continue
        for ld in net["loads"]:
            if not ld.startswith("port:"):
                st.append(ld)
    return out


def neighbour_dmax(M, a_in, R=1000.0):
    """[p50, p99, max] |arrival difference| over mesh-driver input pairs whose sites are <= R um apart (Manhattan)."""
    ds = [c for c in a_in if c.startswith("ckm_d_") and c.endswith("_0")]
    grid = defaultdict(list)
    for c in ds:
        x, y = M.centre(c)
        grid[(int(x // R), int(y // R))].append((x, y, a_in[c]))
    v = []
    for (gx, gy), pts in grid.items():
        near = [p for dx in (-1, 0, 1) for dy in (-1, 0, 1) for p in grid.get((gx + dx, gy + dy), [])]
        for x, y, a in pts:
            for x2, y2, a2 in near:
                if (x2, y2) > (x, y) and abs(x - x2) + abs(y - y2) <= R:
                    v.append(abs(a - a2))
    v.sort()
    return [round(v[len(v) // 2], 2), round(v[int(0.99 * len(v))], 2), round(v[-1], 2)] if v else None


def size_branches(cells, nets, libs, r_um, c_um, buf, buf_w, row_y, widths, sizes=SIZES, slew_max=320.0,
                  min_level=1, max_level=11):
    """12.8 d1 plan-computed per-branch sizing (see module doc).  Sets cells[rep]['lib']; returns the record."""
    M = Model(cells, nets, libs, r_um, c_um, buf, buf_w, row_y, widths)
    reps, nodes = legs_of(cells)
    base_in, base_out, base_sl = M.forward()
    ends_all = [c for c in base_in if c not in M.by_drv]
    rec = dict(model="NLDM lumped load + Elmore star wire, plan geometry (cell sites, Manhattan pin-to-pin), "
                     "wire R/C per um calibrated globally (12.8 d1); no per-branch measured input",
               r_kohm_per_um=r_um, c_ff_per_um=c_um, sizes=list(sizes), slew_max_ps=slew_max, levels={},
               hist=defaultdict(int))
    pre = [base_in[e] for e in ends_all]
    rec["model_endpoint_spread_full_ps"] = round(max(pre) - min(pre), 3)
    # P(node) from the current (partially sized) model, evaluated bottom-up
    maxL = max(L for L, _ in nodes) if nodes else 0
    for L in range(min(maxL, max_level), min_level - 1, -1):
        # a leg = its repeaters + its child node: every one of those cells lies only in this leg's subtree
        legs = [(k, reps.get(k, []) + [nodes[k]]) for k in nodes if k[0] == L]
        if not legs:
            rec["levels"][L] = dict(legs=0)
            continue
        a_in, a_out, sl = M.forward()

        def P(n):
            es = endpoints_below(M, n)
            return sum(a_in[e] for e in es) / len(es) - a_out[n]

        cand = {}
        for (lv, tag), rl in legs:
            child = rl[-1]
            if child not in a_out:
                continue
            pnode = M.parent[rl[0]]
            pd = P(child)
            opts = [()] + [(m, j) for m in sizes[1:] for j in range(1, len(rl) + 1)]
            res = []
            for o in opts:
                saved = {c: M.lib.get(c) for c in rl}
                if o:
                    m, j = o
                    pick = {rl[min(len(rl) - 1, int((i + 0.5) * len(rl) / j))] for i in range(j)}
                    for c in rl:
                        M.lib[c] = m if c in pick else buf
                # leg delay from the parent node output: its branch to rl[0], then the chain, then the child cell
                # first rep cap change shifts the parent's branch Elmore a little: re-evaluate the parent net
                e0 = M.net_eval(pnode, sl[pnode])
                t = e0[0] - (a_out[pnode] - a_in[pnode]) + e0[1][rl[0]][0]
                s, smax = e0[1][rl[0]][1], e0[1][rl[0]][1]
                chain = rl
                for i, c in enumerate(chain):
                    e = M.net_eval(c, s)
                    dc, br = e
                    if i < len(chain) - 1:
                        el, s = br[chain[i + 1]]
                        t += dc + el
                        smax = max(smax, s)
                    else:
                        t += dc
                        smax = max(smax, max(v[1] for v in br.values()))
                res.append((o, t + pd, smax))
                for c, v in saved.items():
                    if v is None:
                        M.lib.pop(c, None)
                    else:
                        M.lib[c] = v
            cand[(lv, tag)] = (rl, res)
        full = [r[0][1] for _, r in cand.values()]
        target = max(full)
        post, nsized = [], 0
        for k, (rl, res) in cand.items():
            ok = [r for r in res if r[2] <= slew_max or not r[0]]
            o, t, s = min(ok, key=lambda r: (abs(r[1] - target), len(r[0]) and r[0][1]))
            if o:
                m, j = o
                pick = {rl[min(len(rl) - 1, int((i + 0.5) * len(rl) / j))] for i in range(j)}
                for c in pick:
                    M.lib[c] = m
                    rec["hist"][m] += 1
                nsized += 1
            post.append(t)
        rec["levels"][L] = dict(legs=len(cand), target_ps=round(target, 2), legs_sized=nsized,
                                T_full_range_ps=[round(min(full), 2), round(max(full), 2)],
                                T_sized_range_ps=[round(min(post), 2), round(max(post), 2)])
    a_in, a_out, sl = M.forward()
    post = [a_in[e] for e in ends_all]
    rec["model_endpoint_spread_sized_ps"] = round(max(post) - min(post), 3)
    dd = [a_in[e] for e in ends_all if e.startswith("ckm_d_")]
    db = [base_in[e] for e in ends_all if e.startswith("ckm_d_")]
    rec["model_driver_input_spread_full_ps"] = round(max(db) - min(db), 3)
    rec["model_driver_input_spread_sized_ps"] = round(max(dd) - min(dd), 3)
    rec["model_neighbour_driver_dmax_ps"] = dict(full=neighbour_dmax(M, base_in), sized=neighbour_dmax(M, a_in))
    rec["model_insertion_full_ps"] = [round(min(pre), 2), round(max(pre), 2)]
    rec["model_insertion_sized_ps"] = [round(min(post), 2), round(max(post), 2)]
    rec["model_tree_slew_max_ps"] = round(max(sl.values()), 2)
    for c, m in M.lib.items():
        if m != buf:
            cells[c]["lib"] = m
    rec["cells_resized"] = sum(1 for m in M.lib.values() if m != buf)
    rec["hist"] = dict(sorted(rec["hist"].items()))
    return rec
