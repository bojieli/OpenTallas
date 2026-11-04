#!/usr/bin/env python3
"""HG-SPLIT 11-03 (DIE-KV-64 ruling): soft split of the 8 KV head-group types over the 400k native-cell cap.

Every kv3_hg* type (1278.72 x 1520.64) is cut at type-frame y = CUT into two partition types <T>_a (y < CUT) and <T>
(y >= CUT, shifted down by CUT; b keeps the type name and the collector root); every hg_<Q>_<k> partition becomes
hg_<Q>_<k> (half b, same name) + hg_<Q>_<k>_a (half a).  The half of every element is fixed by geometry or by the H2opt half map (hg_h2opt/<T>_H2opt.json, key H:
"PORT:<bus>" / "HC:u_bound.<core>" / bound leaf -> a|b; v1* reuse the v3 map with owner -> a, efault -> b):

  buses, ft slots, landing pins/bands/edge clocks   the bus's half (H PORT, else the face/window of its port)
  hard cores, clock taps (explicit, old R4 grid)     their y (die positions unchanged: the die clock tree keeps its leaves)
  contents                                           H (bound leaf u_<inst>), else the hard core it is grouped into
  crossing ft slot (ft2 on v3/v1*)                   one slot per half; a new port a.ft2_o -> b.ft2_i (+1 in-face station)
  crossing internal-station legs (b -> a)            one leg per half; a new lane b.o_<bus> -> a.i_<bus> (same names, so
                                                     bind forwards the bits by name), fixed_cycles = b stations; the
                                                     out lane keeps the a stations (total stations unchanged, +2 boundary)
  every other a <-> b net                            two generic cut lanes per partition, o_hgcut_ab / o_hgcut_ba
                                                     (+2 each, as bind emits them; widths from --cut-widths)
The cut is CUT = 673.92 (8.64 lattice; 665.28 = the H2opt 667.44 snapped down cuts the die-clock islands at y 665.0 of
every HG type; 673.92 cuts no core, macro, island, station or band).  The ep SRAM macros sc0/sc1 (ep is half a) move from
y 682.6 / 812.2 into the half-a street between the core rows (x 570.24, y 240.84 / 287.28).

Both halves stay in ONE landing region (eW_sidecar regions[].parts += hg_*_a): the cut lanes are same-region plain
boundary pairs (no landing ring); every landed port keeps its row with the moved endpoint renamed.

usage (repo root): hg_split.py PLAN SIDECAR MAP_JSON OUTDIR [--cut-widths J]
  writes OUTDIR/plan_c.json, eW_sidecar.json, asbuilt_map.json (map.parts remapped), report.json
The reset wavefront / landing collector entries are recomputed by hg_split_collector.py on the output."""
import argparse
import copy
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S  # noqa: E402

CUT = 673.92
HG = ["kv3_hg", "kv3_hg_v1", "kv3_hg_v1p2", "kv3_hg_v1p3", "kv3_hg_v1p4", "kv3_hg_v1p5", "kv3_hg_v1p6", "kv3_hg_v3"]
HMAP = {tn: ("kv3_hg" if tn == "kv3_hg" else "kv3_hg_v3") for tn in HG}
# contents the H2opt map does not name (single small leaves); half = the half of their main connection
CONTENT_OVERRIDE = {"u_id_row": "b", "u_id_next": "a", "u_fch": "b"}
MAP_INST_HALF = {"u_id": "b"}   # asbuilt_map_binder2 idhg_*: the id source of the die netlist (u_id_row in half b; straps elsewhere)
# ep SRAM macros moved into half a (ep is a): free street between the core rows y 233.28..336.96, channel x 552.96..656.64
PP_MOVE = {"u_bound.u_astk_u_strip_u_strip_g_ep_p_u_ep.u_sc1": [570.24, 240.84],
           "u_bound.u_astk_u_strip_u_strip_g_ep_p_u_ep.u_sc0": [570.24, 287.28]}
CUT_LAYERS = ["M5", "M7"]
COLLECTOR_PIN = re.compile(r"^(cland_up_|cland_dn_|fclk_out_cland_up$|fclk_in_cland_dn_)")
SITE = 0.216
EPS = 1e-6


def half_of_y(y0, y1=None):
    y1 = y0 if y1 is None else y1
    if y1 <= CUT + EPS:
        return "a"
    if y0 >= CUT - EPS:
        return "b"
    raise ValueError(f"[{y0}, {y1}] straddles the cut {CUT}")


def sh(xy, side):
    return [xy[0], round(xy[1] - CUT, 6)] if side == "b" else list(xy)


def shr(r, side):
    return [r[0], round(r[1] - CUT, 6), r[2], round(r[3] - CUT, 6)] if side == "b" else list(r)


def half_type(tn, s):
    """ruling 18:09: half b keeps the type name, half a is <type>_a"""
    return tn + "_a" if s == "a" else tn


def load_h(tn):
    H = dict(json.load(open(HERE / "hg_h2opt" / f"{HMAP[tn]}_H2opt.json"))["H"])
    return H


