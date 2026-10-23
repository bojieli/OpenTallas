#!/usr/bin/env python3
"""HBMc/SMH8 (H.STA.BLK.14.6, 2026-10-22): landing-local placement boxes for the SMH r7 landed parent.

WHY (r7 MAIN 14 h CTS repair_timing WNS -417 ps; r7 worst placed path u_lpl_9_r.g_chunk[82].u_local read_oh[0] -> o[13]
-781.8 ps: 3 logic levels, two ~380 ps wires INSIDE one landing local).  The r7 band fences put every landing read half in
its destination clock band, but several bands cannot reach the pins their readers feed: the xs band is the strip WEST and
SOUTH of the x-store macro while bk1 (2,069 b) enters on its NORTH face; the m band lies below the merge macro while ev /
sum / tag_d enter on its TOP face (inside band c).  GPL then spread one 24-bit local between ring, band and pin.

WHAT: every landing half (ring writer u_lpl_N_w, read u_lpl_N_r) gets its own small placement box at its landing:
  * a read half beside the pins its o bits feed (hard-child pins bit-exact from the child LEF; IO pins from the kit pin
    regions), a ring beside the pins / port its i bits come from;
  * a half whose endpoint is soft follows the same-region soft chain (<= 3 instances) to the first hard pins / ports;
    else it takes the box of the landing half it shares that chain with; else it sits beside its partner half.
  * MAIN ("hardened landing local", --mode chunk): one box per kept 24-bit u_local (keep_hierarchy cluster), laid along the
    pin edge in bit order; FALLBACK ("soft local", --mode half): one box per landing half (all its chunks).
Boxes never overlap a hard child (+ halo) or each other; each is sized from the local's estimated cell area at
--util.  The PRE_GLOBAL_PLACE hook re-groups the landing cells out of their r7 band group into these r6_-named groups (so
the r7 PRE_DETAIL_PLACE dissolve removes them before DPL / CTS repair).  Placement only: 0 cycles, RTL untouched.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "landed_parent"))
import lp  # noqa: E402

HALO = 5.4
SITE, ROW = 0.054, 0.27
# estimated placed std-cell area (um2) of one kept local at W bits (ASAP7 R: DFF 0.29, AOI/mux ~0.09-0.12)
AREA_R = lambda w: 0.60 * w + 4.0      # o flop + AND-OR share + read_oh / rc / warm / rq
AREA_W = lambda w: 1.60 * w + 6.0      # D=4 slot flops with write enable + write_oh / valid / wc / rq


def lef_pins(path: Path):
    sx = sy = None
    pins, cur, got = {}, None, False
    for ln in path.open():
        s = ln.split()
        if not s:
            continue
        if s[0] == "SIZE" and sx is None:
            sx, sy = float(s[1]), float(s[3])
        elif s[0] == "PIN":
            cur, got = s[1].replace("\\", ""), False
        elif s[0] == "END" and cur and len(s) > 1 and s[1].replace("\\", "") == cur:
            cur = None
        elif s[0] == "RECT" and cur and not got:
            x0, y0, x1, y1 = map(float, s[1:5])
            pins[cur] = ((x0 + x1) / 2, (y0 + y1) / 2)
            got = True
    return sx, sy, pins


def orient_xy(sx, sy, x, y, o):
    if o == "MX":
        return x, sy - y
    if o == "MY":
        return sx - x, y
    if o == "R180":
        return sx - x, sy - y
    if o != "R0":
        raise SystemExit(f"orientation {o} unsupported")
    return x, y


class Geo:
    def __init__(self, kit: dict, kenv: str):
        self.W, self.H = kit["outline"]["w"], kit["outline"]["h"]
        self.macro = {}          # flat-parent inst -> dict(box, pins{name: (x, y)})
        for c in kit["children"]:
            v = c["view"]
            sx, sy, pins = lef_pins(ROOT / v / (Path(v).name + ".lef"))
            ox, oy = c["at"]
            o = c.get("orient", "R0")
            P = {n: tuple(a + b for a, b in zip(orient_xy(sx, sy, x, y, o), (ox, oy))) for n, (x, y) in pins.items()}
            inst = c["inst"].split(".")[0]          # u_mg1.u_merge: the soft wrapper u_mg1 passes its ports straight through
            self.macro[inst] = dict(box=(ox, oy, ox + sx, oy + sy), pins=P, name=c["inst"])
        self.ports = {}
        for m in re.finditer(r"--pin-region '\^\((\w+)\)\(\\\[\|\$\)=(\w+):([\d.]+)-([\d.]+)'", kenv):
            self.ports[m.group(1)] = (m.group(2), float(m.group(3)), float(m.group(4)))

    def macro_pin(self, inst, pin, bit, width):
        P = self.macro[inst]["pins"]
        for n in ((f"{pin}[{bit}]", pin) if width > 1 else (pin, f"{pin}[0]")):
            if n in P:
                return P[n]
        return None

    def port_pin(self, port, bit, width):
        if port not in self.ports:
            return None
        face, lo, hi = self.ports[port]
        t = lo + (hi - lo) * (bit + 0.5) / max(width, 1)
        x, y = {"left": (0.0, t), "right": (self.W, t), "bottom": (t, 0.0), "top": (t, self.H)}[face]
        return (x, y, "port:" + face)

    def edge_of(self, inst, pts):
        """face of the hard child the points sit on (outward normal)"""
        x0, y0, x1, y1 = self.macro[inst]["box"]
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        d = {"W": abs(mx - x0), "E": abs(mx - x1), "S": abs(my - y0), "N": abs(my - y1)}
        return min(d, key=d.get)


def bitmap(P: lp.Parent, ex: str):
    """[(net, net_bit)] LSB first for a connection expression (ident / ident[a:b] / ident[a] / {concat}); None = unknown"""
    ex = re.sub(r"\s+", "", ex)
    items = lp.split_top(ex[1:-1]) if ex.startswith("{") and ex.endswith("}") else [ex]
    out = []
    for it in reversed(items):                       # concat lists MSB first
        m = re.fullmatch(r"(\w+)(?:\[(\d+)(?::(\d+))?\])?", it)
        if not m or m.group(1) in P.env:
            return None
        n = m.group(1)
        if m.group(2) is None:
            w = lp.eval_width(P.rng(n), P.env)
            out += [(n, b) for b in range(w)]
        elif m.group(3) is None:
            out.append((n, int(m.group(2))))
        else:
            hi, lo = int(m.group(2)), int(m.group(3))
            out += [(n, b) for b in range(lo, hi + 1)] if hi >= lo else [(n, b) for b in range(lo, hi - 1, -1)]
    return out


class Planner:
    def __init__(self, spec, kit, kenv, mode, util, chunk_bits, manual=None):
        self.manual = manual or {}
        self.P = lp.Parent(spec)
        self.plan = self.P.plan()
        self.G = Geo(kit, kenv)
        self.mode, self.util, self.cb = mode, util, chunk_bits
        self.drv, self.rd, self.out_drv = self.plan["drv"], self.plan["rd"], self.plan["out_drv"]
        self.inst = {i["inst"]: i for i in self.P.insts}
        self.lands = self.plan["lands"]
        self.byw = {}                                # (net, src_region) -> landing
        self.byr = {}                                # (net, reader inst) -> landing
        for L in self.lands:
            self.byw[(L["net"], L["src_region"])] = L
            for r in L["readers"]:
                self.byr[(L["net"], r.split(".")[0])] = L

    # ---- endpoint search -------------------------------------------------------------------------------------------
    def pins_of(self, inst, pin, net, bits):
        """positions of the hard-child / port pins that carry net[bits] at inst.pin"""
        ins = self.inst[inst]
        bm = bitmap(self.P, ins["conns"][pin])
        if bm is None or inst not in self.G.macro:
            return []
        out = []
        for pb, (n, b) in enumerate(bm):
            if n == net and (bits is None or b in bits):
                p = self.G.macro_pin(inst, pin, pb, len(bm))
                if p:
                    out.append((p[0], p[1], inst))
        return out

    def forward(self, region, net, bits, readers=None, depth=3):
        """(positions, linked landing halves) of the same-region consumers of net (BFS over soft instances)"""
        seen, front, links = set(), [(net, bits, readers)], []
        for _ in range(depth + 1):
            pos, nxt = [], []
            for n, bs, rds in front:
                for (rn, inst, pin) in self.rd:
                    if rn != n or (rds is not None and f"{inst}.{pin}" not in rds):
                        continue
                    if self.P.region[inst] != region:
                        L = self.byw.get((n, region))
                        if L:
                            links.append((L["name"], "w"))
                        continue
                    if inst in self.G.macro:
                        pos += self.pins_of(inst, pin, n, bs)
                    elif inst not in seen:
                        seen.add(inst)
                        for op, ex in self.inst[inst]["conns"].items():
                            if self.P.cports[self.inst[inst]["module"]].get(op) == "out":
                                for m in lp.idents(ex):
                                    if m not in self.P.env:
                                        same = bs is not None and m in self.P.wires and \
                                            lp.eval_width(self.P.rng(m), self.P.env) == lp.eval_width(self.P.rng(n), self.P.env)
                                        nxt.append((m, bs if same else None, None))
                if n in self.out_drv and n in self.G.ports:
                    w = lp.eval_width(self.P.rng(n), self.P.env)
                    pos += [self.G.port_pin(n, b, w) for b in (bs if bs else range(w))]
            if pos:
                return pos, links
            front = nxt
            if not front:
                break
        return [], links

    def backward(self, region, net, bits, depth=3):
        seen, front, links = set(), [(net, bits)], []
        for _ in range(depth + 1):
            pos, nxt = [], []
            for n, bs in front:
                for d in sorted(self.drv.get(n, ())):
                    if d.startswith("port:"):
                        p = d[5:]
                        w = lp.eval_width(self.P.rng(p), self.P.env)
                        q = [self.G.port_pin(p, b, w) for b in (bs if bs else range(w))]
                        pos += [x for x in q if x]
                        continue
                    if self.P.region[d] != region:
                        continue
                    if d in self.G.macro:
                        for op, ex in self.inst[d]["conns"].items():
                            if self.P.cports[self.inst[d]["module"]].get(op) == "out" and n in lp.idents(ex):
                                pos += self.pins_of(d, op, n, bs)
                    elif d not in seen:
                        seen.add(d)
                        mod = self.inst[d]["module"]
                        for ip, ex in self.inst[d]["conns"].items():
                            if self.P.cports[mod].get(ip) != "in" or ip in (self.P.S.get("clock_pins") or []) \
                                    or ip in (self.P.S.get("reset_pins") or []):
                                continue
                            for m in lp.idents(ex):
                                if m in self.P.env or m in self.P.ck or m == self.P.rst:
                                    continue
                                L = self.byr.get((m, d))
                                if L and L["dst_region"] == region:
                                    links.append((L["name"], "r"))
                                    continue
                                same = bs is not None and lp.eval_width(self.P.rng(m), self.P.env) == \
                                    lp.eval_width(self.P.rng(n), self.P.env)
                                nxt.append((m, bs if same else None))
            if pos:
                return pos, links
            front = nxt
            if not front:
                break
        return [], links

    # ---- anchors --------------------------------------------------------------------------------------------------
    def chunks(self, L):
        w = L["width"]
        return [(c, list(range(c * self.cb, min(w, (c + 1) * self.cb)))) for c in range(math.ceil(w / self.cb))]

    def solve(self):
        H = {}
        for L in self.lands:
            for side in ("r", "w"):
                key = (L["name"], side)
                reg = L["dst_region"] if side == "r" else L["src_region"]
                ch = []
                links = []
                for c, bits in self.chunks(L):
                    if side == "r":
                        pos, lk = self.forward(reg, L["net"], set(bits), readers=set(L["readers"]))
                    else:
                        pos, lk = self.backward(reg, L["net"], set(bits))
                    links += lk
                    ch.append(dict(c=c, w=len(bits), pos=pos))
                H[key] = dict(L=L, side=side, region=reg, chunks=ch, links=sorted(set(links)),
                              how="pins" if all(x["pos"] for x in ch) else None)
        # manual anchors (a chain whose two crossings would otherwise exceed the E=2 reach): the half sits there
        for k, (x, y) in self.manual.items():
            h = H[(k[:-1], k[-1])]
            for c in h["chunks"]:
                c["pos"] = []
            h["anchor"], h["how"] = (x, y), "manual"
        # chunks whose own bits found no pins take the half's mean; halves with no pins take links / partner
        for h in H.values():
            if h["how"] == "manual":
                continue
            allp = [p for x in h["chunks"] for p in x["pos"]]
            if allp:
                m = (sum(p[0] for p in allp) / len(allp), sum(p[1] for p in allp) / len(allp))
                for x in h["chunks"]:
                    x["anchor"] = (sum(p[0] for p in x["pos"]) / len(x["pos"]), sum(p[1] for p in x["pos"]) / len(x["pos"])) \
                        if x["pos"] else m
                h["anchor"], h["how"] = m, h["how"] or "pins(partial)"
        def chain_pass():
            moved = True
            while moved:
                moved = False
                for h in H.values():
                    if "anchor" in h:
                        continue
                    got = [H[k]["anchor"] for k in h["links"] if k in H and "anchor" in H[k] and H[k]["how"] != "manual"]
                    if got:
                        h["anchor"] = (sum(a[0] for a in got) / len(got), sum(a[1] for a in got) / len(got))
                        h["how"] = "chain:" + ",".join(f"{a}{b}" for a, b in h["links"])
                        moved = True
        while True:
            chain_pass()
            todo = [h for h in H.values() if "anchor" not in h]
            if not todo:
                break
            step = False
            # chains first: linked halves wait for their links.  A cycle of linked halves (relay chains: 7r <-> 9w) is
            # opened at ONE ring writer, the widest, placed beside its read half (the chain then gathers at the reader's
            # pins), then the chain pass runs again.
            for h in todo:
                pk = (h["L"]["name"], "w" if h["side"] == "r" else "r")
                if not h["links"] and "anchor" in H[pk]:
                    h["anchor"], h["how"] = H[pk]["anchor"], "partner"
                    step = True
            if not step:
                cand = [h for h in todo if "anchor" in H[(h["L"]["name"], "w" if h["side"] == "r" else "r")]]
                if cand:
                    h = max(cand, key=lambda h: (h["side"] == "w", h["L"]["width"], -int(h["L"]["name"])))
                    h["anchor"], h["how"] = H[(h["L"]["name"], "w" if h["side"] == "r" else "r")]["anchor"], "partner"
                    step = True
            if not step:
                for h in todo:
                    h["anchor"], h["how"] = (self.G.W / 2, self.G.H / 2), "centre"
        for h in H.values():
            if h["how"] == "partner":
                pk = (h["L"]["name"], "w" if h["side"] == "r" else "r")
                for x, y in zip(h["chunks"], H[pk]["chunks"]):
                    if not x["pos"] and y["pos"]:
                        x["pos"], x["anchor"] = list(y["pos"]), y.get("anchor", h["anchor"])
            for x in h["chunks"]:
                x.setdefault("anchor", h["anchor"])
        self.H = H
        return H

    # ---- boxes ----------------------------------------------------------------------------------------------------
    def place(self):
        """boxes: one per kept chunk (chunk mode) or per (half, endpoint owner) (half mode); returns groups + chunk map"""
        G = self.G
        blk = [(x0 - HALO, y0 - HALO, x1 + HALO, y1 + HALO) for (x0, y0, x1, y1) in (m["box"] for m in G.macro.values())]
        taken = []
        EPS = 0.06

        def free(b):
            x0, y0, x1, y1 = b
            if x0 < 1.0 or y0 < 1.0 or x1 > G.W - 1.0 or y1 > G.H - 1.0:
                return False
            return not any(x0 < c and a < x1 and y0 < d and b_ < y1 for (a, b_, c, d) in blk + taken)

        def edge(owner, pts):
            """outward normal of the pin face the points sit on: a hard child's face, or the inward normal of a port face"""
            if owner is None:
                return None
            if owner.startswith("port:"):
                return {"left": "E", "right": "W", "bottom": "N", "top": "S"}[owner[5:]]
            return G.edge_of(owner, pts)

        def face_line(owner, e):
            """the coordinate the box starts from (hard-child face + halo, or the outline face + 2.16 um for pin flops)"""
            if owner.startswith("port:"):
                return {"E": 2.16, "W": G.W - 2.16, "N": 2.16, "S": G.H - 2.16}[e]
            x0, y0, x1, y1 = G.macro[owner]["box"]
            return {"E": x1 + HALO + EPS, "W": x0 - HALO - EPS, "N": y1 + HALO + EPS, "S": y0 - HALO - EPS}[e]

        def fit(anchor, area, owner=None, pts=None):
            ax, ay = anchor
            e = edge(owner, pts) if pts else None
            if e:
                span = (max(p[0] for p in pts) - min(p[0] for p in pts)) if e in "NS" else \
                       (max(p[1] for p in pts) - min(p[1] for p in pts))
                f = face_line(owner, e)
                cands = []
                for si, stretch in enumerate((1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0)):
                    along = max(max(span, math.sqrt(area)) * stretch, 4.32)
                    depth = max(area / along, 2.16)
                    for k in range(0, 160):
                        for s in range(-16, 17):
                            sl = s * along * 0.25
                            cands.append((k * 0.54 + 1.5 * abs(sl) + 6.0 * si, k * 0.54, sl, along, depth))
                cands.sort(key=lambda c: c[0])
                for _, off, sl, along, depth in cands:
                    if e in "NS":
                        x0 = ax + sl - along / 2
                        y0 = f + off if e == "N" else f - off - depth
                        b = (math.floor(x0 / SITE) * SITE, math.floor(y0 / ROW) * ROW)
                        b = (b[0], b[1], b[0] + math.ceil(along / SITE) * SITE, b[1] + math.ceil(depth / ROW) * ROW)
                        if e == "S" and b[3] > f:
                            b = (b[0], b[1] - ROW, b[2], b[3] - ROW)
                    else:
                        y0 = ay + sl - along / 2
                        x0 = f + off if e == "E" else f - off - depth
                        b = (math.floor(x0 / SITE) * SITE, math.floor(y0 / ROW) * ROW)
                        b = (b[0], b[1], b[0] + math.ceil(depth / SITE) * SITE, b[1] + math.ceil(along / ROW) * ROW)
                        if e == "W" and b[2] > f:
                            b = (b[0] - SITE, b[1], b[2] - SITE, b[3])
                    if free(b):
                        taken.append(b)
                        return b, e
            w = max(math.sqrt(area), 4.32)
            for r in range(0, 600):
                st = 1.08 * r
                n = max(1, 8 * r)
                for i in range(n):
                    t = 2 * math.pi * i / n
                    cx, cy = ax + st * math.cos(t), ay + st * math.sin(t)
                    x0 = math.floor((cx - w / 2) / SITE) * SITE
                    y0 = math.floor((cy - w / 2) / ROW) * ROW
                    b = (x0, y0, x0 + math.ceil(w / SITE) * SITE, y0 + math.ceil(w / ROW) * ROW)
                    if free(b):
                        taken.append(b)
                        return b, None
            raise SystemExit(f"no free box of {area:.1f} um2 near {anchor}")

        def owner_of(pts):
            if not pts:
                return None
            cnt = {}
            for p in pts:
                cnt[p[2]] = cnt.get(p[2], 0) + 1
            return max(cnt, key=cnt.get)

        order = sorted(self.H.values(), key=lambda h: (h["how"] not in ("pins", "pins(partial)"), h["side"] == "w",
                                                      -h["L"]["width"]))
        groups, cmap = [], {}
        for h in order:
            fa = AREA_R if h["side"] == "r" else AREA_W
            half = f"u_lpl_{h['L']['name']}_{h['side']}"
            tag = f"l{h['L']['name']}{h['side']}"
            by = {}
            for x in h["chunks"]:
                by.setdefault(owner_of(x["pos"]), []).append(x)
            units = []
            for o, xs in by.items():
                pts = [p for x in xs for p in x["pos"] if p[2] == o] if o else []
                anc = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else h["anchor"]
                units.append((xs, anc, pts))
            for j, (xs, anc, pts) in enumerate(units):
                o = owner_of(pts)
                opts = [p for p in pts if p[2] == o] if o else []
                area = sum(fa(x["w"]) for x in xs)
                b, e = fit(anc, area / self.util, o, opts)
                ug = f"r6_{tag}" + (f"_{j}" if len(units) > 1 else "")
                if self.mode == "half":
                    parts = [(ug, b, xs)]
                else:
                    # hardened landing locals: the unit box is cut into one slice per kept chunk, in pin order along
                    # the pin face (bit order kept), or a row-major grid when the unit has no pin face
                    x0, y0, x1, y1 = b
                    key = (lambda x: x["anchor"][0]) if e in ("N", "S") else (lambda x: x["anchor"][1])
                    xs_o = sorted(xs, key=lambda x: (key(x), x["c"])) if e else sorted(xs, key=lambda x: x["c"])
                    tot = sum(fa(x["w"]) for x in xs_o)
                    parts = []
                    if e:
                        acc = 0.0
                        for x in xs_o:
                            a0, acc = acc, acc + fa(x["w"]) / tot
                            if e in ("N", "S"):
                                s0 = x0 + math.floor((x1 - x0) * a0 / SITE) * SITE
                                s1 = x0 + math.floor((x1 - x0) * acc / SITE) * SITE if acc < 1 - 1e-9 else x1
                                parts.append((f"r6_{tag}_c{x['c']}", (round(s0, 3), y0, round(s1, 3), y1), [x]))
                            else:
                                s0 = y0 + math.floor((y1 - y0) * a0 / ROW) * ROW
                                s1 = y0 + math.floor((y1 - y0) * acc / ROW) * ROW if acc < 1 - 1e-9 else y1
                                parts.append((f"r6_{tag}_c{x['c']}", (x0, round(s0, 3), x1, round(s1, 3)), [x]))
                    else:
                        n = len(xs_o)
                        cols = max(1, math.ceil(math.sqrt(n)))
                        rows = math.ceil(n / cols)
                        for i, x in enumerate(xs_o):
                            r_, c_ = divmod(i, cols)
                            s0 = x0 + math.floor((x1 - x0) * c_ / cols / SITE) * SITE
                            s1 = x0 + math.floor((x1 - x0) * (c_ + 1) / cols / SITE) * SITE if c_ < cols - 1 else x1
                            t0 = y0 + math.floor((y1 - y0) * r_ / rows / ROW) * ROW
                            t1 = y0 + math.floor((y1 - y0) * (r_ + 1) / rows / ROW) * ROW if r_ < rows - 1 else y1
                            parts.append((f"r6_{tag}_c{x['c']}", (round(s0, 3), round(t0, 3), round(s1, 3), round(t1, 3)), [x]))
                for g, bb, xx in parts:
                    groups.append(dict(group=g, half=half, region=h["region"], box=[round(v, 3) for v in bb], edge=e,
                                       owner=o, how=h["how"].split(":")[0], chunks=[x["c"] for x in xx],
                                       est_um2=round(sum(fa(x["w"]) for x in xx), 1)))
                    for x in xx:
                        cmap[f"{half}/{x['c']}"] = g
        self.groups, self.cmap = groups, cmap
        return groups


