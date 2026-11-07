#!/usr/bin/env python3
"""KV-SLGLAND-1/vS 11-06 (COORD 21:4x (5), 22:4x item 4): split one over-target KV partition type at a vertical cut x = CUT
(type frame) into <T>_a (x < CUT) and <T> (x >= CUT, shifted by -CUT; keeps the type name, part name and reset / monitor /
start root).  Both halves stay in one clock region; the half <part>_a is a count-aligned RELAY of its origin <part>.

Seam forms:
  crossing ft slot     one slot per half, a new port between them, stage count of the lane UNCHANGED (the reg next to the
                       cut is moved to the cut face), so the lane latency, R8 and the compiler see no change
  flop-to-flop nets    registered "leaves" lanes o_vscut_ab / o_vscut_ba, 0 added cycles (regleaf, leaf_pinreg.py proves
                       every bit on the kit netlist).  Only nets that are flop to flop may ride them: --placement chooses
                       the contents so that holds, bind fails closed otherwise.

usage (repo root): vs_split.py CONFIG.json PLAN SIDECAR OUTDIR
CONFIG: {type, cut, a: [regex of contents in a], b: [...], widths: {ab, ba}, ab_y, window_moves: [{port, window_um}],
         map_in: <asbuilt map json>, asbuilt_in: <asbuilt json>}
writes OUTDIR/plan_c.json, eW_sidecar.json, asbuilt_map.json, asbuilt.json, report.json"""
import copy
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402
import gen_phys as GP  # noqa: E402
import clock_landing_plan as CLP  # noqa: E402
import count_align_bind as CAB  # noqa: E402

RELAY = CAB.RELAY_STAGES
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
BAD_CORE_MARGIN = 2.16
REACH = 450.0


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