class TypeSplit:
    def __init__(self, raw, tn, parts_of_type):
        self.raw, self.tn = raw, tn
        self.t = raw["partition_types"][tn]
        self.H = load_h(tn)
        self.W, self.Ht = self.t["outline_um"]
        assert abs(self.Ht - 1520.64) < EPS and abs(self.W - 1278.72) < EPS, (tn, self.t["outline_um"])
        self.parts = parts_of_type
        self.ports = raw["ports"]
        self.bus_side = {}
        self.bus_conflicts = {}
        self.notes = []

    # ---- halves of buses ---------------------------------------------------------------------------------------
    def local_face(self, part, df):
        o = self.raw_part(part).get("orient", "R0")
        flipx, flipy = o in ("MY", "R180"), o in ("MX", "R180")
        if df in "NS":
            return {"N": "S", "S": "N"}[df] if flipy else df
        return {"E": "W", "W": "E"}[df] if flipx else df

    def raw_part(self, part):
        return next(p for p in self.raw["partitions"] if p["name"] == part)

    def geom_side(self, bus):
        """the half a bus's ports put it in (all instances, both ends must agree)."""
        sides = set()
        for p in self.ports:
            for e in ("src", "dst"):
                if p[e]["part"] in self.parts and p[e]["bus"] == bus:
                    df = p["face"] if e == "src" or p["src"]["part"] == "@die" else {"N": "S", "S": "N", "E": "W", "W": "E"}[p["face"]]
                    lf = self.local_face(p[e]["part"], df)
                    if lf == "N":
                        sides.add("b")
                    elif lf == "S":
                        sides.add("a")
                    else:
                        part = self.raw_part(p[e]["part"])
                        oy = part["origin_um"][1]
                        flip = part.get("orient", "R0") in ("MX", "R180")
                        ly = [(oy + self.Ht - v) if flip else (v - oy) for v in p["window_um"]]
                        sides.add(half_of_y(min(ly), max(ly)))
        if len(sides) > 1:
            raise ValueError(f"{self.tn}.{bus}: ports put it in both halves {sides}")
        return next(iter(sides), None)

    def side_of_bus(self, bus):
        if bus in self.bus_side:
            return self.bus_side[bus]
        g = self.geom_side(bus)
        h = self.H.get("PORT:" + bus)
        if g and h and g != h:
            # the port's face decides the bus half; its logic (H) is in the other half: those bits cross the cut
            # (generic cut lane, +2 as bind emits it) -> listed for the latency delta table
            self.bus_conflicts[bus] = dict(port_half=g, logic_half=h)
        s = g or h
        if s is None:
            raise ValueError(f"{self.tn}.{bus}: no half (no port, not in H)")
        self.bus_side[bus] = s
        return s

    # ---- contents ----------------------------------------------------------------------------------------------
    def core_members(self):
        mem = {}
        for h in self.t["hard_cores"]:
            m = re.match(r'"?\w+: ([^;]*);', h.get("note", ""))
            if m and h["inst"].startswith("head"):
                for x in m.group(1).split(" + "):
                    mem[x.strip()] = h["inst"]
        return mem

    def core_side(self, h):
        return half_of_y(h["origin_um"][1], h["origin_um"][1] + h["outline_um"][1])

    def content_side(self, inst, mem, cores):
        k = "u_" + inst.replace("__", "_")
        if k in self.H:
            return self.H[k]
        for m, ci in mem.items():
            if inst == m or inst.startswith(m + "__"):
                return self.core_side(cores[ci])
        if inst in CONTENT_OVERRIDE:
            return CONTENT_OVERRIDE[inst]
        raise ValueError(f"{self.tn}: content {inst} has no half")

    # ---- the split ---------------------------------------------------------------------------------------------
    def split(self, cut_widths):
        t = self.t
        A, B = {}, {}
        skip = {"outline_um", "buses", "ft_slots", "clock", "reset", "contents", "hard_cores", "internal_stations",
                "count_straps", "reset_spine_pins", "module", "note", "cells"}
        for k, v in t.items():
            if k not in skip:
                A[k] = copy.deepcopy(v)
                B[k] = copy.deepcopy(v)
        unknown = set(t) - skip - {"face_pins_per_um", "face_budget_g2", "core_pg_connect", "hard"}
        if unknown:
            raise ValueError(f"{self.tn}: unhandled type keys {sorted(unknown)}")
        H = {"a": A, "b": B}
        A["module"], B["module"] = self.tn + "_a_part", t.get("module", self.tn + "_part")
        A["outline_um"], B["outline_um"] = [self.W, CUT], [self.W, round(self.Ht - CUT, 6)]
        for s in "ab":
            H[s]["note"] = (f"HG-SPLIT 11-03 (DIE-KV-64 ruling) half {s} of {self.tn} (type-frame y "
                            f"{'< ' if s == 'a' else '>= '}{CUT}{', shifted by -' + str(CUT) if s == 'b' else ''}) | "
                            + t.get("note", ""))
        # buses
        for s in "ab":
            H[s]["buses"] = []
        for b in t["buses"]:
            H[self.side_of_bus(b["name"])]["buses"].append(copy.deepcopy(b))
        # hard cores
        cores = {h["inst"]: h for h in t["hard_cores"]}
        for s in "ab":
            H[s]["hard_cores"] = []
        for h in t["hard_cores"]:
            s = self.core_side(h)
            hh = copy.deepcopy(h)
            hh["origin_um"] = sh(h["origin_um"], s)
            if self.H.get("HC:u_bound.u_" + h["inst"], s) != s:
                raise ValueError(f"{self.tn}: core {h['inst']} H half differs from its geometry")
            H[s]["hard_cores"].append(hh)
        # contents
        mem = self.core_members()
        self.content_half = {}
        for s in "ab":
            H[s]["contents"] = []
        for c in t["contents"]:
            s = self.content_side(c["inst"], mem, cores)
            self.content_half[c["inst"]] = s
            cc = copy.deepcopy(c)
            for q in cc.get("physical_parts") or []:
                if q["physical_inst"] in PP_MOVE and s == "a":
                    old = q["origin_um"]
                    q["origin_um"] = list(PP_MOVE[q["physical_inst"]])
                    q["note"] = q.get("note", "") + f" | HG-SPLIT: moved from {old} into half a (ep is half a)"
                y0 = q["origin_um"][1]
                if half_of_y(y0, y0 + q["outline_um"][1]) != s:
                    raise ValueError(f"{self.tn}: {q['physical_inst']} lies outside the half {s} of {c['inst']}")
                q["origin_um"] = sh(q["origin_um"], s)
            H[s]["contents"].append(cc)
        # ft slots
        self.ft_cut = []
        for s in "ab":
            H[s]["ft_slots"] = []
        for f in t["ft_slots"]:
            ys = [r[1] for r in f["regs_um"]]
            sides = {half_of_y(y) for y in ys}
            si, so = self.side_of_bus(f["name"] + "_i"), self.side_of_bus(f["name"] + "_o")
            if si == so:
                if sides != {si}:
                    raise ValueError(f"{self.tn}.{f['name']}: stations {sides} outside its half {si}")
                g = copy.deepcopy(f)
                g["regs_um"] = [sh(r, si) for r in f["regs_um"]]
                if "bit_sites_um" in g:
                    g["bit_sites_um"] = [[sh(p, si) for p in st] for st in f["bit_sites_um"]]
                H[si]["ft_slots"].append(g)
                continue
            if (f["in_face"], f["out_face"]) != ("S", "N") or (si, so) != ("a", "b"):
                raise ValueError(f"{self.tn}.{f['name']}: crossing slot form {f['in_face']}->{f['out_face']} {si}->{so}")
            regs = f["regs_um"]
            k = max(i for i, r in enumerate(regs) if r[1] < CUT)          # last station in a
            (x0, y0), (x1, y1) = regs[k], regs[k + 1]
            xc = x0 + (x1 - x0) * (CUT - y0) / (y1 - y0)
            xc = round(round(xc / 0.432) * 0.432, 3)
            ga, gb = copy.deepcopy(f), copy.deepcopy(f)
            ga["regs_um"] = [list(r) for r in regs[:k + 1]]
            ga["stations"] = len(ga["regs_um"])
            gb["regs_um"] = [[xc, 0.0]] + [sh(r, "b") for r in regs[k + 1:]]
            gb["stations"] = len(gb["regs_um"])
            if "bit_sites_um" in f:            # bit_sites_um[j] = stage j+1 (stage 0 = the in-face flop)
                ga["bit_sites_um"] = [list(map(list, st)) for st in f["bit_sites_um"][:k]]
                gb["bit_sites_um"] = [[sh(p, "b") for p in st] for st in f["bit_sites_um"][k:]]
            for g in (ga, gb):
                g["note"] = (g.get("note", "") + f" | HG-SPLIT: half of the crossing {f['name']} (cut x {xc})").lstrip(" |")
            H["a"]["ft_slots"].append(ga)
            H["b"]["ft_slots"].append(gb)
            self.ft_cut.append(dict(slot=f["name"], x=xc, width=f["width"], stations=[ga["stations"], gb["stations"]],
                                    old=f["stations"]))
        # internal stations
        self.leg_cut = {}
        for s in "ab":
            H[s]["internal_stations"] = []
        rows = t.get("internal_stations", [])
        bw = {b["name"]: b for b in t["buses"]}
        for r in rows:
            bus = r["conn"][4:]
            pts = [r["from_um"]] + r["regs_um"] + [r["to_um"]]
            sides = [half_of_y(p[1]) for p in pts]
            if len(set(sides)) == 1:
                rr = copy.deepcopy(r)
                s = sides[0]
                for k in ("from_um", "to_um"):
                    rr[k] = sh(r[k], s)
                rr["regs_um"] = [sh(p, s) for p in r["regs_um"]]
                H[s]["internal_stations"].append(rr)
                continue
            if not (r["from_um"][1] > CUT and r["to_um"][1] < CUT and re.match(r"bus i_", r.get("launch", ""))
                    and self.side_of_bus(bus) == "a"):
                raise ValueError(f"{self.tn}: internal leg {r['conn']} crossing form not N(b) -> S(a)")
            regs = r["regs_um"]
            ia = [p for p in regs if p[1] < CUT]
            ib = [p for p in regs if p[1] >= CUT]
            if regs != ib + ia:
                raise ValueError(f"{self.tn}: internal leg {r['conn']} stations not monotone over the cut")
            q0 = ib[-1] if ib else r["from_um"]
            q1 = ia[0] if ia else r["to_um"]
            xc = q0[0] + (q1[0] - q0[0]) * (CUT - q0[1]) / (q1[1] - q0[1])
            key = (bus, tuple(map(tuple, regs)), tuple(r["from_um"]), tuple(r["to_um"]))
            names_all = {b["name"] for b in t["buses"]}
            ib_name = ("i_" if "i_" + bus[2:] not in names_all else "i_hgx_") + bus[2:]   # a's new in bus
            launch = r.get("launch", "").split()[-1]
            if self.side_of_bus(launch) != "b":
                raise ValueError(f"{self.tn}: internal leg {r['conn']} launch {launch} not in half b")
            rb = dict(conn="bus:" + bus, from_um=sh(r["from_um"], "b"), to_um=[round(xc, 3), 0.0],
                      regs_um=[sh(p, "b") for p in ib], launch=r["launch"], capture="face bus " + bus,
                      note=f"HG-SPLIT: half b of {r['conn']} (to the cut, {len(ib)} of {len(regs)} stations)")
            ra = dict(conn="bus:" + bus, from_um=[round(xc, 3), CUT], to_um=list(r["to_um"]),
                      regs_um=[list(p) for p in ia], launch="bus " + ib_name, capture=r.get("capture", "face bus " + bus),
                      note=f"HG-SPLIT: half a of {r['conn']} (from the cut, {len(ia)} of {len(regs)} stations)")
            for k in ("bits",):
                if k in r:
                    rb[k] = ra[k] = r[k]
            H["b"]["internal_stations"].append(rb)
            H["a"]["internal_stations"].append(ra)
            if bus in self.leg_cut and self.leg_cut[bus]["key"] != key:
                raise ValueError(f"{self.tn}: two different crossing legs on {bus}")
            self.leg_cut[bus] = dict(key=key, x=round(xc, 3), nb=len(ib), na=len(ia), width=bw[bus]["width"], a_in=ib_name,
                                     kind=bw[bus].get("kind", "data"))
        for bus, L in self.leg_cut.items():
            ib_name = L["a_in"]
            H["b"]["buses"].append(dict(name=bus, dir="out", width=L["width"], kind=L["kind"]))
            H["a"]["buses"].append(dict(name=ib_name, dir="in", width=L["width"], kind=L["kind"]))
        for s in "ab":
            if not H[s]["internal_stations"]:
                del H[s]["internal_stations"]
        # generic cut buses
        self.cut_w = cut_widths
        H["a"]["buses"] += [dict(name="o_hgcut_ab", dir="out", width=cut_widths["ab"], kind="data"),
                            dict(name="i_hgcut_ba", dir="in", width=cut_widths["ba"], kind="data")]
        H["b"]["buses"] += [dict(name="i_hgcut_ab", dir="in", width=cut_widths["ab"], kind="data"),
                            dict(name="o_hgcut_ba", dir="out", width=cut_widths["ba"], kind="data")]
        # clock
        ck = t["clock"]
        Pl = S.Plan(self.raw, None)
        grid = S.tap_grid(Pl, self.tn)
        for s in "ab":
            c = H[s]["clock"] = {k: copy.deepcopy(v) for k, v in ck.items()
                                 if k not in ("taps", "die_islands_um", "edge_clocks", "landing_contract", "tap_um")}
            c["tap_mode"] = "explicit"
            gt = [(n, x, y) for n, x, y in grid if half_of_y(y) == s]
            c["taps"] = [dict(name="clk" if i == 0 else f"clk_t{i}", xy=sh([x, y], s),
                              note=f"HG-SPLIT: {self.tn} R4 grid tap {n} (die position unchanged)")
                         for i, (n, x, y) in enumerate(gt)]
            c["taps"] += [copy.deepcopy(tp) | {"xy": sh(tp["xy"], s)} for tp in ck["taps"]
                          if half_of_y(tp["xy"][1]) == s]
            c["tap_um"] = c["taps"][0]["xy"]
            c["die_islands_um"] = [shr(r, s) for r in ck["die_islands_um"] if half_of_y(r[1], r[3]) == s]
            c["edge_clocks"] = []
        self.tapmap = {n: (half_of_y(y), i) for s in "ab" for i, (n, x, y) in
                       enumerate([g for g in grid if half_of_y(g[2]) == s])}
        for e in ck.get("edge_clocks", []):
            if COLLECTOR_PIN.match(e["port"]):
                continue                       # monitor children: regenerated by collector()
            bus = re.sub(r"^fclk_in_", "", e["port"])
            s = self.side_of_bus(bus)
            H[s]["clock"]["edge_clocks"].append(copy.deepcopy(e) | {"tap_um": sh(e["tap_um"], s)})
        lc = ck["landing_contract"]
        for s in "ab":
            L = H[s]["clock"]["landing_contract"] = {k: copy.deepcopy(v) for k, v in lc.items()
                                                     if k not in ("pins", "bands", "collector_tree", "collector_local_sources",
                                                                  "collector_children", "collector_root_node")}
            L["base_type"] = half_type(self.tn, s)
            L["pins"], L["bands"] = [], {}
        for p in lc["pins"]:
            if COLLECTOR_PIN.match(p["name"]):
                continue                       # monitor up / children pins: regenerated by collector()
            m = re.match(r"^(fclk_in|fclk_out|cland_fstart_in|cland_fstart_out)_(.*)$", p["name"])
            s = self.side_of_bus(m.group(2)) if m else half_of_y(p["xy_um"][1])
            q = copy.deepcopy(p) | {"xy_um": sh(p["xy_um"], s)}
            if "source_clock_tap" in q:        # tap names are renumbered per half
                hs, i = self.tapmap[q["source_clock_tap"]]
                if hs != s:
                    raise ValueError(f"{self.tn}: pin {p['name']} (half {s}) forwards tap {q['source_clock_tap']} of half {hs}")
                q["source_clock_tap"] = "clk" if i == 0 else f"clk_t{i}"
            H[s]["clock"]["landing_contract"]["pins"].append(q)
        for bus, b in lc["bands"].items():
            if bus.startswith("monitor_"):
                continue
            s = self.side_of_bus(bus)
            bb = copy.deepcopy(b)
            bb["rect_um"] = shr(b["rect_um"], s)
            if "rects_um" in bb:
                bb["rects_um"] = [shr(r, s) for r in b["rects_um"]]
            H[s]["clock"]["landing_contract"]["bands"][bus] = bb
        # reset
        rs = t["reset"]
        s0 = half_of_y(rs["tap_um"][1])
        for s in "ab":
            r = H[s]["reset"] = copy.deepcopy(rs)
            if s == s0:
                r["tap_um"] = sh(rs["tap_um"], s)
            else:
                r["tap_um"] = RESET_TAP[s]
            r["local_taps_um"] = [sh(p, s) for p in rs.get("local_taps_um", []) if half_of_y(p[1]) == s] or \
                [[8.64, 8.64]]
        # count straps: strap_ca_k_<bus> follow the bus, other straps go to both halves
        for s in "ab":
            H[s]["count_straps"] = []
        for st in t.get("count_straps", []):
            m = re.match(r"^strap_ca_k_(.*)$", st["name"])
            if m:
                H[self.side_of_bus(m.group(1))]["count_straps"].append(copy.deepcopy(st))
            else:
                for s in "ab":
                    H[s]["count_straps"].append(copy.deepcopy(st))
        # reset spine pins: wrapper pins of a content -> the content's half, nearest 8.64 lattice point to its reset tap
        for s in "ab":
            H[s]["reset_spine_pins"] = []
        for rp in t.get("reset_spine_pins", []):
            inst = re.sub(r"^ri_", "", rp["name"])
            inst = re.sub(r"_rst_n$", "", inst)
            s = next((self.content_half[c] for c in self.content_half if "u_" + c.replace("__", "_") == "u_" + inst
                      or c.replace("__", "_") == inst), None)
            if s is None:
                raise ValueError(f"{self.tn}: reset spine pin {rp['name']} names no content")
            q = copy.deepcopy(rp)
            q["sites_um"] = [sh(p, s) if half_of_y(p[1]) == s else list(SPINE_SITE[s]) for p in rp["sites_um"]]
            H[s]["reset_spine_pins"].append(q)
        for s in "ab":
            if not H[s]["reset_spine_pins"]:
                del H[s]["reset_spine_pins"]
            if not H[s]["count_straps"]:
                del H[s]["count_straps"]
        return A, B