TCL = r"""# GENERATED by tools/hbm_smh_r8/landing_boxes.py ({kit}, mode {mode}) -- do not edit; re-run the generator.
# HBMc/SMH8 (H.STA.BLK.14.6) PRE_GLOBAL_PLACE, after the r7 band fence: every kept landing local
# (u_lpl_<N>_<r|w>.g_chunk[c].u_local) leaves its band group and joins its landing box beside the pins it reads / feeds
# ({modedoc}).  Group names start with r6_ so physical/hbm_smh_r7/fence_dissolve.tcl removes them before detailed placement.
# Placement only: 0 cycles.
set ot_r8_groups {{
{groups}
}}
set ot_r8_cmap [dict create {cmap}]
set ot_r8_blk [ord::get_db_block]
set ot_r8_dbu [$ot_r8_blk getDbUnitsPerMicron]
set ot_r8_core [$ot_r8_blk getCoreArea]
set ot_r8_grp [dict create]
set ot_r8_box [dict create]
foreach r $ot_r8_groups {{
  lassign $r g x0 y0 x1 y1
  set X0 [expr {{round($x0 * $ot_r8_dbu)}}]; set Y0 [expr {{round($y0 * $ot_r8_dbu)}}]
  set X1 [expr {{round($x1 * $ot_r8_dbu)}}]; set Y1 [expr {{round($y1 * $ot_r8_dbu)}}]
  set rg [odb::dbRegion_create $ot_r8_blk $g]
  odb::dbBox_create $rg $X0 $Y0 $X1 $Y1
  dict set ot_r8_grp $g [odb::dbGroup_create $rg $g]
  dict set ot_r8_box $g [list $X0 $Y0 $X1 $Y1]
}}
set ot_r8_area [dict create]
set ot_r8_n 0
foreach i [$ot_r8_blk getInsts] {{
  if {{[[$i getMaster] isBlock]}} continue
  regsub -all {{\\}} [$i getName] {{}} n
  if {{![regexp {{^(u_lpl_[0-9]+_[rw])\.g_chunk\[([0-9]+)\]\.u_local[./]}} $n -> half c]}} continue
  if {{![dict exists $ot_r8_cmap "$half/$c"]}} {{ error "R8_LANDING_BOX: no box for $half/$c ($n)" }}
  if {{[$i getPlacementStatus] in {{FIRM LOCKED COVER}}}} continue
  set g [dict get $ot_r8_cmap "$half/$c"]
  set og [$i getGroup]
  if {{$og ne "NULL"}} {{ $og removeInst $i }}
  [dict get $ot_r8_grp $g] addInst $i
  set m [$i getMaster]
  dict set ot_r8_area $g [expr {{([dict exists $ot_r8_area $g] ? [dict get $ot_r8_area $g] : 0.0) + double([$m getWidth]) * [$m getHeight]}}]
  incr ot_r8_n
}}
# a box the synthesized local fills above 0.45 (GPL target density 0.50) grows about its centre to 0.36 (logged)
set ot_r8_grown 0
set ot_r8_umax 0.0
set ot_r8_empty 0
dict for {{g b}} $ot_r8_box {{
  lassign $b X0 Y0 X1 Y1
  if {{![dict exists $ot_r8_area $g]}} {{
    # a local synthesis emptied (constant / unloaded bits): drop its region so GPL sees no empty group
    odb::dbGroup_destroy [dict get $ot_r8_grp $g]
    foreach rr [$ot_r8_blk getRegions] {{ if {{[$rr getName] eq $g}} {{ odb::dbRegion_destroy $rr }} }}
    incr ot_r8_empty
    continue
  }}
  set a [dict get $ot_r8_area $g]
  set u [expr {{$a / (double($X1 - $X0) * ($Y1 - $Y0))}}]
  if {{$u > 0.45}} {{
    set s [expr {{sqrt($u / 0.36)}}]
    set cx [expr {{($X0 + $X1) / 2.0}}]; set cy [expr {{($Y0 + $Y1) / 2.0}}]
    set hw [expr {{($X1 - $X0) * $s / 2.0}}]; set hh [expr {{($Y1 - $Y0) * $s / 2.0}}]
    set X0 [expr {{max([$ot_r8_core xMin], round($cx - $hw))}}]; set X1 [expr {{min([$ot_r8_core xMax], round($cx + $hw))}}]
    set Y0 [expr {{max([$ot_r8_core yMin], round($cy - $hh))}}]; set Y1 [expr {{min([$ot_r8_core yMax], round($cy + $hh))}}]
    set rg [[dict get $ot_r8_grp $g] getRegion]
    foreach bx [$rg getBoundaries] {{ odb::dbBox_destroy $bx }}
    odb::dbBox_create $rg $X0 $Y0 $X1 $Y1
    puts [format "R8_LANDING_BOX grow %s util %.2f -> %.2f,%.2f,%.2f,%.2f" $g $u [expr {{$X0/double($ot_r8_dbu)}}] [expr {{$Y0/double($ot_r8_dbu)}}] [expr {{$X1/double($ot_r8_dbu)}}] [expr {{$Y1/double($ot_r8_dbu)}}]]
    incr ot_r8_grown
    set u [expr {{$a / (double($X1 - $X0) * ($Y1 - $Y0))}}]
  }}
  if {{$u > $ot_r8_umax}} {{ set ot_r8_umax $u }}
}}
puts [format "R8_LANDING_BOX mode={mode} boxes=%d cells=%d grown=%d empty=%d max_util=%.2f" [dict size $ot_r8_box] $ot_r8_n $ot_r8_grown $ot_r8_empty $ot_r8_umax]
if {{$ot_r8_n == 0}} {{ error "R8_LANDING_BOX: no landing-local cells matched" }}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lp_spec")
    ap.add_argument("kit_dir", help="r7 kit dir with spec.json + kit.env (geometry, children, pin regions)")
    ap.add_argument("--mode", choices=["chunk", "half"], required=True)
    ap.add_argument("--util", type=float, default=0.33)
    ap.add_argument("--kit-name", required=True)
    ap.add_argument("--tcl", required=True)
    ap.add_argument("--json", required=True)
    ap.add_argument("--png")
    ap.add_argument("--anchor", action="append", default=[], help="HALF=x,y manual anchor, e.g. 0r=672,640")
    a = ap.parse_args()
    manual = {k: tuple(map(float, v.split(","))) for k, v in (s.split("=") for s in a.anchor)}
    spec = lp.load(a.lp_spec) if hasattr(lp, "load") else json.load(open(a.lp_spec))
    kd = ROOT / a.kit_dir
    kit = json.load(open(kd / "spec.json"))
    pl = Planner(spec, kit, (kd / "kit.env").read_text(), a.mode, a.util, int(spec.get("landing_chunk_bits", 24)), manual)
    H = pl.solve()
    groups = pl.place()
    grows = "\n".join(f"  {{{g['group']} {g['box'][0]:.3f} {g['box'][1]:.3f} {g['box'][2]:.3f} {g['box'][3]:.3f}}}" for g in groups)
    cm = " ".join(f"{k} {v}" for k, v in sorted(pl.cmap.items()))
    Path(a.tcl).write_text(TCL.format(kit=a.kit_name, mode=a.mode, groups=grows, cmap=cm,
                                      modedoc="one box per kept 24-bit local: hardened landing local" if a.mode == "chunk"
                                      else "one box per landing half and endpoint child: soft landing local"))
    cen = {}
    for g in groups:
        x0, y0, x1, y1 = g["box"]
        a_ = (x1 - x0) * (y1 - y0)
        s = cen.setdefault(g["half"], [0.0, 0.0, 0.0])
        s[0] += a_ * (x0 + x1) / 2
        s[1] += a_ * (y0 + y1) / 2
        s[2] += a_
    reach = {}
    for L in pl.lands:
        w, r = cen[f"u_lpl_{L['name']}_w"], cen[f"u_lpl_{L['name']}_r"]
        reach[L["name"]] = round(abs(w[0] / w[2] - r[0] / r[2]) + abs(w[1] / w[2] - r[1] / r[2]), 1)
    worst = sorted(reach.items(), key=lambda kv: -kv[1])[:6]
    print("landing ring->read centre Manhattan (um), worst: " + ", ".join(f"L{k} {v}" for k, v in worst))
    halves = {f"{k[0]}{k[1]}": dict(net=h["L"]["net"], width=h["L"]["width"], region=h["region"], how=h["how"],
                                    anchor=[round(v, 1) for v in h["anchor"]], links=[f"{x}{y}" for x, y in h["links"]])
              for k, h in sorted(H.items(), key=lambda kv: (int(kv[0][0]), kv[0][1]))}
    Path(a.json).write_text(json.dumps(dict(schema="opentallas.hbm_smh_r8.landing_boxes.v1", kit=a.kit_name, mode=a.mode,
                                            util=a.util, lp_spec=a.lp_spec, halves=halves, groups=groups, crossing_um=reach,
                                            n_boxes=len(groups)), indent=1) + "\n")
    print(f"{a.kit_name}: {len(groups)} boxes ({a.mode}); anchors: " +
          ", ".join(f"{k}={v['how'].split(':')[0]}" for k, v in halves.items()))
    if a.png:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        fig, ax = plt.subplots(figsize=(7, 12.5))
        ax.add_patch(Rectangle((0, 0), pl.G.W, pl.G.H, fill=False, lw=1))
        for m in pl.G.macro.values():
            x0, y0, x1, y1 = m["box"]
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="0.8"))
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, m["name"], ha="center", fontsize=7)
        cols = dict(u="tab:blue", upn="tab:cyan", upne="tab:olive", c="tab:green", m="tab:red", cpw="tab:purple",
                    cpe="tab:pink", xs="tab:orange", mpse="tab:brown")
        for b in groups:
            x0, y0, x1, y1 = b["box"]
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color=cols.get(b["region"], "k"), alpha=0.7, lw=0))
        if a.mode == "half":
            for b in groups:
                x0, y0, x1, y1 = b["box"]
                ax.text(x1, y1, b["group"][3:], fontsize=4)
        ax.set_xlim(-5, pl.G.W + 5)
        ax.set_ylim(-5, pl.G.H + 5)
        ax.set_aspect("equal")
        ax.set_title(f"{a.kit_name} landing boxes ({a.mode}); colour = clock region")
        fig.savefig(a.png, dpi=130, bbox_inches="tight")


if __name__ == "__main__":
    main()