class Split:
    def __init__(self, raw, cfg):
        self.raw, self.cfg = raw, cfg
        self.tn, self.cut = cfg["type"], float(cfg["cut"])
        self.t = raw["partition_types"][self.tn]
        self.W, self.H = self.t["outline_um"]
        self.parts = {p["name"]: p for p in raw["partitions"] if p["type"] == self.tn}
        self.notes, self.ft_cut = [], []
        self.bus_side = {}

    # ---- frames
    def s_of_x(self, x0, x1=None):
        x1 = x0 if x1 is None else x1
        if x1 <= self.cut + 1e-6:
            return "a"
        if x0 >= self.cut - 1e-6:
            return "b"
        raise ValueError(f"{self.tn}: x [{x0}, {x1}] straddles the cut {self.cut}")

    def sh(self, xy, s):
        return [round(xy[0] - self.cut, 6), xy[1]] if s == "b" else list(xy)

    def shr(self, r, s):
        return [round(r[0] - self.cut, 6), r[1], round(r[2] - self.cut, 6), r[3]] if s == "b" else list(r)

    def flips(self, part):
        o = self.parts[part].get("orient", "R0")
        return o in ("MY", "R180"), o in ("MX", "R180")

    def local_face(self, part, df):
        fx, fy = self.flips(part)
        if df in "NS":
            return OPP[df] if fy else df
        return OPP[df] if fx else df

    def local_x(self, part, v):
        fx, _ = self.flips(part)
        ox = self.parts[part]["origin_um"][0]
        return ox + self.W - v if fx else v - ox

    # ---- buses
    def compute_bus_sides(self):
        sides = defaultdict(set)
        for p in self.raw["ports"]:
            for e in ("src", "dst"):
                if p[e]["part"] not in self.parts or not p.get("window_um"):
                    continue
                df = p["face"] if e == "src" else OPP[p["face"]]
                lf = self.local_face(p[e]["part"], df)
                if lf == "E":
                    sides[p[e]["bus"]].add("b")
                elif lf == "W":
                    sides[p[e]["bus"]].add("a")
                else:
                    wins = [q["window_um"] for q in p.get("segments", [])] or [p["window_um"]]
                    for w in wins:
                        lo, hi = sorted(self.local_x(p[e]["part"], v) for v in w)
                        sides[p[e]["bus"]].add(self.s_of_x(lo, hi))
        for b, v in sides.items():
            if len(v) != 1:
                raise ValueError(f"{self.tn}.{b}: ports on both sides of the cut {sorted(v)}")
            self.bus_side[b] = next(iter(v))

    def side_of_bus(self, b):
        if b not in self.bus_side:
            raise ValueError(f"{self.tn}.{b}: no side (no windowed port)")
        return self.bus_side[b]

    def content_side(self, inst):
        for s in "ab":
            if any(re.fullmatch(rx, inst) for rx in self.cfg[s]):
                return s
        raise ValueError(f"{self.tn}: content {inst} matches neither side")

    # ---- the ft slots
    def split_slot(self, f, H):
        name = f["name"]
        si, so = self.side_of_bus(name + "_i"), self.side_of_bus(name + "_o")
        regs = f["regs_um"]
        sides = [self.s_of_x(r[0]) for r in regs]
        if si == so:
            if set(sides) != {si}:
                raise ValueError(f"{name}: stations {sides} outside its side {si}")
            g = copy.deepcopy(f)
            g["regs_um"] = [self.sh(r, si) for r in regs]
            if "bit_sites_um" in g:
                g["bit_sites_um"] = [[self.sh(p, si) for p in st] for st in f["bit_sites_um"]]
            H[si]["ft_slots"].append(g)
            return
        # exactly one change of side, in -> out
        k = next(i for i, s in enumerate(sides) if s != si) if so in sides else len(regs)
        if set(sides[:k]) != {si} or set(sides[k:]) - {so}:
            raise ValueError(f"{name}: stations {sides} do not cross the cut once ({si}->{so})")
        u = regs[k - 1]
        v = regs[k] if k < len(regs) else None
        tail = v or self._out_point(f)
        yc = u[1] + (tail[1] - u[1]) * (self.cut - u[0]) / (tail[0] - u[0])
        yc = round(round(yc / 0.432) * 0.432, 3)
        cutp = [self.cut, yc]
        # keep the stage count: drop the reg next to the cut, whichever leaves the shorter longest hop
        cands = []
        if k >= 2:
            first, second = regs[:k - 1], regs[k:]
            cands.append((max(man(first[-1], cutp), man(cutp, second[0] if second else self._out_point(f))), "u", first, second))
        if v is not None:
            first, second = regs[:k], regs[k + 1:]
            cands.append((max(man(first[-1], cutp), man(cutp, second[0] if second else self._out_point(f))), "v", first, second))
        if not cands:
            raise ValueError(f"{name}: no reg can move to the cut (k={k}, {len(regs)} regs)")
        hop, drop, first, second = min(cands, key=lambda c: c[0])
        ga, gb = copy.deepcopy(f), copy.deepcopy(f)
        respaced = []
        # a hop at the cut over reach: re-space the regs of that half evenly along their own path (they stay in its streets)
        outp = self._out_point(f)
        if man(first[-1], cutp) > REACH and len(first) >= 2:
            pin = first[0]
            first = respace([pin] + first[1:] + [cutp], len(first) - 1)[:-1]
            respaced.append("first")
        if man(cutp, second[0] if second else outp) > REACH and second:
            second = respace([cutp] + second + [outp], len(second))[1:-1]
            respaced.append("second")
        hop = max(man(first[-1], cutp), man(cutp, second[0] if second else outp))
        ga["regs_um"] = [self.sh(r, si) for r in first]
        gb["regs_um"] = [self.sh(cutp, so)] + [self.sh(r, so) for r in second]
        ga["stations"], gb["stations"] = len(ga["regs_um"]), len(gb["regs_um"])
        cf = "E" if si == "a" else "W"
        ga["out_face"], gb["in_face"] = cf, OPP[cf]
        if "bit_sites_um" in f and not respaced:     # bit_sites_um[j] = stage j+1 (stage 0 = the in-face flop)
            sites = f["bit_sites_um"]
            di = k - 1 if drop == "u" else k     # index in regs of the dropped reg
            keep = [(i, sites[i - 1]) for i in range(1, len(regs)) if i != di]
            ga["bit_sites_um"] = [[self.sh(p, si) for p in st] for i, st in keep if i < di]
            gb["bit_sites_um"] = [[self.sh(p, so) for p in st] for i, st in keep if i > di]
            for g in (ga, gb):
                if not g["bit_sites_um"]:
                    del g["bit_sites_um"]
        elif respaced:
            ga.pop("bit_sites_um", None)
            gb.pop("bit_sites_um", None)
        for g in (ga, gb):
            g["note"] = (g.get("note", "") + f" | vS: half of crossing {name} (cut y {yc}), stage count kept").lstrip(" |")
        H[si]["ft_slots"].append(ga)
        H[so]["ft_slots"].append(gb)
        self.ft_cut.append(dict(slot=name, width=f["width"], y=yc, first=si, stations=[ga["stations"], gb["stations"]],
                                old=f["stations"], dropped=drop, hop=round(hop, 1)))
        if hop > REACH:
            self.notes.append(f"{name}: longest hop at the cut {hop:.0f} um > {REACH}")

    def _out_point(self, f):
        """the out pin of a slot from its port windows (type frame)"""
        for p in self.raw["ports"]:
            if p["src"]["part"] in self.parts and p["src"]["bus"] == f["name"] + "_o":
                lf = self.local_face(p["src"]["part"], p["face"])
                part = p["src"]["part"]
                if lf in "NS":
                    x = self.local_x(part, sum(p["window_um"]) / 2)
                    return [x, self.H if lf == "N" else 0.0]
                oy = self.parts[part]["origin_um"][1]
                fy = self.flips(part)[1]
                v = sum(p["window_um"]) / 2
                return [self.W if lf == "E" else 0.0, oy + self.H - v if fy else v - oy]
        return f["regs_um"][-1]

    # ---- the split
    def split(self):
        t = self.t
        self.compute_bus_sides()
        A, B = {}, {}
        skip = {"outline_um", "buses", "ft_slots", "clock", "reset", "contents", "hard_cores", "internal_stations",
                "count_straps", "reset_spine_pins", "module", "note", "cells", "die_ft_bands"}
        known = {"face_pins_per_um", "face_budget_g2", "core_pg_connect", "hard", "landing_control_status_copy"}
        unknown = set(t) - skip - known
        if unknown:
            raise ValueError(f"{self.tn}: unhandled type keys {sorted(unknown)}")
        for k, v in t.items():
            if k not in skip:
                A[k], B[k] = copy.deepcopy(v), copy.deepcopy(v)
        H = {"a": A, "b": B}
        A["module"], B["module"] = self.tn + "_a_part", t.get("module", self.tn + "_part")
        A["outline_um"], B["outline_um"] = [self.cut, self.H], [round(self.W - self.cut, 6), self.H]
        for s in "ab":
            H[s]["note"] = f"KV vS 11-06 side {s} of {self.tn} (type-frame x {'<' if s == 'a' else '>='} {self.cut}) | " + t.get("note", "")
            H[s]["buses"], H[s]["hard_cores"], H[s]["contents"], H[s]["ft_slots"] = [], [], [], []
        for b in t["buses"]:
            H[self.side_of_bus(b["name"])]["buses"].append(copy.deepcopy(b))
        for h in t["hard_cores"]:
            s = self.s_of_x(h["origin_um"][0], h["origin_um"][0] + h["outline_um"][0])
            hh = copy.deepcopy(h)
            hh["origin_um"] = self.sh(h["origin_um"], s)
            H[s]["hard_cores"].append(hh)
        self.content_half = {}
        for c in t["contents"]:
            s = self.content_side(c["inst"])
            self.content_half[c["inst"]] = s
            cc = copy.deepcopy(c)
            for q in cc.get("physical_parts") or []:
                if self.s_of_x(q["origin_um"][0], q["origin_um"][0] + q["outline_um"][0]) != s:
                    raise ValueError(f"{self.tn}: {q['physical_inst']} is not on side {s} of {c['inst']}")
                q["origin_um"] = self.sh(q["origin_um"], s)
            H[s]["contents"].append(cc)
        if t.get("cells"):
            fa = float(self.cfg.get("cells_frac_a", 0.5))
            A["cells"], B["cells"] = int(t["cells"] * fa), int(t["cells"] * (1 - fa))
        for f in t["ft_slots"]:
            self.split_slot(f, H)
        for z in t.get("die_ft_bands", []):
            for s in "ab":
                lo, hi = z["span_um"]
                c0, c1 = (0.0, self.cut) if s == "a" else (self.cut, self.W)
                if z["dir"] != "NS":
                    raise ValueError(f"{self.tn}: die_ft_band dir {z['dir']}")
                l2, h2 = max(lo, c0), min(hi, c1)
                if h2 > l2:
                    zz = copy.deepcopy(z)
                    off = self.cut if s == "b" else 0.0
                    zz["span_um"] = [round(l2 - off, 6), round(h2 - off, 6)]
                    H[s].setdefault("die_ft_bands", []).append(zz)
        w = self.cfg["widths"]
        A["buses"] += [dict(name="o_vscut_ab", dir="out", width=w["ab"], kind="data"),
                       dict(name="i_vscut_ba", dir="in", width=w["ba"], kind="data")]
        B["buses"] += [dict(name="i_vscut_ab", dir="in", width=w["ab"], kind="data"),
                       dict(name="o_vscut_ba", dir="out", width=w["ba"], kind="data")]
        self.split_clock(H)
        self.split_reset(H)
        return A, B

    def split_clock(self, H):
        ck = self.t["clock"]
        drop = ("taps", "die_islands_um", "edge_clocks", "landing_contract", "tap_um", "landing_ring_wreg")
        for s in "ab":
            c = H[s]["clock"] = {k: copy.deepcopy(v) for k, v in ck.items() if k not in drop}
            c["taps"] = [copy.deepcopy(tp) | {"xy": self.sh(tp["xy"], s)} for tp in ck["taps"] if self.s_of_x(tp["xy"][0]) == s]
            if not c["taps"]:
                raise ValueError(f"{self.tn}: side {s} has no clock tap")
            c["tap_um"] = c["taps"][0]["xy"]
            c["die_islands_um"] = [self.shr(r, s) for r in ck["die_islands_um"] if self.s_of_x(r[0], r[2]) == s]
            c["edge_clocks"] = []
        lw = ck.get("landing_ring_wreg")
        if lw:
            for s in "ab":
                L = copy.deepcopy(lw)
                L["buses"] = [b for b in lw["buses"] if self.side_of_bus(b) == s]
                if L["buses"]:
                    H[s]["clock"]["landing_ring_wreg"] = L
        for e in ck.get("edge_clocks", []):
            m = re.match(r"^fclk_in_(.*)$", e["port"])
            bus = m.group(1)
            if bus.startswith("cland_dn_"):
                s = self.s_of_x(e["tap_um"][0])
            else:
                s = self.side_of_bus(bus)
            H[s]["clock"]["edge_clocks"].append(copy.deepcopy(e) | {"tap_um": self.sh(e["tap_um"], s)})
        lc = ck["landing_contract"]
        gen = ("pins", "bands", "collector_tree", "collector_local_sources", "collector_children", "collector_root_node")
        for s in "ab":
            L = H[s]["clock"]["landing_contract"] = {k: copy.deepcopy(v) for k, v in lc.items() if k not in gen}
            L["base_type"] = self.tn + "_a" if s == "a" else self.tn
            L["pins"], L["bands"] = [], {}
        root_pins = re.compile(r"^(cland_up_|fclk_out_cland_up$|cland_tstart_|cland_raw_reset_out$)")
        for p in lc["pins"]:
            m = re.match(r"^(fclk_in|fclk_out|cland_fstart_in|cland_fstart_out)_(.*)$", p["name"])
            if m and not m.group(2).startswith("cland_"):
                s = self.side_of_bus(m.group(2))
            elif root_pins.match(p["name"]):
                s = "b"
            else:
                s = self.s_of_x(p["xy_um"][0])
            xy = list(p["xy_um"])
            if self.s_of_x(xy[0]) != s:         # pin of the other side (root pins): nearest legal site on its own side
                xy[0] = self.cut + 2.16 if s == "b" else self.cut - 2.16
                xy = list(GP._snap_tap(self.plan_view(), *xy)) if False else xy
                self.notes.append(f"pin {p['name']} moved to side {s} at x {xy[0]}")
            H[s]["clock"]["landing_contract"]["pins"].append(copy.deepcopy(p) | {"xy_um": self.sh(xy, s)})
        for bus, b in lc["bands"].items():
            if bus.startswith("monitor_"):
                s = self.s_of_x(b["rect_um"][0], b["rect_um"][2])
            else:
                s = self.side_of_bus(bus)
            r = b["rect_um"]
            if self.s_of_x(r[0], r[2]) != s:
                raise ValueError(f"{self.tn}: band {bus} rect {r} is not on the side {s} of its bus")
            bb = copy.deepcopy(b)
            bb["rect_um"] = self.shr(r, s)
            if "rects_um" in bb:
                bb["rects_um"] = [self.shr(q, s) for q in b["rects_um"]]
            H[s]["clock"]["landing_contract"]["bands"][bus] = bb

    def split_reset(self, H):
        rs = self.t["reset"]
        tap = self.cfg["reset_tap"]
        for s in "ab":
            r = H[s]["reset"] = copy.deepcopy(rs)
            r["tap_um"] = tap[s]
            r["local_taps_um"] = [self.sh(p, s) for p in rs.get("local_taps_um", []) if self.s_of_x(p[0]) == s] or \
                [[8.64, 8.64]]
        # count straps are regenerated from the sidecar (CAB.strap_ties); id straps do not exist on these types
        sp = self.cfg.get("spine_pins", {})
        for s in "ab":
            if sp.get(s):
                H[s]["reset_spine_pins"] = copy.deepcopy(sp[s])