# half-local reset taps (8.64 lattice, channel x 639.36 between the core columns, clear of cores / macros / islands)
RESET_TAP = {"a": [639.36, 285.12], "b": [639.36, 86.4]}
SPINE_SITE = {"a": [630.72, 285.12], "b": [630.72, 86.4]}


def type_window(lo_hi, part, raw_part, t_out, face_local):
    """type-frame cut-face window -> die (face, window, order) for one instance (schema.geom_to_die)."""
    w, h = t_out
    o = raw_part.get("orient", "R0")
    ox, oy = raw_part["origin_um"]
    flipx, flipy = o in ("MY", "R180"), o in ("MX", "R180")
    df = {"N": "S", "S": "N"}[face_local] if flipy else face_local
    a, b = lo_hi
    if flipx:
        a, b = w - b, w - a
        order = "lsb_high"
    else:
        order = "lsb_low"
    return df, [round(ox + a, 6), round(ox + b, 6)], order


def windows_for(items, width_um, per_um):
    """items [(key, pins, x_pref or None)] -> {key: [(lo, hi, pins), ...]} disjoint type-frame windows on
    [MARGIN, width - MARGIN].  Fixed-position items (stations' x) first, one window centred on x_pref; the generic cut
    buses then fill the free gaps left to right, split over several windows (port segments) where a gap is short."""
    MARGIN, GAP, G = 8.64, 2.16, 0.432

    def need(b):
        return max(2.16, math.ceil(b / per_um / G + 1) * G)

    def cap(L):
        return int(math.floor((L / G - 1) * G * per_um + 1e-9))
    out, used = {}, []
    for k, b, x in sorted([i for i in items if i[2] is not None], key=lambda i: i[2]):
        n = need(b)
        lo = max(MARGIN, round((x - n / 2) / G) * G)
        for u0, u1 in sorted(used):
            if lo < u1 + GAP and lo + n > u0 - GAP:
                lo = u1 + GAP
        if lo + n > width_um - MARGIN:
            raise ValueError(f"cut face: {k} does not fit at x {x}")
        out[k] = [(round(lo, 3), round(lo + n, 3), b)]
        used.append((lo, lo + n))
    free, cur = [], MARGIN
    for u0, u1 in sorted(used):
        if u0 - GAP > cur:
            free.append([cur, u0 - GAP])
        cur = max(cur, u1 + GAP)
    if width_um - MARGIN > cur:
        free.append([cur, width_um - MARGIN])
    for k, b, x in [i for i in items if i[2] is None]:
        left, segs = b, []
        for f in free:
            if left <= 0:
                break
            L = f[1] - f[0]
            if L < 4.32:
                continue
            take = min(left, cap(L))
            if take <= 0:
                continue
            n = need(take) if take == left else L
            segs.append((round(f[0], 3), round(f[0] + n, 3), take))
            f[0] = f[0] + n + GAP
            left -= take
        if left > 0:
            raise ValueError(f"cut face full: {k} has {left} of {b} pins without a window at {per_um}/um")
        out[k] = segs
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("sidecar")
    ap.add_argument("map_json", help="asbuilt map file (parts, rules) or an asbuilt.json with an inline map")
    ap.add_argument("outdir")
    ap.add_argument("--cut-widths", help="JSON {type: {ab: n, ba: n}} (default: H2opt estimate + 15 pct)")
    ap.add_argument("--per-um", type=float, default=8.0, help="cut-face pin density used to size the windows")
    a = ap.parse_args()
    raw = json.load(open(a.plan))
    orig = copy.deepcopy(raw)
    side = json.load(open(a.sidecar))
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    cw = json.load(open(a.cut_widths)) if a.cut_widths else json.load(open(HERE / "cut_widths_est.json"))
    parts_by_type = defaultdict(list)
    for p in raw["partitions"]:
        parts_by_type[p["type"]].append(p["name"])
    rep = dict(cut_um=CUT, types={}, ports_added=[], lanes_added=[], lanes_changed={}, notes=[])
    splits = {}
    for tn in HG:
        ts = TypeSplit(raw, tn, set(parts_by_type[tn]))
        A, B = ts.split(cw[tn])
        splits[tn] = (ts, A, B)
        rep["types"][tn] = dict(
            a=dict(buses=len(A["buses"]), cores=len(A["hard_cores"]), contents=len(A["contents"]), ft=len(A["ft_slots"]),
                   istations=len(A.get("internal_stations", [])), taps=len(A["clock"]["taps"])),
            b=dict(buses=len(B["buses"]), cores=len(B["hard_cores"]), contents=len(B["contents"]), ft=len(B["ft_slots"]),
                   istations=len(B.get("internal_stations", [])), taps=len(B["clock"]["taps"])),
            ft_cut=ts.ft_cut, legs={k: {kk: v[kk] for kk in ("x", "nb", "na", "width")} for k, v in ts.leg_cut.items()},
            cut_widths=cw[tn], content_half=dict(Counter(ts.content_half.values())), bus_conflicts=ts.bus_conflicts)
        rep["notes"] += ts.notes
    # ---- types
    pt = {}
    for tn, t in raw["partition_types"].items():
        if tn in splits:
            pt[tn] = splits[tn][2]
            pt[tn + "_a"] = splits[tn][1]        # right after b, so e0/e1/e2 cohort order and block hashes stay
        else:
            pt[tn] = t
    raw["partition_types"] = pt
    # ---- partitions
    newparts = []
    aname = {}
    for p in raw["partitions"]:
        if p["type"] not in splits:
            newparts.append(p)
            continue
        tn = p["type"]
        o = p.get("orient", "R0")
        ox, oy = p["origin_um"]
        H = 1520.64
        flipy = o in ("MX", "R180")
        na = p["name"] + "_a"
        pa = dict(p, name=na, type=tn + "_a", origin_um=[ox, round(oy + (H - CUT if flipy else 0.0), 6)])
        pb = dict(p, type=tn, origin_um=[ox, round(oy if flipy else oy + CUT, 6)])
        aname[p["name"]] = na
        newparts += [pb, pa]
    raw["partitions"] = newparts
    pmap = {p["name"]: p for p in newparts}
    # ---- ports: move endpoints of b buses
    def ep_part(part, bus):
        if part not in aname:
            return part
        tn = [q for q in orig["partitions"] if q["name"] == part][0]["type"]
        ts = splits[tn][0]
        return aname[part] if ts.side_of_bus(bus) == "a" else part
    moved = Counter()
    for p in raw["ports"]:
        for e in ("src", "dst"):
            np_ = ep_part(p[e]["part"], p[e]["bus"])
            if np_ != p[e]["part"]:
                moved[e] += 1
                p[e]["part"] = np_
    rep["port_ends_moved"] = dict(moved)
    # ---- new ports / lanes
    ports = {p["id"]: p for p in raw["ports"]}
    lanes = {l["id"]: l for l in raw["lanes"]}
    lmax = max(int(l["id"][1:]) for l in raw["lanes"])
    new_lat = []
    for p in orig["partitions"]:
        if p["type"] not in splits:
            continue
        tn = p["type"]
        ts = splits[tn][0]
        pa, pb = aname[p["name"]], p["name"]
        items = [("leg:" + bus, L["width"] + 1, L["x"]) for bus, L in sorted(ts.leg_cut.items())]
        items += [("ft:" + f["slot"], f["width"] + 1, f["x"]) for f in ts.ft_cut]
        items += [("cut:ab", cw[tn]["ab"] + 1, None), ("cut:ba", cw[tn]["ba"] + 1, None)]   # + epoch pin
        win = windows_for(items, ts.W, a.per_um)
        rep["types"][tn]["cut_windows"] = win
        Wd, Hd = ts.W, CUT
        rpa = pmap[pa]

        def port(pid, src, sbus, dst, dbus, width, kind, key):
            segs = win[key]
            dw = [type_window(sg[:2], pa, rpa, (Wd, Hd), "N") for sg in segs]
            df, order = dw[0][0], dw[0][2]
            lo, hi = min(d[1][0] for d in dw), max(d[1][1] for d in dw)
            pr = dict(id=pid, src=dict(part=src, bus=sbus), dst=dict(part=dst, bus=dbus), width=width, kind=kind,
                      face=df if src == pa else {"N": "S", "S": "N"}[df], layers=list(CUT_LAYERS), window_um=[lo, hi],
                      order=order, note=f"HG-SPLIT 11-03: {pa} / {pb} cut face ({key})")
            if len(segs) > 1:
                npins = S.port_pins_count(pr)
                extra = npins - sum(sg[2] for sg in segs)   # window sizing counted the epoch pin; trim the last segment
                pr["segments"] = [dict(pins=sg[2] + (extra if k == len(segs) - 1 else 0), window_um=d[1])
                                  for k, (sg, d) in enumerate(zip(segs, dw))]
            raw["ports"].append(pr)
            ports[pid] = pr
            rep["ports_added"].append(pid)
            return pr
        # generic cut lanes
        for d, (s_, sb, d_, db) in (("ab", (pa, "o_hgcut_ab", pb, "i_hgcut_ab")), ("ba", (pb, "o_hgcut_ba", pa, "i_hgcut_ba"))):
            lmax += 1
            lid = f"L{lmax}"
            port(f"{lid}_0", s_, sb, d_, db, cw[tn][d], "data", "cut:" + d)
            raw["lanes"].append(dict(id=lid, ports=[f"{lid}_0"], note=f"HG-SPLIT 11-03 generic cut lane {p['name']} {d}"))
            new_lat.append(lid)
            rep["lanes_added"].append(lid)
        # internal legs: b.o_<bus> -> a.i_<bus>, fixed = b stations; the out lane keeps the a stations
        for bus, L in sorted(ts.leg_cut.items()):
            lmax += 1
            lid = f"L{lmax}"
            port(f"{lid}_0", pb, bus, pa, L["a_in"], L["width"], L["kind"], "leg:" + bus)
            raw["lanes"].append(dict(id=lid, ports=[f"{lid}_0"], fixed_cycles=L["nb"],
                                     note=f"HG-SPLIT 11-03 internal forward leg {bus} half b -> half a, {L['nb']} stations"))
            new_lat.append(lid)
            rep["lanes_added"].append(lid)
            outl = [l for l in raw["lanes"] if ports[l["ports"][0]]["src"]["part"] == pa
                    and ports[l["ports"][0]]["src"]["bus"] == bus]
            if len(outl) != 1:
                raise ValueError(f"{pa}.{bus}: {len(outl)} out lanes")
            ol = outl[0]
            old = int(ol.get("fixed_cycles", 0))
            if old < L["na"] + L["nb"]:
                raise ValueError(f"{ol['id']}: fixed {old} < leg stations {L['na'] + L['nb']}")
            ol["fixed_cycles"] = old - L["nb"]
            ol["note"] = ol.get("note", "") + f" | HG-SPLIT: {L['nb']} of the forward stations moved to the cut lane {lid}"
            rep["lanes_changed"][ol["id"]] = dict(fixed=[old, ol["fixed_cycles"]])
        # crossing ft slots: insert a.ft_o -> b.ft_i into every lane through it
        for f in ts.ft_cut:
            for l in raw["lanes"]:
                ps = l["ports"]
                for i, q in enumerate(ps):
                    pr = ports[q]
                    if pr["dst"]["part"] == pa and pr["dst"]["bus"] == f["slot"] + "_i":
                        nxt = ports[ps[i + 1]] if i + 1 < len(ps) else None
                        if nxt is None or nxt["src"]["part"] != pb or nxt["src"]["bus"] != f["slot"] + "_o":
                            raise ValueError(f"lane {l['id']}: {pa}.{f['slot']}_i not followed by {pb}.{f['slot']}_o")
                        nid = f"{q}c"
                        port(nid, pa, f["slot"] + "_o", pb, f["slot"] + "_i", f["width"], pr.get("kind", "data"),
                             "ft:" + f["slot"])
                        ps.insert(i + 1, nid)
                        rep["lanes_changed"].setdefault(l["id"], {})["ft_cut"] = nid
                        break
    # ---- landing network: forwarded clock / start edges follow their functional port's (moved) endpoints
    nren = 0
    for e in raw["clock"]["landing_network"]["edges"]:
        m = re.match(r"^cland_(clk|start)__(.*)$", e["id"])
        if m and m.group(2) in ports:
            pr = ports[m.group(2)]
            for k in ("src", "dst"):
                if e[k]["part"] != pr[k]["part"]:
                    e[k]["part"] = pr[k]["part"]
                    nren += 1
    rep["landing_edges_moved"] = nren
    # ---- latency: recompute every lane from the new plan; only touched lanes may change
    S_raw = json.loads(json.dumps(raw))
    P = S.Plan(S_raw, None)
    lat = raw["latency"]["lanes"]
    changed = {}
    for lid in list(lanes) + new_lat:
        d = P.lane_latency(lid)
        old = lat.get(lid)
        ent = dict(d)
        ent.setdefault("param", f"LAT_{lid}")
        if old is not None:
            ent["param"] = old.get("param", ent["param"])
            if {k: v for k, v in old.items() if k != "param"} != {k: v for k, v in ent.items() if k != "param"}:
                changed[lid] = dict(old=old.get("cycles"), new=ent["cycles"])
        lat[lid] = ent
    rep["latency_changed"] = changed
    touched = set(rep["lanes_changed"]) | set(new_lat)
    pads_moved = {l: v for l, v in changed.items() if l not in touched}
    rep["latency_changed_untouched"] = pads_moved
    # ---- reset in sites
    ins = raw["reset"].get("in_sites", {})
    for tn in HG:
        if tn in ins:
            xy = ins.pop(tn)
            s = half_of_y(xy[1])
            o = "a" if s == "b" else "b"
            ins[half_type(tn, s)] = sh(xy, s)
            ins[half_type(tn, o)] = [xy[0], round(CUT - 8.672, 3)] if o == "a" else [xy[0], 8.672]
    # ---- sidecar
    sd = copy.deepcopy(side)
    for r in sd["regions"]:
        add = [aname[p] for p in r["parts"] if p in aname]
        r["parts"] += add
    for r in sd["ports"]:
        pr = ports[r["port"]]
        if r["src"] != pr["src"]["part"]:
            r["src"] = pr["src"]["part"]
        if r["dst"] != pr["dst"]["part"]:
            r["dst"] = pr["dst"]["part"]
    sd["note_hgsplit"] = (f"HG-SPLIT 11-03: hg_*_a halves share their hg_* region; {len(rep['ports_added'])} cut ports are "
                          "same-region (no landing row); landed rows of moved buses renamed")
    # ---- map
    mj = json.load(open(a.map_json))
    M = mj["map"] if "map" in mj and "parts" not in mj else mj
    nmap = 0
    for k, v in list(M["parts"].items()):
        if isinstance(v, str):
            if v in aname:
                raise ValueError(f"map {k}: whole HG partition {v} (needs a half)")
            continue
        part, inst = v
        if part in aname:
            tn = [q for q in orig["partitions"] if q["name"] == part][0]["type"]
            ts = splits[tn][0]
            hc = {h["inst"]: h for h in ts.t["hard_cores"]}
            s = ts.content_half.get(inst) or (ts.core_side(hc[inst]) if inst in hc else None) or MAP_INST_HALF.get(inst)
            if s is None:
                raise ValueError(f"map {k}: {part}.{inst} has no half")
            if s == "a":
                M["parts"][k] = [aname[part], inst]
                nmap += 1
    rep["map_moved"] = nmap
    json.dump(raw, open(out / "plan_c.json", "w"), indent=1)
    json.dump(sd, open(out / "eW_sidecar.json", "w"), indent=1)
    json.dump(mj, open(out / "asbuilt_map.json", "w"), indent=1)
    json.dump(rep, open(out / "report.json", "w"), indent=1)
    print(json.dumps(dict(types=len(splits) * 2, parts=len(aname) * 2, ports_added=len(rep["ports_added"]),
                          lanes_added=len(rep["lanes_added"]), lanes_changed=len(rep["lanes_changed"]),
                          latency_changed=len(changed), untouched_changed=len(pads_moved), map_moved=nmap)))


if __name__ == "__main__":
    main()