def respace(pts, n):
    """pts = polyline with fixed ends -> [start, n evenly spaced points, end] along it (Manhattan length, 0.432 grid)"""
    seg = [man(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    tot = sum(seg)
    out = [list(pts[0])]
    for k in range(1, n + 1):
        d = tot * k / (n + 1)
        i = 0
        while d > seg[i] and i < len(seg) - 1:
            d -= seg[i]
            i += 1
        p, q = pts[i], pts[i + 1]
        f = d / seg[i] if seg[i] else 0.0
        out.append([round(round((p[0] + (q[0] - p[0]) * f) / 0.432) * 0.432, 3), round(round((p[1] + (q[1] - p[1]) * f) / 0.432) * 0.432, 3)])
    out.append(list(pts[-1]))
    return out


def windows_for(items, length, per_um):
    """items [(key, pins, pref or None)] -> {key: (lo, hi)} disjoint windows along the cut face (type-frame y)"""
    MARGIN, GAP, G = 8.64, 2.16, 0.432

    def need(b):
        return max(2.16, math.ceil(b / per_um / G + 1) * G)
    out, used = {}, []
    for k, b, y in sorted(items, key=lambda i: -i[1]):
        n = need(b)
        best = None
        for c in sorted(set([y] + [u[1] + GAP + n / 2 for u in used] + [u[0] - GAP - n / 2 for u in used]),
                        key=lambda v: abs(v - y)):
            lo = round((c - n / 2) / G) * G
            if lo < MARGIN or lo + n > length - MARGIN:
                continue
            if all(lo + n + GAP <= u0 or lo >= u1 + GAP for u0, u1 in used):
                best = lo
                break
        if best is None:
            raise ValueError(f"cut face full: {k} ({b} pins)")
        out[k] = (round(best, 3), round(best + n, 3))
        used.append((best, best + n))
    return out


def main():
    cfg = json.load(open(sys.argv[1]))
    plan_path, side_path, out = sys.argv[2], sys.argv[3], Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    raw = json.load(open(plan_path))
    side = json.load(open(side_path))
    tn = cfg["type"]
    # window moves first: the neighbour ports that straddle the cut
    pid = {p["id"]: p for p in raw["ports"]}
    for m in cfg.get("window_moves", []):
        p = pid[m["port"]]
        p["window_um"] = m["window_um"]
        if m.get("segments"):
            p["segments"] = m["segments"]
        else:
            p.pop("segments", None)
        p["note"] = (p.get("note", "") + " | " + m["note"]).lstrip(" |")
    sp = Split(raw, cfg)
    A, B = sp.split()
    an = tn + "_a"
    rep = dict(type=tn, cut=sp.cut, ft_cut=sp.ft_cut, notes=sp.notes, content_half=Counter(sp.content_half.values()))
    # ---- types
    pt = {}
    for k, t in raw["partition_types"].items():
        if k == tn:
            pt[tn], pt[an] = B, A
        else:
            pt[k] = t
    raw["partition_types"] = pt
    # ---- partitions
    aname, newparts = {}, []
    for p in raw["partitions"]:
        if p["type"] != tn:
            newparts.append(p)
            continue
        ox, oy = p["origin_um"]
        fx = p.get("orient", "R0") in ("MY", "R180")
        na = p["name"] + "_a"
        aname[p["name"]] = na
        newparts.append(dict(p, origin_um=[ox if fx else round(ox + sp.cut, 6), oy]))
        newparts.append(dict(p, name=na, type=an, origin_um=[round(ox + sp.W - sp.cut, 6) if fx else ox, oy]))
    raw["partitions"] = newparts
    pmap = {p["name"]: p for p in newparts}
    # ---- ports + landing edges: endpoints follow their bus
    side_of = sp.side_of_bus

    def ep(part, bus):
        return aname[part] if part in aname and side_of(bus) == "a" else part
    for p in raw["ports"]:
        for e in ("src", "dst"):
            if p[e]["part"] in aname:
                p[e]["part"] = ep(p[e]["part"], p[e]["bus"])
    ports = {p["id"]: p for p in raw["ports"]}
    lanes = {l["id"]: l for l in raw["lanes"]}
    lmax = max(int(l["id"][1:]) for l in raw["lanes"])
    new_lat, changed_l = [], {}
    per_um = float(cfg.get("per_um", 8.0))
    for b0, a0 in aname.items():
        fx, fy = sp.flips(b0)
        oy = pmap[b0]["origin_um"][1]
        items = [(f"ft:{f['slot']}", f["width"], f["y"]) for f in sp.ft_cut]
        w = cfg["widths"]
        items += [("cut:ab", w["ab"] + 1, cfg["ab_y"]), ("cut:ba", w["ba"] + 1, cfg["ba_y"])]
        win = windows_for(items, sp.H, per_um)
        rep["cut_windows"] = win

        def port(i, src, sbus, dst, dbus, width, kind, key):
            lo, hi = win[key]
            if fy:
                lo, hi = oy + sp.H - hi, oy + sp.H - lo
            else:
                lo, hi = oy + lo, oy + hi
            src_is_a = src == a0
            lf = "E" if src_is_a else "W"
            df = OPP[lf] if fx else lf
            pr = dict(id=i, src=dict(part=src, bus=sbus), dst=dict(part=dst, bus=dbus), width=width, kind=kind, face=df,
                      layers=list(cfg.get("cut_layers", ["M4", "M6"])), window_um=[round(lo, 6), round(hi, 6)],
                      order="lsb_high" if fy else "lsb_low", note=f"KV vS 11-06: {a0} / {b0} cut face ({key})")
            raw["ports"].append(pr)
            ports[i] = pr
            return pr
        for d, s_, sb, d_, db in (("ab", a0, "o_vscut_ab", b0, "i_vscut_ab"), ("ba", b0, "o_vscut_ba", a0, "i_vscut_ba")):
            lmax += 1
            lid = f"L{lmax}"
            port(f"{lid}_0", s_, sb, d_, db, w[d], "data", "cut:" + d)
            raw["lanes"].append(dict(id=lid, ports=[f"{lid}_0"], registered="leaves",
                                     note=f"KV vS 11-06 flop-to-flop seam {b0} {d}: 0 added cycles"))
            new_lat.append(lid)
        for f in sp.ft_cut:
            first = a0 if f["first"] == "a" else b0
            second = b0 if f["first"] == "a" else a0
            hit = 0
            for l in raw["lanes"]:
                ps = l["ports"]
                for i, q in enumerate(ps):
                    pr = ports[q]
                    if pr["dst"]["part"] == first and pr["dst"]["bus"] == f["slot"] + "_i":
                        nxt = ports[ps[i + 1]] if i + 1 < len(ps) else None
                        if nxt is None or nxt["src"]["part"] != second or nxt["src"]["bus"] != f["slot"] + "_o":
                            raise ValueError(f"lane {l['id']}: {first}.{f['slot']}_i not followed by {second}.{f['slot']}_o")
                        nid = f"{q}c"
                        port(nid, first, f["slot"] + "_o", second, f["slot"] + "_i", f["width"], pr.get("kind", "data"), "ft:" + f["slot"])
                        ps.insert(i + 1, nid)
                        changed_l[l["id"]] = nid
                        hit += 1
                        break
            if hit != 1:
                raise ValueError(f"slot {f['slot']}: {hit} lanes through it")
    # ---- landing network edges follow their functional port
    ln = raw["clock"]["landing_network"]
    moved_edges = 0
    for e in ln["edges"]:
        m = re.match(r"^cland_(clk|start)__(.*)$", e["id"])
        if m and m.group(2) in ports:
            pr = ports[m.group(2)]
            for k in ("src", "dst"):
                if e[k]["part"] != pr[k]["part"]:
                    e[k]["part"] = pr[k]["part"]
                    moved_edges += 1
    rep["landing_edges_moved"] = moved_edges
    # ---- misc plan tables
    tw = raw["clock"].get("tap_window", {}).get("per_type_ps", {})
    if tn in tw:
        tw[an] = tw[tn]
    if tn in raw.get("budgets", {}).get("id_straps_in_type_types", []):
        raw["budgets"]["id_straps_in_type_types"].append(an)
    ins = raw["reset"]["in_sites"]
    xy = ins[tn]
    ins[tn] = sp.sh(xy, "b") if sp.s_of_x(xy[0]) == "b" else [8.672, xy[1]]
    ins[an] = cfg["a_in_site"]
    # ---- sidecar: region, ports, count aligned
    sd = side
    for r in sd["regions"]:
        r["parts"] += [aname[p] for p in r["parts"] if p in aname]
    for r in sd["ports"]:
        pr = ports[r["port"]]
        r["src"], r["dst"] = pr["src"]["part"], pr["dst"]["part"]
    ca = sd["count_aligned"]
    kpatch = 0
    for b0, a0 in aname.items():
        reg = ca["parts"][b0]["region"]
        ca["parts"][a0] = dict(region=reg, role="relay", src=b0, stages=RELAY)
        # bind_parts: K = sched_lat - 1 - (N_dst - N_src), N(relay) = N(origin) + RELAY; the lag L stays the plan's value
        for r in sd["ports"]:
            dk = (-RELAY if r["dst"] == a0 else 0) + (RELAY if r["src"] == a0 else 0)
            if dk and r["port"] in ca["ports"]:
                c = ca["ports"][r["port"]]
                if not c.get("tree"):
                    c["K"] = int(c["K"]) + dk
                    kpatch += 1
                else:
                    raise ValueError(f"start tree port {r['port']} lands on the relay {a0}")
    rep["ring_k_patched"] = kpatch
    # relay port: origin -> relay
    for b0, a0 in aname.items():
        ln["edges"].append(dict(id="cland_relay__" + a0, src=dict(part=b0, bus="cland_rstart_out"),
                                dst=dict(part=a0, bus="cland_rstart_in"), kind="ctl", width=1, epoch=False,
                                max_hop_um=405, source_registered=True, capture_registered=True))
    # ---- latency: recompute touched lanes; every other lane must stay
    P = S.Plan(json.loads(json.dumps(raw)), plan_path)
    lat = raw["latency"]["lanes"]
    diffs = {}
    for lid in list(changed_l) + new_lat:
        d = dict(P.lane_latency(lid))
        old = lat.get(lid)
        d.setdefault("param", (old or {}).get("param", f"LAT_{lid}"))
        if old is not None and int(old["cycles"]) != int(d["cycles"]):
            diffs[lid] = (old["cycles"], d["cycles"])
        lat[lid] = dict(old or {}, **d)
    rep["latency_changed_on_ft"] = diffs
    if diffs:
        raise ValueError(f"ft lanes changed cycles {diffs}: the seam must add none")
    # ---- reset wavefront + monitor on the new topology
    import pickle
    cache = out / "wf.pkl"
    W = pickle.load(open(cache, "rb")) if cache.exists() else RT.wf_plan(P)
    if not cache.exists():
        pickle.dump(W, open(cache, "wb"))
    root = sd["collector"]["root"]
    mon = CLP._collector_graph(P, W, root)
    old_parent = {k: v["parent"] for k, v in sd["collector"]["parts"].items()}
    rep["monitor_parent_changes"] = {k: [old_parent.get(k), v] for k, v in mon.items() if old_parent.get(k) != v}
    rep["reset_max_release"] = [sd["collector"]["reset_max_release"], W["max_release"]]
    json.dump(rep, open(out / "report_pre.json", "w"), indent=1, default=str)
    collector(raw, sd, P, W, mon, sp, aname, an, tn, rep, ports)
    # ---- count straps
    st = CAB.strap_ties(ca, raw)
    for x in (tn, an):
        info = st["types"].get(x) or {}
        raw["partition_types"][x]["count_straps"] = [dict(name=k, width=v, note="OWNER 12.15a count strap (tied at the parent)")
                                                     for k, v in sorted(info.get("straps", {}).items())]
        if not raw["partition_types"][x]["count_straps"]:
            del raw["partition_types"][x]["count_straps"]
    rep["straps"] = {x: len(raw["partition_types"][x].get("count_straps", [])) for x in (tn, an)}
    # ---- as-built map
    mj = json.load(open(cfg["map_in"]))
    M = mj["map"] if "map" in mj and "parts" not in mj else mj
    ab = json.load(open(cfg["asbuilt_in"]))

    def remap(MM):
        n = 0
        for k, v in list(MM["parts"].items()):
            if isinstance(v, str):
                if v in aname:
                    raise ValueError(f"map {k}: whole partition {v}")
                continue
            part, inst = v
            if part not in aname:
                continue
            hc = {h["inst"]: h for h in sp.t["hard_cores"]}
            if inst in sp.content_half:
                s = sp.content_half[inst]
            elif inst in hc:
                s = sp.s_of_x(hc[inst]["origin_um"][0])
            else:
                s = next((x for x in "ab" if any(re.fullmatch(rx, inst) for rx in cfg[x])), None)
                if s is None:
                    raise ValueError(f"map {k}: {part}.{inst} has no side")
            if s == "a":
                MM["parts"][k] = [aname[part], inst]
                n += 1
        return n
    rep["map_moved"] = remap(M)
    if "map" in ab and "parts" in ab["map"]:
        rep["inline_map_moved"] = remap(ab["map"])
    ab["map_file"] = cfg["map_out"]
    # bind.py reads clock_landing_table under the asbuilt base (and nowhere else): the base must be the tree holding this event
    ab["base"] = cfg["base"]
    ab["clock_landing_table"] = cfg["sidecar_out"]
    json.dump(raw, open(out / "plan_c.json", "w"), indent=1)
    json.dump(sd, open(out / "eW_sidecar.json", "w"), indent=1)
    json.dump(mj, open(out / "asbuilt_map.json", "w"), indent=1)
    json.dump(ab, open(out / "asbuilt.json", "w"), indent=1)
    json.dump(rep, open(out / "report.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in rep.items() if k not in ("cut_windows",)}, default=str)[:4000])


def pin(P, t, name, d, kind, xy, s=None):
    return dict(name=name, dir=d, kind=kind, layer=P.layer_budget["partition_signal_max"], xy_um=xy, epoch=False)


def collector(raw, sd, P, W, mon, sp, aname, an, tn, rep, ports):
    """regenerate the monitor / reset contract of the two sides (clock_landing_plan.compose rules) on the new topology"""
    C = sd["collector"]
    told = C["types"].pop(tn)
    root_part = C["root"]
    region = {}
    for r in sd["regions"]:
        for q in r["parts"]:
            region[q] = r["tag"]
    def hard_xy(pn):
        return CLP._reset_entry_xy(W, raw, P.parts[pn]["type"])
    active = {pn for pn, v in C["parts"].items() if v["active"]} | set(aname.values())
    children = defaultdict(list)
    for pn in sorted(active):
        par = mon[pn]
        if par is not None:
            end = CLP._monitor_endpoints(P, W, pn, par, hard_xy)
            children[par].append(dict(part=pn, node=end["dst_node"], xy_um=end["dst_xy"], seam=region[pn] != region[par]))
    bad = sorted(k for k, v in mon.items() if k not in aname and k not in aname.values()
                 and C["parts"].get(k, {}).get("parent") not in (v, *aname, *aname.values()))
    if bad:
        raise ValueError(f"monitor parents changed outside the split: {bad}")
    # the sides' rows
    ln = raw["clock"]["landing_network"]
    new_edges = []
    for x, s in ((tn, "b"), (an, "a")):
        t = raw["partition_types"][x]
        pn = next(q for q, v in P.parts.items() if v["type"] == x)
        tree = RT.for_type(P, x)
        lc = t["clock"]["landing_contract"]
        tapxy = {int(r["q"].split("rst_n_t")[1]): r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
        srcs = []
        bands = lc["bands"]
        for row in told["local_sources"]:
            bus = row["name"]
            if sp.side_of_bus(bus) != s:
                continue
            q = copy.deepcopy(row)
            q["band"] = bands[bus]
            q["pin_xy_um"] = sp.sh(row["pin_xy_um"], s)
            q["xy_um"] = sp.sh(row["xy_um"], s)
            q["tap"] = min(range(RT.consumer_count(tree)), key=lambda i: abs(tapxy[i][0] - q["xy_um"][0]) + abs(tapxy[i][1] - q["xy_um"][1]))
            srcs.append(q)
        ch = sorted(children[pn], key=lambda c: (c["xy_um"], c["seam"], c["part"]))
        rows = [dict(c, index=i, ready=f"cland_dn_ready_{i}", fault=f"cland_dn_fault_{i}") for i, c in enumerate(ch)]
        # pins of the monitor children: renumber; drop the old ones first
        lc["pins"] = [p for p in lc["pins"] if not re.match(r"^(cland_dn_|fclk_in_cland_dn_|cland_up_|fclk_out_cland_up$)", p["name"])]
        t["clock"]["edge_clocks"] = [e for e in t["clock"]["edge_clocks"] if not e["port"].startswith("fclk_in_cland_dn_")]
        oldbands = {k: v for k, v in bands.items() if k.startswith("monitor_")}
        for k in oldbands:
            del bands[k]
        for c in rows:
            i = c["index"]
            xy = c["xy_um"]
            for j, kind in enumerate(("ready", "fault")):
                lc["pins"].append(pin(P, t, f"cland_dn_{kind}_{i}", "in", "ctl", _edge(xy, t, 2.16 * (j + 2))))
            if c["seam"]:
                ep_ = _edge(xy, t, 2.16)
                lc["pins"].append(pin(P, t, f"fclk_in_cland_dn_{i}", "in", "clock", ep_))
                t["clock"]["edge_clocks"].append(dict(port=f"fclk_in_cland_dn_{i}", tap_um=ep_, period_mult=1,
                                                      note="reverse monitor forwarded clock; 2bit landed ring, boot-only cost"))
                used = [v["rect_um"] for v in bands.values() if v.get("rect_um")]
                t["_cland_geom"] = {f"cland_dn_ready_{i}": dict(name=f"cland_dn_ready_{i}", face=CLP._face(t, ep_), width=2,
                                    window_um=[ep_[1] - .216, ep_[1] + .216] if CLP._face(t, ep_) in "EW" else [ep_[0] - .216, ep_[0] + .216])}
                band = CLP._storage_band(t, f"cland_dn_ready_{i}", 2, used, has_epoch=False,
                                         phy=CLP.phy_supply_rects(P, x), resets=CLP._reset_sites_for_type(raw, x, tree, x))
                del t["_cland_geom"]
                band["instance"] = f"u_cland_monitor_{i}"
                bands[f"monitor_{i}"] = band
        par = mon[pn]
        up = CLP._monitor_endpoints(P, W, pn, par, hard_xy) if par is not None else None
        up_seam = par is not None and region[pn] != region[par]
        if up:
            for j, kind in enumerate(("ready", "fault")):
                lc["pins"].append(pin(P, t, f"cland_up_{kind}", "out", "ctl", _edge(up["src_xy"], t, 2.16 * (j + 2))))
            if up_seam:
                q = pin(P, t, "fclk_out_cland_up", "out", "clock", _edge(up["src_xy"], t, 2.16))
                q.update(source_clock_port="clk")
                lc["pins"].append(q)
        # relay pins beside the cut
        yr = sp.cfg["relay_y"]
        if s == "b":
            lc["pins"].append(pin(P, t, "cland_rstart_out", "out", "ctl", [2.16, yr]))
        else:
            lc["pins"].append(pin(P, t, "cland_rstart_in", "in", "ctl", [round(sp.cut - 2.16, 6), yr]))
        # forwarded clock outputs: nearest tap of THIS side
        roots = GP.clock_pins(P, x)
        for q in lc["pins"]:
            if q["kind"] == "clock" and q["dir"] == "out":
                tap = min(roots, key=lambda r: abs(r[1] - q["xy_um"][0]) + abs(r[2] - q["xy_um"][1]))[0]
                q["source_clock_port"] = "clk"
                q["source_clock_tap"] = tap
        lc["collector_tree"] = tree
        lc["collector_root_node"] = up["src_node"] if up else f"rst_n_t{RT.leaf_tap(P, x)}"
        lc["collector_local_sources"] = srcs
        lc["collector_children"] = rows
        inputs = sorted(q["name"] for q in srcs)
        outputs = sorted(b for b in told["mask"]["outputs"] if sp.side_of_bus(b) == s)
        mask = dict(told["mask"])
        mask.update(inputs=inputs, outputs=outputs, active=True, observer=False, up_xy=up["src_xy"] if up else None,
                    up_seam=up_seam, children=[dict(xy_um=c["xy_um"], seam=c["seam"]) for c in ch])
        C["types"][x] = dict(told, base_type=x, mask=mask, tree=tree, local_sources=srcs, children=rows, up_parent=par,
                             reset_entry_um=W["types"][x]["in_um"], bands=bands, collector_root_node=lc["collector_root_node"],
                             collector_root_xy=up["src_xy"] if up else told.get("collector_root_xy"))
        C["parts"][pn] = dict(type=x, parent=par, active=True)
        C["base_type_by_part"][pn] = x
        # die edges of this part's children
        for c in rows:
            for kind in ("ready", "fault"):
                new_edges.append(dict(id=f"cland_mon_{kind}__{c['part']}", src=dict(part=c["part"], bus="cland_up_" + kind),
                                      dst=dict(part=pn, bus=f"cland_dn_{kind}_{c['index']}"), kind="ctl", width=1, epoch=False,
                                      max_hop_um=405, source_registered=True, capture_registered=True))
            if c["seam"]:
                new_edges.append(dict(id="cland_mon_clk__" + c["part"], src=dict(part=c["part"], bus="fclk_out_cland_up"),
                                      dst=dict(part=pn, bus=f"fclk_in_cland_dn_{c['index']}"), kind="clock", width=1, epoch=False,
                                      max_hop_um=405, source_registered=False, capture_registered=False))
    ids = {e["id"] for e in new_edges}
    ln["edges"] = [e for e in ln["edges"] if e["id"] not in ids] + new_edges
    # the monitor edges of the die
    C["edges"] = [e for e in C["edges"] if e["dst"] not in aname and e["src"] not in aname.values()]
    for b0, a0 in aname.items():
        C["edges"] += [dict(src=c["part"], dst=q, dst_index=i, seam=c["seam"], hop_um=0.0, data_cycles_added=0,
                            boot_transport_extra_cycles=3 if c["seam"] else CLP.STATUS_FACE_CYCLES)
                       for q in (b0, a0) for i, c in enumerate(sorted(children[q], key=lambda c: (c["xy_um"], c["seam"], c["part"])))]
    C["reset_max_release"] = W["max_release"]
    bb = C["boot_budget"]
    bb["raw_reset_release_max_cycles"] = W["max_release"]
    for b0, a0 in aname.items():
        bb["local_registered_depths"][a0] = bb["local_registered_depths"][b0]


def _edge(xy, t, shift):
    """a monitor pin near the point xy, on the nearest face, 2.16 inside the edge, shifted along that face"""
    w, h = t["outline_um"]
    x, y = xy
    f = min(((x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")))[1]
    if f in "EW":
        return [2.16 if f == "W" else round(w - 2.16, 6), round(min(max(y + shift, 2.16), h - 2.16), 3)]
    return [round(min(max(x + shift, 2.16), w - 2.16), 3), 2.16 if f == "S" else round(h - 2.16, 6)]


if __name__ == "__main__":
    main()
