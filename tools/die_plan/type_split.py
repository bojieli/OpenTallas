#!/usr/bin/env python3
"""type_split: plan-level N-way partition-type SPLIT along one axis (KV-SPLIT-1 11-13, owner rule R-CAP-3).

    python3 -I tools/die_plan/type_split.py split   SPEC.json --out DIR      the split plan event (files below)
    python3 -I tools/die_plan/type_split.py census  SPEC.json --bind BIND_OUT --out J
                                                    crossing bits of a base bind that the split cuts (sizes the cut lanes)

SPEC (JSON, paths relative to the repo root unless absolute):
  plan, sidecar, asbuilt              the base plan, its clock_landing_table sidecar and the as-built manifest
  plan_cells                          optional: the manifest's plan_cells table (default asbuilt.plan_cells)
  plan_dir                            optional: the plan dir the plan's relative paths (pins_file, census) resolve
                                      against (default: the plan file's dir; set it when the plan sits outside it)
  census_base                         optional: dir of the plan's census map / rows paths (default: plan_dir)
  core_moves {type: {inst: [x, y]}}   hard cores MOVED (no re-shape) before the split; station_moves {type: {slot:
                                      {reg: [dx, dy]}}} moves ft stations out of a moved box (see Event._core_moves)
  event                               tag written into notes / port ids
  family                              type names; every member takes the SAME cut (R-CAP-3.4); a member's type is
                                      split for all of its partitions
  axis "x" | "y", cuts_um [..]        cut lines in the TYPE frame (R0), sorted; every cut on spec.lattice_um (default:
                                      the plan grid, 8.64 um: piece outlines and origins stay on the partition lattice)
  parts [{suffix}, ..]                one per piece, low coordinate first; suffix "" keeps the type / partition names
  parts_by_type / keep_by_type        per-type overrides of parts / keep (the keep piece holds the collector up link)
  keep                                index of the piece that keeps the region origin, the collector up link and the
                                      START pins (the other pieces become count-aligned RELAY partitions of the same
                                      region and collector children of the keep piece)
  contents {type: [[regex, piece]..]} content -> piece (fullmatch on inst, first rule wins); a content that is a member
                                      of a hard core (hard_core note "<x>: a + b + ...;") follows the core geometry
  cut_lanes {type: [{from, to, stem, width}]}   generic leaf/forward cut lanes (census sizes them); legs and ft slots
                                      that cross a cut get their own cut buses automatically
  fold_legs                           drop one internal station next to the cut where both hops stay <= reach
                                      (the cut boundary flop pair replaces it: +1 cycle instead of +2)

What moves (every element is decided by geometry or by the spec; anything else fails closed):
  buses              the piece of every port window of the bus (all instances agree); faces normal to the axis go to
                     the outer pieces
  hard cores         their extent (a core across a cut is an error)
  contents           spec rules / core membership; physical_parts must lie inside the piece
  ft slots           whole slot when its stations lie in one piece, else one slot per piece: the next piece gets a new
                     in-face station at the cut (+1 cycle per cut) and every lane through the slot a new port
  internal stations  one leg per piece; each cut adds a bus pair (o_<stem>_p -> i_<stem>_p) + lane, fixed_cycles moved
                     with the stations (native_istations rule: fixed = source + receiver stations)
  plan cells         per piece; a cell / bus driver whose inputs sit in another piece gets a cut bus; ot_dp_efault is
                     split per piece and the non-keep pieces' faults are ORed into the keep piece's fault bus
  clock              R4 edge grid per piece (tap_edge_y_um kept on the outer edges), added taps by position (renamed
                     clk_t<n>), core taps, sink sites, edge clocks / landing pins / bands by bus, collector pins
  reset              tap (kept when inside, else the piece centre), local taps by position, in_sites
  count straps       strap_ca_k_<bus> by bus, others on every piece (re-derived by count_align_bind.strap_ties)
  partitions         piece origins by orientation; the new partitions follow their base partition
  sidecar            ONE landing region per base partition (all pieces), rows renamed, collector parts/edges/types,
                     count_aligned relay roles (one origin per region) and K of the relay pieces' crossings
  as-built map       map.parts of the type's contents -> their piece
Fail-closed: a straddling element, an unassigned content, a crossing form the code does not handle, a cut-face window
that does not fit, a lane whose latency changes without being touched.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

EPS = 1e-6
G = 0.432            # cut-face window grid (precedent hg_split windows_for)
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
LAND_PIN = re.compile(r"^(fclk_in|fclk_out|cland_fstart_in|cland_fstart_out)_(.*)$")
COLL_PIN = re.compile(r"^(cland_up_ready|cland_up_fault|fclk_out_cland_up|cland_dn_ready_(\d+)|cland_dn_fault_(\d+)|"
                      r"fclk_in_cland_dn_(\d+))$")
START_PINS = ("cland_tstart_in", "cland_tstart_out", "cland_raw_reset_out")
PIN_MARGIN = 2.16    # landing pin keep-in from a piece edge along the cut axis
PIN_STEP = 0.96      # landing pin nudge step (two 0.48 tracks)


class SplitError(ValueError):
    pass


def rnd(v, n=6):
    return round(float(v) + 0.0, n)


def jdump(o, path):
    txt = json.dumps(o, indent=1) + "\n"
    p = Path(path)
    if p.exists() or p.is_symlink():
        p.unlink()                  # never write through a hard link of a cp -al tree
    p.write_text(txt)
    return hashlib.md5(txt.encode()).hexdigest()


def rpath(p):
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


# ---------------------------------------------------------------------------------------------------------------- geometry
class Cut:
    """the cut lines of one family: pieces along `axis` (0 = x, 1 = y) of a type of extent L."""

    def __init__(self, axis, cuts, L):
        self.ax = {"x": 0, "y": 1}[axis]
        self.cuts = [float(c) for c in cuts]
        if self.cuts != sorted(self.cuts) or not all(EPS < c < L - EPS for c in self.cuts):
            raise SplitError(f"cuts {cuts} must be sorted and inside (0, {L})")
        self.L = float(L)
        self.bounds = [0.0] + self.cuts + [self.L]
        self.n = len(self.cuts) + 1

    def lo(self, i):
        return self.bounds[i]

    def hi(self, i):
        return self.bounds[i + 1]

    def ext(self, i):
        return rnd(self.hi(i) - self.lo(i))

    def piece(self, a, b=None, what=""):
        """piece of the interval [a, b] along the axis; straddling a cut is an error"""
        b = a if b is None else b
        a, b = min(a, b), max(a, b)
        for i in range(self.n):
            if a >= self.lo(i) - EPS and b <= self.hi(i) + EPS:
                # an interval that only touches a cut line belongs to the piece holding its interior
                if b - a > EPS or (i == self.n - 1 or a < self.hi(i) - EPS) or i == 0:
                    return i
        raise SplitError(f"{what} [{a:.3f}, {b:.3f}] straddles a cut {self.cuts}")

    def ppiece(self, xy, what=""):
        return self.piece(float(xy[self.ax]), what=what)

    def sh(self, xy, i):
        o = list(xy)
        o[self.ax] = rnd(float(xy[self.ax]) - self.lo(i))
        return o

    def unsh(self, xy, i):
        """piece-frame point -> type frame"""
        o = list(xy)
        o[self.ax] = rnd(float(xy[self.ax]) + self.lo(i))
        return o

    def shr(self, r, i):
        o = list(r)
        o[self.ax] = rnd(r[self.ax] - self.lo(i))
        o[self.ax + 2] = rnd(r[self.ax + 2] - self.lo(i))
        return o

    def rect_piece(self, r, what=""):
        return self.piece(r[self.ax], r[self.ax + 2], what)

    def low_face(self):
        return "S" if self.ax == 1 else "W"

    def high_face(self):
        return "N" if self.ax == 1 else "E"

    def axis_faces(self):
        return (self.low_face(), self.high_face())


def local_face(orient, df):
    """die face -> type-frame face of an instance with this orientation"""
    flipx, flipy = orient in ("MY", "R180"), orient in ("MX", "R180")
    if df in "NS":
        return OPP[df] if flipy else df
    return OPP[df] if flipx else df


def die_face(orient, lf):
    return local_face(orient, lf)      # the flips are involutions


# ------------------------------------------------------------------------------------------------------------- the split
class TypeSplit:
    def __init__(self, ev, tn):
        self.ev, self.tn = ev, tn
        raw = ev.raw
        self.t = raw["partition_types"][tn]
        # internal-station rows repeated with identical geometry (one per core of the same chain; bind and the kit
        # merge them) are ONE chain: kept once so the cut gives it one leg / one cut bus (notes joined)
        ist, seen, ndup = [], {}, 0
        for r in self.t.get("internal_stations", []):
            key = json.dumps({k: v for k, v in r.items() if k != "note"}, sort_keys=True)
            if key in seen:
                ndup += 1
                if r.get("note") and r["note"] not in (seen[key].get("note") or ""):
                    seen[key]["note"] = (seen[key].get("note", "") + " | " + r["note"]).lstrip(" |")
                continue
            seen[key] = r = copy.deepcopy(r)
            ist.append(r)
        if ndup:
            self.t = dict(self.t, internal_stations=ist)
            raw["partition_types"][tn] = self.t
            ev.rep["notes"].append(f"{tn}: {ndup} internal-station rows repeated with identical geometry kept once")
        if self.t.get("hard"):
            raise SplitError(f"{tn}: a hard type is not split (R-CAP-3 splits soft partition types)")
        self.W, self.H = map(float, self.t["outline_um"])
        self.cut = Cut(ev.spec["axis"], ev.spec["cuts_um"], self.H if ev.spec["axis"] == "y" else self.W)
        self.n = self.cut.n
        parts = (ev.spec.get("parts_by_type") or {}).get(tn, ev.spec["parts"])
        if len(parts) != self.n:
            raise SplitError(f"spec.parts has {len(parts)} entries for {self.n} pieces")
        self.parts = [p for p in raw["partitions"] if p["type"] == tn]
        if not self.parts:
            raise SplitError(f"{tn}: no partition")
        sfx = [p["suffix"] for p in parts]
        self.tnames = [tn + s for s in sfx]
        # keep_by_type: the piece that holds the type's collector up link / region origin may differ per type
        self.keep = int((ev.spec.get("keep_by_type") or {}).get(tn, ev.spec.get("keep", 0)))
        if sfx[self.keep] != "":
            raise SplitError("the keep piece must keep the names (suffix '')")
        clash = [x for x in self.tnames if x != tn and x in raw["partition_types"]]
        if clash:
            raise SplitError(f"{tn}: piece type names already exist {clash}")
        self.pname = {p["name"]: [p["name"] + s for s in sfx] for p in self.parts}
        self.bus_piece = {}
        self.rep = dict(pieces=self.tnames, cut_um=self.cut.cuts, axis=ev.spec["axis"], notes=[])
        self.new_bus = [[] for _ in range(self.n)]
        self.cutbus = []          # [dict(src, dst, oname, iname, width, kind, x, key, fixed, ...)]

    # -------------------------------------------------------------- bus pieces from the ports
    def _port_ends(self):
        ends = defaultdict(list)
        names = {p["name"]: p for p in self.parts}
        for pr in self.ev.raw["ports"]:
            for e in ("src", "dst"):
                part = pr[e]["part"]
                if part not in names:
                    continue
                p = names[part]
                df = pr["face"] if (e == "src" or pr["src"]["part"] == "@die") else OPP[pr["face"]]
                ends[pr[e]["bus"]].append((pr, e, p, df))
        return ends

    def _end_piece(self, pr, p, df, segment=None):
        o = p.get("orient", "R0")
        lf = local_face(o, df)
        lo_f, hi_f = self.cut.axis_faces()
        if lf == lo_f:
            return 0
        if lf == hi_f:
            return self.n - 1
        # a face parallel to the axis: the window runs along the axis
        ox, oy = p["origin_um"]
        flip = o in (("MX", "R180") if self.cut.ax == 1 else ("MY", "R180"))
        org = oy if self.cut.ax == 1 else ox
        win = segment or pr["window_um"]
        L = self.cut.L
        loc = [(org + L - v) if flip else (v - org) for v in win]
        return self.cut.piece(min(loc), max(loc), f"{self.tn} port {pr['id']} window")

    def compute_bus_pieces(self):
        ends = self._port_ends()
        self.ends = ends
        for bus, es in ends.items():
            ps = set()
            for pr, e, p, df in es:
                segs = [s["window_um"] for s in pr.get("segments") or []] or [None]
                for sg in segs:
                    ps.add(self._end_piece(pr, p, df, sg))
            if len(ps) != 1:
                raise SplitError(f"{self.tn}.{bus}: port windows put it in pieces {sorted(ps)}")
            self.bus_piece[bus] = ps.pop()
        for b in self.t.get("buses", []):
            if b["name"] not in self.bus_piece:
                raise SplitError(f"{self.tn}.{b['name']}: bus without a port (no piece)")

    def bp(self, bus):
        if bus not in self.bus_piece:
            raise SplitError(f"{self.tn}: bus {bus} has no piece")
        return self.bus_piece[bus]

    # -------------------------------------------------------------- contents
    def core_members(self):
        mem = {}
        for h in self.t.get("hard_cores", []):
            m = re.match(r'"?[\w]+: ([^;]*);', h.get("note", ""))
            if m:
                for x in m.group(1).split(" + "):
                    mem[x.strip().split()[0]] = h["inst"]     # "a + b (module x2)": the member names only
        return mem

    def core_piece(self, h):
        a = h["origin_um"][self.cut.ax]
        w = h["outline_um"][self.cut.ax]
        return self.cut.piece(a, a + w, f"{self.tn} hard core {h['inst']}")

    def content_pieces(self):
        rules = [(re.compile(rx), int(i)) for rx, i in self.ev.spec.get("contents", {}).get(self.tn, [])]
        mem = self.core_members()
        cores = {h["inst"]: h for h in self.t.get("hard_cores", [])}
        out = {}
        for c in self.t.get("contents", []):
            inst = c["inst"]
            byrule = next((i for rx, i in rules if rx.fullmatch(inst)), None)
            bycore = (self.core_piece(cores[mem[inst]]) if inst in mem else
                      self.core_piece(cores[inst]) if inst in cores else None)   # a content hardened as its own core
            if bycore is not None and byrule is not None and bycore != byrule:
                raise SplitError(f"{self.tn}: content {inst} is a member of core {mem[inst]} (piece {bycore}) "
                                 f"but the spec puts it in piece {byrule}")
            s = bycore if bycore is not None else byrule
            if s is None:
                raise SplitError(f"{self.tn}: content {inst} has no piece (spec.contents)")
            out[inst] = s
        self.content_piece = out
        return out

    # -------------------------------------------------------------- the type split
    def split(self):
        t, cut, n = self.t, self.cut, self.n
        self.compute_bus_pieces()
        self.content_pieces()
        T = [dict() for _ in range(n)]
        handled = {"outline_um", "buses", "ft_slots", "clock", "reset", "contents", "hard_cores", "internal_stations",
                   "count_straps", "module", "note", "hard", "face_pins_per_um", "face_budget_g2", "core_pg_connect",
                   "landing_control_status_copy", "reset_spine_pins", "pads", "reach_homes", "cells"}
        unknown = set(t) - handled
        if unknown:
            raise SplitError(f"{self.tn}: unhandled type keys {sorted(unknown)} (extend type_split.py)")
        for i in range(n):
            T[i]["module"] = (t.get("module") or self.tn + "_part") if i == self.keep else self.tnames[i] + "_part"
            o = list(t["outline_um"])
            o[cut.ax] = cut.ext(i)
            T[i]["outline_um"] = o
            T[i]["hard"] = False
            for k in ("face_pins_per_um", "face_budget_g2"):       # type-wide face budget: every piece keeps it
                if k in t:
                    T[i][k] = copy.deepcopy(t[k])
            T[i]["note"] = (f"{self.ev.tag}: piece {i} of {self.tn} ({'xy'[cut.ax]} {cut.lo(i)}..{cut.hi(i)} of the "
                            f"type frame, shifted by -{cut.lo(i)}) | " + t.get("note", ""))
        self.T = T
        # buses
        for i in range(n):
            T[i]["buses"] = []
        for b in t.get("buses", []):
            T[self.bp(b["name"])]["buses"].append(copy.deepcopy(b))
        # hard cores
        for i in range(n):
            T[i]["hard_cores"] = []
        for h in t.get("hard_cores", []):
            i = self.core_piece(h)
            hh = copy.deepcopy(h)
            hh["origin_um"] = cut.sh(h["origin_um"], i)
            T[i]["hard_cores"].append(hh)
        # contents
        for i in range(n):
            T[i]["contents"] = []
        for c in t.get("contents", []):
            i = self.content_piece[c["inst"]]
            cc = copy.deepcopy(c)
            for q in cc.get("physical_parts") or []:
                a = q["origin_um"][cut.ax]
                if cut.piece(a, a + q["outline_um"][cut.ax], f"{self.tn} {q.get('physical_inst')}") != i:
                    raise SplitError(f"{self.tn}: physical part {q.get('physical_inst')} lies outside piece {i}")
                q["origin_um"] = cut.sh(q["origin_um"], i)
            T[i]["contents"].append(cc)
        self._ft_slots()
        self._internal_stations()
        self._clock()
        self._reset()
        self._reset_spine_pins()
        self._count_straps()
        if t.get("reach_homes"):
            raise SplitError(f"{self.tn}: reach_homes present (drop them before the split; re-derive after)")
        if "pads" in t:
            self._pads()
        if "cells" in t:
            # the type's cell estimate (cell_check.py) split by register share (clock sink bins) else by area
            sb = getattr(self, "sink_bins", None)
            w = [sum(int(b[2]) for b in sb[i]["bins"]) for i in range(n)] if sb else \
                [T[i]["outline_um"][0] * T[i]["outline_um"][1] for i in range(n)]
            for i in range(n):
                T[i]["cells"] = int(round(int(t["cells"]) * w[i] / sum(w)))
            self.rep["cells_split"] = dict(base=t["cells"], by="registers" if sb else "area",
                                           pieces=[T[i]["cells"] for i in range(n)])
        for i in range(n):
            if "core_pg_connect" in t and T[i].get("hard_cores"):
                T[i]["core_pg_connect"] = copy.deepcopy(t["core_pg_connect"])   # the piece places hard-core macros
            if "landing_control_status_copy" in t and \
                    ((T[i].get("clock") or {}).get("landing_contract") or {}).get("bands"):
                T[i]["landing_control_status_copy"] = t["landing_control_status_copy"]   # needs its count-aligned rings
        for i in range(n):
            T[i]["buses"] += self.new_bus[i]
            for k in ("internal_stations", "count_straps", "hard_cores", "contents"):
                if k in T[i] and not T[i][k] and k not in t:
                    del T[i][k]
            if not T[i].get("internal_stations") and "internal_stations" in T[i]:
                del T[i]["internal_stations"]
        names = [Counter(b["name"] for b in T[i]["buses"]) for i in range(n)]
        for i in range(n):
            d = [k for k, v in names[i].items() if v > 1]
            if d:
                raise SplitError(f"{self.tnames[i]}: duplicate bus names {d}")
        return T

    # -------------------------------------------------------------- ft slots
    def _ft_slots(self):
        t, cut, T = self.t, self.cut, self.T
        self.ft_cut = []
        self.ft_in = {}           # (slot, piece) -> (piece slot dict, previous station type-frame, next station type-frame)
        for i in range(self.n):
            T[i]["ft_slots"] = []
        reroute = (self.ev.spec.get("slot_reroute") or {}).get(self.tn, {})
        unknown = set(reroute) - {f["name"] for f in t.get("ft_slots", [])}
        if unknown:
            raise SplitError(f"{self.tn}: slot_reroute names unknown slots {sorted(unknown)}")
        for f in t.get("ft_slots", []):
            if f["name"] in reroute:
                f = self._reroute_slot(f, reroute[f["name"]])
            regs = f["regs_um"]
            if int(f.get("stations", len(regs))) != len(regs):
                raise SplitError(f"{self.tn}.{f['name']}: stations {f.get('stations')} != {len(regs)} regs")
            si, so = self.bp(f["name"] + "_i"), self.bp(f["name"] + "_o")
            seq = [cut.ppiece(r, f"{self.tn}.{f['name']} station") for r in regs]
            # a station that dips across a cut and comes back (re-entry) within station_snap_um of the cut is moved
            # just across it (cut +- 4.32 um), with its bit sites: the chain then crosses once
            snap = float(self.ev.spec.get("station_snap_um", 0.0))
            full = seq + ([so] if seq[-1] != so else [])
            k = 1
            while snap > 0 and k < len(seq):
                if seq[k] != seq[k - 1]:
                    e = k
                    while e < len(seq) and seq[e] == seq[k]:
                        e += 1
                    after = seq[e] if e < len(seq) else so
                    if after == seq[k - 1]:
                        c = cut.hi(seq[k]) if seq[k - 1] > seq[k] else cut.lo(seq[k])
                        to_ = c + 4.32 if seq[k - 1] > seq[k] else c - 4.32
                        reach = float(self.ev.raw.get("budgets", {}).get("ft_station_max_um", 405.0)) - 8.64
                        chain = [list(p) for p in regs]
                        for q in range(k, e):
                            chain[q][cut.ax] = to_
                        nxt = chain[e] if e < len(chain) else self._face_point(f["name"] + "_o")
                        pts_ = chain[k - 1:e] + [nxt]
                        hops_ok = all(abs(a[0] - b[0]) + abs(a[1] - b[1]) <= reach for a, b in zip(pts_, pts_[1:]))
                        if hops_ok and all(abs(regs[q][cut.ax] - c) <= snap for q in range(k, e)):
                            f = copy.deepcopy(f)
                            regs = f["regs_um"]
                            to = c + 4.32 if seq[k - 1] > seq[k] else c - 4.32
                            for q in range(k, e):
                                dv = to - regs[q][cut.ax]
                                regs[q][cut.ax] = rnd(to)
                                if f.get("bit_sites_um") and q >= 1:
                                    for p in f["bit_sites_um"][q - 1]:
                                        p[cut.ax] = rnd(p[cut.ax] + dv)
                                seq[q] = seq[k - 1]
                                self.rep.setdefault("stations_snapped", []).append(
                                    dict(slot=f["name"], station=q, moved_um=rnd(dv, 3), to=list(regs[q])))
                    k = e
                else:
                    k += 1
            if seq[0] != si:
                raise SplitError(f"{self.tn}.{f['name']}: in-face station in piece {seq[0]}, bus {f['name']}_i in {si}")
            # runs of pieces along the chain; each run must be a different piece, adjacent to the previous one
            runs = []
            for k, s in enumerate(seq):
                if not runs or runs[-1][0] != s:
                    runs.append([s, []])
                runs[-1][1].append(k)
            if runs[-1][0] != so:
                runs.append([so, []])      # the chain leaves its last station towards a face in the next piece
            ps = [r[0] for r in runs]
            if len(set(ps)) != len(ps) or any(abs(a - b) != 1 for a, b in zip(ps, ps[1:])):
                raise SplitError(f"{self.tn}.{f['name']}: re-entrant / non-adjacent crossing {ps}")
            bs = f.get("bit_sites_um")
            if len(runs) == 1:
                g = copy.deepcopy(f)
                g["regs_um"] = [cut.sh(r, si) for r in regs]
                if bs is not None:
                    g["bit_sites_um"] = [[cut.sh(p, si) for p in st] for st in bs]
                T[si]["ft_slots"].append(g)
                continue
            pieces = []
            for j, (s, ks) in enumerate(runs):
                g = copy.deepcopy(f)
                rr = [cut.sh(regs[k], s) for k in ks]
                sites = [copy.deepcopy(bs[k - 1]) for k in ks if k >= 1] if bs is not None else None
                if sites is not None:
                    sites = [[cut.sh(p, s) for p in st] for st in sites]
                if j > 0:
                    # new in-face station at the cut where the chain enters this piece (+1 cycle)
                    prev = regs[runs[j - 1][1][-1]]
                    nxt = regs[ks[0]] if ks else self._face_point(f["name"] + "_o")
                    c = cut.hi(runs[j - 1][0]) if s > runs[j - 1][0] else cut.lo(runs[j - 1][0])
                    xc = self._cross(prev, nxt, c)
                    face_xy = [0.0, 0.0]
                    face_xy[cut.ax] = 0.0 if s > runs[j - 1][0] else cut.ext(s)
                    face_xy[1 - cut.ax] = xc
                    rr = [face_xy] + rr
                    if sites is not None:
                        # bit_sites_um[j] belongs to regs[j + 1]: the new in-face station carries no bit sites
                        pass
                    g["in_face"] = cut.low_face() if s > runs[j - 1][0] else cut.high_face()
                if j < len(runs) - 1:
                    g["out_face"] = cut.high_face() if runs[j + 1][0] > s else cut.low_face()
                g["regs_um"] = rr
                g["stations"] = len(rr)
                if sites is not None:
                    g["bit_sites_um"] = sites
                g["note"] = (g.get("note", "") + f" | {self.ev.tag}: piece {s} of the crossing slot "
                             f"{f['name']} ({len(rr)} of {f['stations']}+{len(runs) - 1} stations)").lstrip(" |")
                T[s]["ft_slots"].append(g)
                pieces.append(dict(piece=s, stations=len(rr), xc=rr[0][1 - cut.ax] if j > 0 else None))
                if j > 0:
                    self.ft_in[(f["name"], s)] = (g, list(prev), list(nxt))
            self.ft_cut.append(dict(slot=f["name"], width=int(f["width"]), pieces=pieces, old=int(f["stations"]),
                                    new=sum(p["stations"] for p in pieces)))
            for j in range(len(runs) - 1):
                a, b = runs[j][0], runs[j + 1][0]
                self.bus_piece.setdefault(f["name"] + "_o@%d" % a, a)
        self.rep["ft_cut"] = self.ft_cut

    def _reroute_slot(self, f, how):
        """spec slot_reroute {type: {slot: {"waypoints": [[x, y], ...]}}}: the station chain follows the polyline
        regs[0] -> waypoints -> regs[-1] (type frame) with its station count kept; stations 1..n-2 sit evenly along
        it, each station's bit sites move with it.  Every hop (and the in/out ends) stays at reach."""
        f = copy.deepcopy(f)
        regs = f["regs_um"]
        if len(regs) < 2:
            raise SplitError(f"{self.tn}.{f['name']}: reroute needs >= 2 stations")
        poly = [list(regs[0])] + [list(map(float, w)) for w in how["waypoints"]] + [list(regs[-1])]
        W, H = self.t["outline_um"]
        for p in poly:
            if not (0 <= p[0] <= W and 0 <= p[1] <= H):
                raise SplitError(f"{self.tn}.{f['name']}: reroute waypoint {p} outside the outline")
        seg = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(poly, poly[1:])]
        total = sum(seg)
        if any(a[0] != b[0] and a[1] != b[1] for a, b in zip(poly, poly[1:])):
            raise SplitError(f"{self.tn}.{f['name']}: reroute polyline must be rectilinear")

        def at(d):
            for (a, b), L in zip(zip(poly, poly[1:]), seg):
                if d <= L + 1e-9:
                    u = d / L if L else 0.0
                    return [rnd(a[0] + (b[0] - a[0]) * u, 3), rnd(a[1] + (b[1] - a[1]) * u, 3)]
                d -= L
            return list(poly[-1])
        n = len(regs)
        new = [list(regs[0])] + [at(total * k / (n - 1)) for k in range(1, n - 1)] + [list(regs[-1])]
        reach = float(self.ev.raw.get("budgets", {}).get("ft_station_max_um", 405.0))
        hop = total / (n - 1)
        if hop > reach:
            raise SplitError(f"{self.tn}.{f['name']}: reroute hop {hop:.0f} um > reach {reach:.0f}")
        bs = f.get("bit_sites_um")
        for k in range(1, n):
            dx, dy = new[k][0] - regs[k][0], new[k][1] - regs[k][1]
            if bs is not None:
                for p in bs[k - 1]:
                    p[0], p[1] = rnd(p[0] + dx), rnd(p[1] + dy)
                    if not (0 <= p[0] <= W and 0 <= p[1] <= H):
                        raise SplitError(f"{self.tn}.{f['name']}: rerouted station {k} bit site {p} outside the outline")
        old_len = sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(regs, regs[1:]))
        f["regs_um"] = new
        f["note"] = (f.get("note", "") + f" | {self.ev.tag}: rerouted via {how['waypoints']} ({n} stations kept, "
                     f"hop {hop:.0f} um)").lstrip(" |")
        self.rep.setdefault("slots_rerouted", []).append(dict(type=self.tn, slot=f["name"], old=regs, new=new,
                                                                 chain_um=[rnd(old_len, 1), rnd(total, 1)]))
        return f

    def _face_point(self, bus):
        """type-frame centre of the bus's first port window (for a chain that crosses after its last station)"""
        pr, e, p, df = self.ends[bus][0]
        o = p.get("orient", "R0")
        lf = local_face(o, df)
        ox, oy = p["origin_um"]
        a, b = pr["window_um"]
        if lf in "EW":
            y = (a + b) / 2 - oy
            return [self.W if lf == "E" else 0.0, y]
        x = (a + b) / 2 - ox
        return [x, self.H if lf == "N" else 0.0]

    def _cross(self, p, q, c):
        """the other coordinate where segment p -> q crosses the axis value c (snapped to the window grid)"""
        ax = self.cut.ax
        a0, a1 = float(p[ax]), float(q[ax])
        b0, b1 = float(p[1 - ax]), float(q[1 - ax])
        f = 0.5 if abs(a1 - a0) < EPS else (c - a0) / (a1 - a0)
        v = b0 + (b1 - b0) * min(1.0, max(0.0, f))
        return rnd(round(v / G) * G, 3)

    # -------------------------------------------------------------- internal stations (legs)
    def _new_bus_name(self, piece, base):
        # unique across ALL pieces of the type: one leg keeps one stem on every piece (window keys, readability)
        have = set()
        for i in range(self.n):
            have |= {b["name"] for b in self.T[i]["buses"]} | {b["name"] for b in self.new_bus[i]} | \
                {f["name"] + s for f in self.T[i].get("ft_slots", []) for s in ("_i", "_o")}
        nm = base + "_p"
        k = 2
        while nm in have:
            nm = f"{base}_p_{k}"           # '_p' and digit tokens keep bind name affinity (bind._aff drops them)
            k += 1
        return nm

    def _internal_stations(self):
        t, cut, T = self.t, self.cut, self.T
        self.legs = []
        for i in range(self.n):
            T[i]["internal_stations"] = []
        reach = float(self.ev.raw.get("budgets", {}).get("ft_station_max_um", 405.0))
        bw = {b["name"]: b for b in t.get("buses", [])}
        rows = self._netlist_rows([copy.deepcopy(r) for r in t.get("internal_stations", [])], bw, reach)
        for r in rows:
            if not r.get("conn", "").startswith("bus:"):
                raise SplitError(f"{self.tn}: internal station conn {r.get('conn')} is not bus:<name>")
            bus = r["conn"][4:]
            r = self._reanchor(r, bw, reach)
            regs = r["regs_um"]
            pts = [r["from_um"]] + regs + [r["to_um"]]
            seq = [cut.ppiece(p, f"{self.tn} {r['conn']} point") for p in pts]
            # an end exactly on the outline of a face normal to the axis belongs to the piece of its bus
            if len(set(seq)) == 1:
                rr = copy.deepcopy(r)
                s = seq[0]
                rr["from_um"], rr["to_um"] = cut.sh(r["from_um"], s), cut.sh(r["to_um"], s)
                rr["regs_um"] = [cut.sh(p, s) for p in regs]
                T[s]["internal_stations"].append(rr)
                continue
            out_row = bw[bus]["dir"] == "out"
            if self.bp(bus) != (seq[-1] if out_row else seq[0]):
                raise SplitError(f"{self.tn}: leg {r['conn']} ends in piece {seq[-1] if out_row else seq[0]}, its bus "
                                 f"in {self.bp(bus)}")
            runs = []
            for k, s in enumerate(seq):
                if not runs or runs[-1][0] != s:
                    runs.append([s, []])
                runs[-1][1].append(k)
            ps = [x[0] for x in runs]
            if len(set(ps)) != len(ps) or any(abs(a - b) != 1 for a, b in zip(ps, ps[1:])):
                raise SplitError(f"{self.tn}: leg {r['conn']} re-enters a piece {ps}")
            width = int(r.get("bits") or bw[bus]["width"])
            kind = bw[bus].get("kind", "data")
            # stem: the bus whose name affinity the cut lane must keep (bind._aff): a bus-to-bus forward keeps the
            # LAUNCH bus (its source pin matched that lane), a core leg keeps its own bus
            lm = re.match(r"^bus (\w+)$", r.get("launch", ""))
            stem_bus = lm.group(1) if lm else bus
            stem = re.sub(r"^[oi]_", "", stem_bus)
            cuts_here = []
            for j in range(len(runs) - 1):
                a, b = runs[j][0], runs[j + 1][0]
                c = cut.hi(a) if b > a else cut.lo(a)
                p0, p1 = pts[runs[j][1][-1]], pts[runs[j + 1][1][0]]
                cuts_here.append(dict(a=a, b=b, c=c, x=self._cross(p0, p1, c)))
            # point index sets per piece (regs only: index 1..len(regs))
            piece_regs = [[k for k in ks if 1 <= k <= len(regs)] for _, ks in runs]
            # dead cuts (spec dead_cuts {type: [[conn, a, b], ...]}): the bound / census bits of this row do not cross
            # cut a -> b on this row's leg (a bind shows them on another crossing lane).  No cut bus / lane is made
            # for it.  The runs between dead cuts form segments; a segment that holds the row's bus end or a live
            # cut is kept and ends / starts on the face of its dead cut; the stations of the other segments are
            # dropped (they carry no bit).
            dspec = [tuple(x) for x in (self.ev.spec.get("dead_cuts") or {}).get(self.tn, [])
                     if x[0] == r["conn"]]
            dead = {j for j, cc in enumerate(cuts_here) if (r["conn"], cc["a"], cc["b"]) in dspec}
            for x in dspec:
                if not any((cc["a"], cc["b"]) == (x[1], x[2]) for cc in cuts_here):
                    raise SplitError(f"{self.tn}: dead cut {list(x)} is not a cut of that row ({[(c['a'], c['b']) for c in cuts_here]})")
            # run segments between dead cuts; a segment is kept when it holds the row's bus end or a live cut
            bounds = [0] + [j + 1 for j in sorted(dead)]
            segs = [(b0, (bounds[i + 1] - 1) if i + 1 < len(bounds) else len(runs) - 1) for i, b0 in enumerate(bounds)]
            bus_run = len(runs) - 1 if out_row else 0
            seg_of = {}
            for (a0, e0) in segs:
                if a0 <= bus_run <= e0 or any(j not in dead for j in range(a0, e0)):
                    for j in range(a0, e0 + 1):
                        seg_of[j] = (a0, e0)
            if dead:
                for j in sorted(dead):
                    self.ev.rep.setdefault("dead_cuts", []).append(dict(type=self.tn, conn=r["conn"], a=cuts_here[j]["a"],
                                                                         b=cuts_here[j]["b"]))
                drop_runs = [j for j in range(len(runs)) if j not in seg_of]
                self.ev.rep.setdefault("dead_cut_stations_dropped", {})[f"{self.tn}:{r['conn']}"] = \
                    sum(len(piece_regs[j]) for j in drop_runs)
            dropped = []
            if self.ev.spec.get("fold_legs", True):
                for j, cc in enumerate(cuts_here):
                    if j in dead or j not in seg_of or j + 1 not in seg_of:
                        continue
                    # try to drop the last station before the cut or the first after it
                    for side in ("after", "before"):
                        if side == "after":
                            cand = piece_regs[j + 1][:1]
                            if not cand:
                                continue
                            k = cand[0]
                            prv = pts[piece_regs[j][-1]] if piece_regs[j] else pts[0]
                            nxt = pts[k + 1]
                        else:
                            cand = piece_regs[j][-1:]
                            if not cand:
                                continue
                            k = cand[0]
                            prv = pts[k - 1]
                            nxt = pts[piece_regs[j + 1][0]] if piece_regs[j + 1] else pts[-1]
                        x = self._fold_x(prv, nxt, cc["c"], cc["x"], reach)
                        if x is None:
                            continue
                        cc["x"] = x
                        (piece_regs[j + 1] if side == "after" else piece_regs[j]).remove(k)
                        dropped.append(dict(cut=j, station=list(pts[k]), side=side))
                        cc["folded"] = True
                        break
            names = []
            for j, cc in enumerate(cuts_here):
                if j in dead or j not in seg_of:
                    names.append(None)
                    continue
                on = self._new_bus_name(cc["a"], "o_" + stem)
                inn = self._new_bus_name(cc["b"], "i_" + stem)
                self.new_bus[cc["a"]].append(dict(name=on, dir="out", width=width, kind=kind))
                self.new_bus[cc["b"]].append(dict(name=inn, dir="in", width=width, kind=kind))
                names.append((on, inn))
            last = len(runs) - 1
            for j, (s, ks) in enumerate(runs):
                if j not in seg_of:
                    continue
                seg_s, seg_e = seg_of[j]
                rr = {k: copy.deepcopy(v) for k, v in r.items() if k not in ("from_um", "to_um", "regs_um", "launch",
                                                                               "capture", "conn", "note")}
                rr["regs_um"] = [cut.sh(pts[k], s) for k in piece_regs[j]]
                # every piece but the last forwards to its cut out bus (an OUT row: native_istations prices its
                # stations as the source stations of that cut lane); the last piece keeps the row's own form
                if j == seg_e and j < last:
                    # a segment cut short at a dead cut: it ends on the face toward that cut
                    cc = cuts_here[j]
                    tp = [0.0, 0.0]
                    tp[cut.ax] = cut.ext(s) if cc["b"] > s else 0.0
                    tp[1 - cut.ax] = cc["x"]
                    if j == 0:
                        if out_row:
                            raise SplitError(f"{self.tn}: {r['conn']}: kept OUT segment without its bus")
                        rr["from_um"] = cut.sh(r["from_um"], s)
                        rr["launch"] = r.get("launch")
                        rr["conn"] = "bus:" + bus
                    elif j == seg_s:
                        raise SplitError(f"{self.tn}: {r['conn']}: kept one-piece segment {s} without bus or live cut")
                    else:
                        pc = cuts_here[j - 1]
                        fp = [0.0, 0.0]
                        fp[cut.ax] = 0.0 if s > pc["a"] else cut.ext(s)
                        fp[1 - cut.ax] = pc["x"]
                        rr["from_um"] = fp
                        rr["launch"] = "bus " + names[j - 1][1]
                        rr["conn"] = "bus:" + names[j - 1][1]
                    rr["to_um"] = tp
                    rr["capture"] = "face:" + (cut.high_face() if cc["b"] > s else cut.low_face())
                    rr["note"] = (f"{self.ev.tag}: piece {s} of the row {r['conn']} cut short at the dead cut "
                                  f"{cc['a']} -> {cc['b']} ({len(rr['regs_um'])} of {len(regs)} stations) | " + r.get("note", ""))
                    if rr["launch"] is None:
                        del rr["launch"]
                    T[s]["internal_stations"].append(rr)
                    continue
                if j == seg_s and j > 0:
                    # a segment started past a dead cut: its kept segment launches from the face of that cut
                    pc = cuts_here[j - 1]
                    fp = [0.0, 0.0]
                    fp[cut.ax] = 0.0 if s > pc["a"] else cut.ext(s)
                    fp[1 - cut.ax] = pc["x"]
                    rr["from_um"] = fp
                    rr["launch"] = "face:" + (cut.low_face() if s > pc["a"] else cut.high_face())
                elif j == 0:
                    rr["from_um"] = cut.sh(r["from_um"], s)
                    rr["launch"] = r.get("launch") if out_row else "bus " + bus
                else:
                    cc = cuts_here[j - 1]
                    fp = [0.0, 0.0]
                    fp[cut.ax] = 0.0 if s > cc["a"] else cut.ext(s)
                    fp[1 - cut.ax] = cc["x"]
                    rr["from_um"] = fp
                    if j < last or out_row:
                        rr["launch"] = "bus " + names[j - 1][1]
                    else:
                        rr["launch"] = "face:" + (cut.low_face() if s > cc["a"] else cut.high_face())
                if j == last:
                    rr["to_um"] = cut.sh(r["to_um"], s)
                    rr["capture"] = r.get("capture")
                    rr["conn"] = "bus:" + (bus if out_row else names[j - 1][1])
                else:
                    cc = cuts_here[j]
                    tp = [0.0, 0.0]
                    tp[cut.ax] = cut.ext(s) if cc["b"] > s else 0.0
                    tp[1 - cut.ax] = cc["x"]
                    rr["to_um"] = tp
                    rr["capture"] = "face bus " + names[j][0]
                    rr["conn"] = "bus:" + names[j][0]
                rr["note"] = (f"{self.ev.tag}: piece {s} of the crossing leg {r['conn']} ({len(rr['regs_um'])} of "
                              f"{len(regs)} stations) | " + r.get("note", ""))
                if rr["launch"] is None:
                    del rr["launch"]
                if rr["capture"] is None:
                    del rr["capture"]
                T[s]["internal_stations"].append(rr)
            leg = dict(conn=r["conn"], dir="out" if out_row else "in", width=width, kind=kind,
                       pieces=[dict(piece=s, stations=len(piece_regs[j])) for j, (s, _) in enumerate(runs)
                               if j in seg_of],
                       cuts=[dict(a=cc["a"], b=cc["b"], x=cc["x"], oname=names[j][0], iname=names[j][1],
                                  folded=bool(cc.get("folded"))) for j, cc in enumerate(cuts_here) if names[j]],
                       old_stations=len(regs), dropped=dropped,
                       dead_cuts=[[cuts_here[j]["a"], cuts_here[j]["b"]] for j in sorted(dead)],
                       span=[runs[0][0], runs[-1][0]])
            self.legs.append(leg)
            for j, cc in enumerate(cuts_here):
                if names[j] is None:
                    continue
                self.bus_piece[names[j][0]] = cc["a"]
                self.bus_piece[names[j][1]] = cc["b"]
        self.rep["legs"] = self.legs

    # ------------------------------------------------------------- BASE-DEFECT: row core ends from the netlist
    @staticmethod
    def _top(name):
        return str(name).split(".", 1)[0]

    @staticmethod
    def _same_inst(a, b):
        return a == b or a.startswith(b + "__") or b.startswith(a + "__")

    def _core_end(self, r, out_row):
        """('core', top instance) | ('fwd', in bus) | None (face / unknown) for the row's core end"""
        v = str(r.get("launch" if out_row else "capture", ""))
        if v.startswith("face") or not v:
            return None
        m = re.match(r"^bus (\w+)$", v)
        if m:
            return ("fwd", m.group(1))
        return ("core", self._top(v))

    def _netlist_end(self, bus, out_row):
        """majority netlist end of the bus (census ends, from the base bind): ('core', local inst) | ('fwd', in bus)"""
        ends = (getattr(self.ev, "census", None) or {}).get("ends") or {}
        hubs = [p["name"] for p in self.ev.raw["partitions"] if p["type"] == self.tn]
        got, alls = set(), set()
        for h in hubs:
            rows = [e for e in ends.get(h, {}).get(bus, []) if e[0] in (("drv", "fwd") if out_row else ("sink",))]
            if rows:
                role, name, _piece, _n = max(rows, key=lambda e: e[3])
                got.add(("fwd", name) if role == "fwd" else ("core", self._top(name)))
                alls |= {("fwd", e[1]) if e[0] == "fwd" else ("core", self._top(e[1])) for e in rows}
        if len(got) > 1:
            raise SplitError(f"{self.tn}: bus {bus} has different netlist ends per instance {sorted(got)}")
        if not got:
            return None
        # an IN bus may fan out to several sinks (one row per capture): any netlist sink is a valid core end;
        # an OUT bus has one driver (the majority)
        return next(iter(got)), (alls if not out_row else set(got))

    def _matches(self, have, ends):
        return any(have[0] == w[0] and (have[1] == w[1] if have[0] == "fwd" else self._same_inst(have[1], w[1]))
                   for w in ends)

    def _lroute(self, A, B, n_min, reach):
        on_ew = min(A[0], self.W - A[0]) < 2.0
        corner = [B[0], A[1]] if on_ew else [A[0], B[1]]
        poly = [A, corner, B]
        segs = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(poly, poly[1:])]
        Ltot = sum(segs)
        n = max(n_min, math.ceil(Ltot / (reach - 8.64)) - 1)
        regs = []
        for k in range(1, n + 1):
            d = Ltot * k / (n + 1)
            for (a, b), sl in zip(zip(poly, poly[1:]), segs):
                if d <= sl + 1e-9:
                    f = d / sl if sl else 0.0
                    regs.append([rnd(a[0] + (b[0] - a[0]) * f, 3), rnd(a[1] + (b[1] - a[1]) * f, 3)])
                    break
                d -= sl
        return regs

    def _hops_ok(self, r, reach):
        pts = [r["from_um"]] + r["regs_um"] + [r["to_um"]]
        return all(abs(a[0] - b[0]) + abs(a[1] - b[1]) <= reach + 1e-6 for a, b in zip(pts, pts[1:]))

    def _netlist_rows(self, rows, bw, reach):
        """KV-SPLIT-1113 BASE-DEFECT (DIE-KV-100 option A): a row whose core end (IN capture / OUT launch) is not the
        bus's netlist end is corrected before the cut -- a swapped pair exchanges core end + stations (each keeps its
        own face end; an L route at reach only when a hop would exceed it); an OUT row the netlist drives by
        forwarding an input becomes a forward row of that input.  Anything else fails closed (spec base_defect_rows
        "off" skips the correction for a family whose buses have no single netlist end)."""
        self.defect = {}
        if not ((getattr(self.ev, "census", None) or {}).get("ends")):
            return rows
        if self.ev.spec.get("base_defect_rows") == "off":
            # spec opt-out (pv family): the bus's netlist ends are split between several drivers (vport_E / vport_W
            # each drive a share of one forward chain bus), so a single 'netlist end' is not defined; the base rows
            # bound clean in the base strict bind and are kept (cut stations only)
            self.ev.rep.setdefault("base_defect_off", []).append(self.tn)
            return rows
        bad = []
        for k, r in enumerate(rows):
            bus = r.get("conn", "")[4:]
            if bus not in bw:
                continue
            out_row = bw[bus]["dir"] == "out"
            have, ne = self._core_end(r, out_row), self._netlist_end(bus, out_row)
            if have is None or ne is None:
                continue
            want, ok = ne
            if self._matches(have, ok):
                continue
            bad.append((k, bus, out_row, have, want))
        done = set()
        for k, bus, out_row, have, want in bad:
            if k in done:
                continue
            r = rows[k]
            old = dict(from_um=r["from_um"], to_um=r["to_um"], n=len(r["regs_um"]),
                       end=r.get("launch" if out_row else "capture"))
            if want[0] == "core":
                mate = [(k2, b2) for k2, b2, o2, h2, w2 in bad if k2 != k and k2 not in done and o2 == out_row
                        and h2[0] == "core" and w2[0] == "core" and self._same_inst(h2[1], want[1])
                        and self._same_inst(w2[1], have[1])]
                if len(mate) > 1:
                    # several candidates: the one whose bus is the same signal (quadrant tokens dropped, bind._aff)
                    aff = lambda n: "".join(t for t in re.split(r"[_.]+", re.sub(r"^[oi]_", "", n))
                                            if t and not re.fullmatch(r"Q|N|p|[EW][NS]|[NS]|\d+", t)).lower()
                    mate = [m for m in mate if aff(m[1]) == aff(bus)]
                if not mate and out_row and self._soft_driver(r, bus, want, reach, old):
                    done.add(k)
                    continue
                if len(mate) != 1:
                    raise SplitError(f"{self.tn}: row {r['conn']} core end {have} != netlist {want} and no unique "
                                     f"swapped mate ({[b for _, b in mate]})")
                k2, b2 = mate[0]
                q = rows[k2]
                oldq = dict(from_um=q["from_um"], to_um=q["to_um"], n=len(q["regs_um"]),
                            end=q.get("launch" if out_row else "capture"))
                ce, ek = ("from_um", "launch") if out_row else ("to_um", "capture")
                for x, y in ((r, q),):
                    x[ce], y[ce] = y[ce], x[ce]
                    x[ek], y[ek] = y[ek], x[ek]
                    x["regs_um"], y["regs_um"] = y["regs_um"], x["regs_um"]
                for x, o, b in ((r, old, bus), (q, oldq, b2)):
                    how = "swap"
                    if not self._hops_ok(x, reach):
                        x["regs_um"] = self._lroute(x["from_um"], x["to_um"], 0, reach)
                        how = "swap+lroute"
                    x["note"] = (f"{self.ev.tag} BASE-DEFECT: core end {o['end']} -> {x.get(ek)} (netlist; {how}), "
                                 f"{o['n']} -> {len(x['regs_um'])} stations | " + x.get("note", ""))
                    self.defect[b] = (o["n"], len(x["regs_um"]))
                    self.rep.setdefault("base_defect_rows", []).append(
                        dict(conn=x["conn"], how=how, old=o, new=dict(from_um=x["from_um"], to_um=x["to_um"],
                                                                     n=len(x["regs_um"]), end=x.get(ek))))
                done |= {k, k2}
            elif want[0] == "fwd" and out_row:
                src = want[1]
                if src not in bw or bw[src]["dir"] != "in":
                    raise SplitError(f"{self.tn}: row {r['conn']} netlist forward source {src} is not an input bus")
                A = [rnd(v, 3) for v in self._face_point(src)]
                r["from_um"] = A
                r["regs_um"] = self._lroute(A, r["to_um"], 0, reach)
                r["launch"] = "bus " + src
                r["capture"] = "face bus " + bus
                r["note"] = (f"{self.ev.tag} BASE-DEFECT: launch {old['end']} -> forward of {src} (netlist), "
                             f"{old['n']} -> {len(r['regs_um'])} stations on an L route | " + r.get("note", ""))
                self.defect[bus] = (old["n"], len(r["regs_um"]))
                self.rep.setdefault("base_defect_rows", []).append(
                    dict(conn=r["conn"], how="forward", old=old, new=dict(from_um=A, to_um=r["to_um"],
                                                                          n=len(r["regs_um"]), end=r["launch"])))
                done.add(k)
            else:
                raise SplitError(f"{self.tn}: row {r['conn']} core end {have} != netlist {want} (not handled)")
        return rows

    def _soft_driver(self, r, bus, want, reach, old):
        """BASE-DEFECT (soft-driver, DIE-KV-100 approved): the netlist driver of an OUT row is a soft content instance
        (no plan position) in another piece than the row's core end.  The core end moves into the driver's piece at
        the cut face nearest the port, at the row's own crossing x; the launch is the netlist driver pin (base bind);
        stations re-derived at reach.  False when the rule does not apply (the caller fails closed)."""
        inst = want[1]
        if any(self._same_inst(inst, h["inst"]) for h in self.t.get("hard_cores", [])):
            return False
        try:
            dp = self._local_piece_of(inst)
        except SplitError:
            return False
        pp = self.bp(bus)
        if dp == pp:
            return False
        pins = []
        for h in [p["name"] for p in self.ev.raw["partitions"] if p["type"] == self.tn]:
            pins += [x for x in ((getattr(self.ev, "census", None) or {}).get("drv_pins", {}).get(h, {}).get(bus, []))
                     if self._same_inst(self._top(x[0]), inst)]
        if not pins:
            return False
        cell, port, _n = max(pins, key=lambda x: x[2])
        cut, ax = self.cut, self.cut.ax
        c = cut.lo(dp) if dp > pp else cut.hi(dp)          # the driver piece's cut face towards the port
        inward = 2.16 if dp > pp else -2.16
        A = [0.0, 0.0]
        A[ax] = rnd(c + inward, 3)
        A[1 - ax] = rnd(float(r["from_um"][1 - ax]), 3)
        r["from_um"] = A
        r["regs_um"] = self._lroute(A, r["to_um"], 0, reach)
        r["launch"] = f"{cell}.{port}"
        r["note"] = (f"{self.ev.tag} BASE-DEFECT (soft-driver): launch {old['end']} -> {r['launch']} (netlist driver, "
                     f"soft, piece {dp}); core end at its cut face {A}, {old['n']} -> {len(r['regs_um'])} stations | "
                     + r.get("note", ""))
        self.defect[bus] = (old["n"], len(r["regs_um"]))
        self.rep.setdefault("base_defect_rows", []).append(
            dict(conn=r["conn"], how="soft-driver", old=old, new=dict(from_um=A, to_um=r["to_um"],
                                                                     n=len(r["regs_um"]), end=r["launch"])))
        return True

    def _local_piece_of(self, inst):
        """piece of a type-local content instance (content rows, then the spec content rules)"""
        if inst in self.content_piece:
            return self.content_piece[inst]
        rules = [(re.compile(rx), int(i)) for rx, i in self.ev.spec.get("contents", {}).get(self.tn, [])]
        v = next((i for rx, i in rules if rx.fullmatch(inst)), None)
        if v is None:
            raise SplitError(f"{self.tn}: instance {inst} has no piece")
        return v

    def _reanchor(self, r, bw, reach):
        """a leg whose face end does not sit in its bus's port-window piece (stale row: the port window moved after
        the chain was drawn) is redrawn from the actual window point: L route (along the face first), the same
        station count evenly spaced, more stations only when a hop would exceed reach (reported)"""
        bus = r["conn"][4:]
        ends = []
        if str(r.get("launch", "")).startswith("face"):
            ends.append(("from_um", bus if bw[bus]["dir"] == "in" else None))
        m = re.match(r"^bus (\w+)$", str(r.get("launch", "")))
        if m:
            ends.append(("from_um", m.group(1)))
        if str(r.get("capture", "")).startswith("face"):
            ends.append(("to_um", bus))
        fix = []
        for k, b in ends:
            if b is None or b not in self.bus_piece:
                continue
            if self.cut.ppiece(r[k]) != self.bus_piece[b]:
                fix.append((k, self._face_point(b)))
        if not fix:
            return r
        r = copy.deepcopy(r)
        old = dict(from_um=r["from_um"], to_um=r["to_um"], n=len(r["regs_um"]))
        for k, p in fix:
            r[k] = [rnd(p[0], 3), rnd(p[1], 3)]
        A, B = r["from_um"], r["to_um"]
        on_ew = min(A[0], self.W - A[0]) < 2.0
        corner = [B[0], A[1]] if on_ew else [A[0], B[1]]
        poly = [A, corner, B]
        segs = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(poly, poly[1:])]
        Ltot = sum(segs)
        n = max(len(r["regs_um"]), math.ceil(Ltot / (reach - 8.64)) - 1)
        regs = []
        for k in range(1, n + 1):
            d = Ltot * k / (n + 1)
            for (a, b), sl in zip(zip(poly, poly[1:]), segs):
                if d <= sl or sl == segs[-1] and (a, b) == (poly[-2], poly[-1]):
                    f = d / sl if sl else 0.0
                    regs.append([rnd(a[0] + (b[0] - a[0]) * f, 3), rnd(a[1] + (b[1] - a[1]) * f, 3)])
                    break
                d -= sl
        r["regs_um"] = regs
        r["note"] = (f"{self.ev.tag}: face end re-anchored on the bus port window ({[k for k, _ in fix]}; stale "
                     f"{old['from_um']}->{old['to_um']}), {old['n']} -> {n} stations evenly on an L route | "
                     + r.get("note", ""))
        self.rep.setdefault("legs_reanchored", []).append(dict(conn=r["conn"], ends=[k for k, _ in fix], old=old,
                                                               new=dict(from_um=A, to_um=B, n=n)))
        return r

    def _fold_x(self, p, q, c, x0, reach):
        """x on the cut line c with |p -> (x, c)| and |(x, c) -> q| both <= reach (Manhattan), nearest x0; None if none"""
        ax = self.cut.ax
        r1 = reach - abs(c - float(p[ax]))
        r2 = reach - abs(float(q[ax]) - c)
        if r1 < 0 or r2 < 0:
            return None
        L = self.W if ax == 1 else self.H
        lo = max(float(p[1 - ax]) - r1, float(q[1 - ax]) - r2, 8.64)
        hi = min(float(p[1 - ax]) + r1, float(q[1 - ax]) + r2, L - 8.64)
        lo, hi = lo + 2 * G, hi - 2 * G           # room for the window grid snap
        if lo > hi:
            return None
        return rnd(round(min(hi, max(lo, x0)) / G) * G, 3)

    # -------------------------------------------------------------- clock
    def _clock(self):
        t, cut, T = self.t, self.cut, self.T
        ck = t.get("clock") or {}
        known = {"tap_um", "layer", "insertion_ps", "insertion_tol_ps", "tap_pitch_um", "tap_edge_y_um", "taps",
                 "core_taps", "edge_clocks", "landing_contract", "added_taps", "tap_mode", "sink_sites_um",
                 "reach_fix_sinks", "tap_radius_um", "tap_max_sinks", "tap_target_sinks", "die_islands_um",
                 "keepouts_um", "sink_bins_file", "landing_ring_wreg"}
        drop = set(self.ev.spec.get("drop_clock_keys") or [])
        unk = set(ck) - known - drop
        if unk:
            raise SplitError(f"{self.tn}: unhandled clock keys {sorted(unk)} (a START / raw transport key can only be "
                             f"dropped for re-derivation: spec drop_clock_keys)")
        if ck.get("tap_mode") not in (None, "grid", "grid+explicit", "density"):
            raise SplitError(f"{self.tn}: clock.tap_mode {ck.get('tap_mode')} not handled")
        dropped_keys = sorted(drop & set(ck))
        if dropped_keys:
            self.rep["clock_keys_dropped"] = dropped_keys
        import schema as S
        P = S.Plan(self.ev.raw, None)
        grid = S._grid_taps(P, self.tn)
        added = ck.get("added_taps") or []
        self.tapmap = [dict() for _ in range(self.n)]
        for i in range(self.n):
            c = T[i]["clock"] = {k: copy.deepcopy(v) for k, v in ck.items()
                                 if k not in ("taps", "edge_clocks", "landing_contract", "added_taps", "sink_sites_um",
                                              "reach_fix_sinks", "tap_um", "tap_edge_y_um", "die_islands_um",
                                              "keepouts_um", "sink_bins_file", "landing_ring_wreg") and k not in drop}
            for k in ("die_islands_um", "keepouts_um"):
                if k in ck:
                    # a reservation / keep-out rect is kept on every piece it touches (clipped: the part inside)
                    lo, hi = cut.lo(i), cut.hi(i)
                    rr = []
                    for r in ck[k]:
                        a, b = max(r[cut.ax], lo), min(r[cut.ax + 2], hi)
                        if b - a > EPS:
                            q = list(r)
                            q[cut.ax], q[cut.ax + 2] = a, b
                            rr.append(cut.shr(q, i))
                            if a > r[cut.ax] + EPS or b < r[cut.ax + 2] - EPS:
                                self.rep.setdefault("clock_rects_clipped", []).append(dict(key=k, rect=r, piece=i))
                    c[k] = rr
            if "sink_bins_file" in ck:
                self.sink_bins = getattr(self, "sink_bins", None) or self._load_sink_bins(ck["sink_bins_file"])
                c["sink_bins_file"] = ("__PIECE__", i)
            centre = [rnd(round(v / 2 / 8.64) * 8.64) for v in T[i]["outline_um"]]
            if "tap_um" in ck:
                c["tap_um"] = (cut.sh(ck["tap_um"], i) if cut.ppiece(ck["tap_um"]) == i else centre)
            if "tap_edge_y_um" in ck:
                if cut.ax != 1:
                    raise SplitError(f"{self.tn}: tap_edge_y_um with an x cut is not handled")
                h = T[i]["outline_um"][1]
                e = [rnd(y - cut.lo(i)) for y in ck["tap_edge_y_um"] if cut.lo(i) - EPS <= y <= cut.hi(i) + EPS]
                c["tap_edge_y_um"] = e or [rnd(21.6 if i < self.n - 1 else h - 21.6)]
            c["taps"] = []
            for tp in ck.get("taps", []):
                s = cut.ppiece(tp["xy"], f"{self.tn} core tap {tp['name']}")
                if s == i:
                    c["taps"].append(copy.deepcopy(tp) | {"xy": cut.sh(tp["xy"], i)})
            for k in ("sink_sites_um", "reach_fix_sinks"):
                if k in ck:
                    c[k] = [cut.sh(p[:2], i) + list(p[2:]) for p in ck[k] if cut.ppiece(p, f"{self.tn} {k}") == i]
        # grid taps of each piece, then the added taps in their old order, renamed after the piece grid
        sub = copy.deepcopy(self.ev.raw)
        for i in range(self.n):
            sub["partition_types"][self.tnames[i] + "__probe"] = dict(T[i], hard=False)
        P2 = S.Plan(sub, None)
        for i in range(self.n):
            g = S._grid_taps(P2, self.tnames[i] + "__probe")
            mine = [a for a in added if cut.ppiece(a["xy"], f"{self.tn} added tap {a['name']}") == i]
            # taps.grid_explicit_sites legality in the piece: clear of the (new) outline, of the piece grid taps and
            # of the placement boxes; an added tap at a cut slides inward, one on a grid tap is dropped (the grid tap
            # serves its sinks)
            from placement_obstacles import placement_boxes
            clear = S.TAP_CLEAR_UM
            w, h = T[i]["outline_um"]
            boxes = list(placement_boxes(T[i], halo=clear).values())
            taken = [(x, y) for _, x, y in g]
            kept, dropped = [], []
            for a in mine:
                x, y = cut.sh(a["xy"], i)
                x = min(max(x, clear), w - clear)
                y = min(max(y, clear), h - clear)
                if any(abs(x - p) < clear and abs(y - q) < clear for p, q in taken) or \
                        any(b0 < x < b2 and b1 < y < b3 for b0, b1, b2, b3 in boxes):
                    dropped.append(a["name"])
                    continue
                kept.append((a, [rnd(x), rnd(y)]))
                taken.append((x, y))
            mine = [a for a, _ in kept]
            T[i]["clock"]["added_taps"] = [dict(name=f"clk_t{len(g) + k}", xy=xy) for k, (a, xy) in enumerate(kept)]
            sites = [(n_, x, y) for n_, x, y in g] + [(f"clk_t{len(g) + k}", xy[0], xy[1]) for k, (a, xy) in enumerate(kept)]
            for k, (a, xy) in enumerate(kept):
                self.tapmap[i][a["name"]] = f"clk_t{len(g) + k}"
            # old grid taps and dropped added taps: the nearest tap of the piece (landing pins' source_clock_tap)
            for n_, x0, y0 in [(n_, x, y) for n_, x, y in grid] + [(a["name"], *a["xy"]) for a in added]:
                if n_ in self.tapmap[i]:
                    continue
                p = cut.sh([x0, y0], i)
                self.tapmap[i][n_] = min(sites, key=lambda s_: abs(s_[1] - p[0]) + abs(s_[2] - p[1]))[0]
            if dropped:
                self.rep.setdefault("taps_dropped", {})[self.tnames[i]] = dropped
            self.rep.setdefault("taps", {})[self.tnames[i]] = dict(grid=len(g), added=len(mine))
            if not added and "added_taps" in T[i]["clock"] and not ck.get("added_taps"):
                del T[i]["clock"]["added_taps"]
        old_grid = {n_: (x, y) for n_, x, y in grid}
        self.rep["old_grid_taps"] = len(old_grid)
        # edge clocks by bus
        for i in range(self.n):
            T[i]["clock"]["edge_clocks"] = []
        for e in ck.get("edge_clocks", []):
            m = re.match(r"^fclk_in_(.*)$", e["port"])
            if m and COLL_PIN.match(e["port"]):
                s = cut.ppiece(e["tap_um"], f"{self.tn} edge clock {e['port']}")
            elif m:
                s = self.bp(m.group(1))
            else:
                raise SplitError(f"{self.tn}: edge clock {e['port']} not handled")
            T[s]["clock"]["edge_clocks"].append(copy.deepcopy(e) | {"tap_um": cut.sh(e["tap_um"], s)})
        if "edge_clocks" not in ck:
            for i in range(self.n):
                del T[i]["clock"]["edge_clocks"]
        if "landing_ring_wreg" in ck:
            wr = ck["landing_ring_wreg"]
            for i in range(self.n):
                bs = [b for b in wr.get("buses", []) if self.bp(b) == i]
                if bs:
                    T[i]["clock"]["landing_ring_wreg"] = copy.deepcopy(wr) | {"buses": bs}
        self._landing_contract(ck.get("landing_contract"))

    def _load_sink_bins(self, path):
        import taps
        d = json.loads(taps.input_path(path, self.ev.plan_dir).read_text())
        out = [dict(d, bins=[], note=f"{self.ev.tag}: piece {i} of {path} (bins by centre, piece frame)")
               for i in range(self.n)]
        for b in d["bins"]:
            i = self.cut.ppiece(b[:2], f"{self.tn} sink bin")
            out[i]["bins"].append(self.cut.sh(b[:2], i) + list(b[2:]))
        for i in range(self.n):
            out[i]["n"] = sum(int(b[2]) for b in out[i]["bins"]) if all(len(b) > 2 for b in out[i]["bins"]) else d.get("n")
            out[i]["type"] = self.tnames[i]
        return out

    def _landing_contract(self, lc):
        if lc is None:
            return
        cut, T = self.cut, self.T
        known = {"pins", "bands", "base_type", "registered_monitor", "physical_qualified", "collector_tree",
                 "collector_root_node", "collector_local_sources", "collector_children", "forwarded_clock_only_inputs"}
        unk = set(lc) - known
        if unk:
            raise SplitError(f"{self.tn}: unhandled landing_contract keys {sorted(unk)}")
        L = []
        for i in range(self.n):
            d = {k: copy.deepcopy(v) for k, v in lc.items() if k not in ("pins", "bands", "collector_tree",
                                                                       "collector_local_sources", "collector_children")}
            d["base_type"] = self.tnames[i]
            d["pins"], d["bands"] = [], {}
            d["collector_local_sources"], d["collector_children"] = [], []
            d["collector_tree"] = copy.deepcopy(lc.get("collector_tree"))     # republished after the split
            T[i]["clock"]["landing_contract"] = d
            L.append(d)
        self.band_clip = []
        for p in lc.get("pins", []):
            m = LAND_PIN.match(p["name"])
            cm = COLL_PIN.match(p["name"])
            if cm or p["name"] in START_PINS:
                s = cut.ppiece(p["xy_um"], f"{self.tn} pin {p['name']}")
            elif m:
                s = self.bp(m.group(2))
            else:
                raise SplitError(f"{self.tn}: landing pin {p['name']} not handled")
            q = copy.deepcopy(p) | {"xy_um": cut.sh(p["xy_um"], s)}
            if "native_entry_reference_um" in q:
                q["native_entry_reference_um"] = cut.sh(q["native_entry_reference_um"], s)
            if p["name"] in START_PINS and s != self.keep:
                # the region origin (keep piece) holds the START pins: same in-piece offset, moved into the keep piece
                lim = T_ext = cut.ext(self.keep)
                for k in ("xy_um", "native_entry_reference_um"):
                    if k in q:
                        v = q[k][cut.ax]
                        q[k][cut.ax] = rnd(v if s < self.keep else T_ext - (cut.ext(s) - v))
                        if not 0 <= q[k][cut.ax] <= lim:
                            raise SplitError(f"{self.tn}: START pin {p['name']} does not fit the keep piece")
                q["note"] = (q.get("note", "") + f" | {self.ev.tag}: moved from piece {s} to the region origin piece "
                             f"{self.keep} (same in-piece offset)").lstrip(" |")
                self.rep.setdefault("start_pins_moved", []).append(dict(pin=p["name"], from_piece=s, xy=q["xy_um"]))
                s = self.keep
            if "source_clock_tap" in q:
                q["source_clock_tap"] = self.tapmap[s].get(q["source_clock_tap"], q["source_clock_tap"])
            L[s]["pins"].append(q)
        # a pin that follows its bus into a piece but sat just across the cut (beside a window near the cut) is
        # nudged inward along the cut axis on a 0.96-um step, clear of the other landing pins of its layer
        for s in range(self.n):
            ext, pins = cut.ext(s), L[s]["pins"]
            for q in pins:
                v = q["xy_um"][cut.ax]
                if PIN_MARGIN - 1e-6 <= v <= ext - PIN_MARGIN + 1e-6:
                    continue
                used = {(x["layer"], round(x["xy_um"][1 - cut.ax], 3), round(x["xy_um"][cut.ax], 2))
                        for x in pins if x is not q}
                step = -PIN_STEP if v > ext / 2 else PIN_STEP
                w = v
                for _ in range(400):
                    w = rnd(w + step)
                    if PIN_MARGIN <= w <= ext - PIN_MARGIN and \
                            not any((q["layer"], round(q["xy_um"][1 - cut.ax], 3)) == u[:2] and abs(u[2] - w) < 0.5
                                    for u in used):
                        break
                else:
                    raise SplitError(f"{self.tn}: landing pin {q['name']} has no free site inside piece {s}")
                q["xy_um"][cut.ax] = w
                if "native_entry_reference_um" in q:
                    q["native_entry_reference_um"][cut.ax] = w
                q["note"] = (q.get("note", "") + f" | {self.ev.tag}: nudged {v:.3f} -> {w:.3f} into piece {s} "
                             f"(its bus sits in this piece)").lstrip(" |")
                self.rep.setdefault("pins_nudged", []).append(dict(pin=q["name"], piece=s, old=v, new=w))
        # seam child monitor rings (bands monitor_<index>) follow their child
        cidx, cnt = {}, [0] * self.n
        for ch in lc.get("collector_children", []):
            s = cut.ppiece(ch["xy_um"], f"{self.tn} collector child {ch['part']}")
            cidx[int(ch["index"])] = (s, cnt[s])
            cnt[s] += 1
        for bus, b in (lc.get("bands") or {}).items():
            mm = re.match(r"^monitor_(\d+)$", bus)
            if mm:
                s, k = cidx[int(mm.group(1))]
                bb = copy.deepcopy(b)
                bb["rect_um"] = cut.shr(b["rect_um"], s)
                if cut.rect_piece(b["rect_um"], f"{self.tn} band {bus}") != s:
                    raise SplitError(f"{self.tn}: monitor band {bus} is not in its child's piece {s}")
                if "instance" in bb:
                    bb["instance"] = f"u_cland_monitor_{k}"
                L[s]["bands"][f"monitor_{k}"] = bb
                continue
            s = self.bp(bus)
            bb = copy.deepcopy(b)
            r = b["rect_um"]
            lo, hi = cut.lo(s), cut.hi(s)
            if r[cut.ax] < lo - EPS or r[cut.ax + 2] > hi + EPS:
                rr = list(r)
                rr[cut.ax], rr[cut.ax + 2] = max(r[cut.ax], lo), min(r[cut.ax + 2], hi)
                old_a = (r[2] - r[0]) * (r[3] - r[1])
                new_a = (rr[2] - rr[0]) * (rr[3] - rr[1])
                need = float(b.get("area_reserve_um2", 0.0))
                how = "clipped"
                if new_a < need - EPS:
                    # too little area left on the bus side: slide the whole band into the piece (same size)
                    span = r[cut.ax + 2] - r[cut.ax]
                    if span > hi - lo - 2 * 8.64:
                        raise SplitError(f"{self.tn}: band {bus} {r} neither clips ({new_a:.1f} < reserve {need:.1f} "
                                         f"um2) nor fits piece {s}")
                    rr = list(r)
                    a0 = min(max(r[cut.ax], lo + 8.64), hi - 8.64 - span)
                    a0 = round(a0 / 0.27) * 0.27 if a0 > lo + 8.64 else a0
                    rr[cut.ax], rr[cut.ax + 2] = rnd(a0, 4), rnd(a0 + span, 4)
                    new_a, how = old_a, "moved"
                self.band_clip.append(dict(bus=bus, how=how, old=r, new=rr, area=[rnd(old_a, 2), rnd(new_a, 2)],
                                           reserve=need))
                bb["rect_um"] = rr
                if how == "clipped" and new_a > 0 and "band_use" in bb:
                    bb["band_use"] = rnd(need / new_a, 4)
                bb["resize"] = (bb.get("resize", "") + f" | {self.ev.tag}: {how} into piece {s}").lstrip(" |")
            bb["rect_um"] = cut.shr(bb["rect_um"], s)
            if "rects_um" in bb:
                bb["rects_um"] = [cut.shr(x, s) for x in bb["rects_um"] if cut.rect_piece(x, f"{self.tn} band {bus}") == s]
            L[s]["bands"][bus] = bb
        self.rep["band_clip"] = self.band_clip
        for src in lc.get("collector_local_sources", []):
            s = self.bp(src["name"])
            q = copy.deepcopy(src)
            for k in ("xy_um", "pin_xy_um"):
                if k in q:
                    q[k] = cut.sh(q[k], s)
            if "band" in q:
                q["band"] = copy.deepcopy(L[s]["bands"].get(src["name"], q["band"]))
            L[s]["collector_local_sources"].append(q)
        idx = [0] * self.n
        self.child_map = {}
        for ch in lc.get("collector_children", []):
            s = cut.ppiece(ch["xy_um"], f"{self.tn} collector child {ch['part']}")
            q = copy.deepcopy(ch)
            q["xy_um"] = cut.sh(ch["xy_um"], s)
            old = int(ch["index"])
            q["index"] = idx[s]
            q["ready"], q["fault"] = f"cland_dn_ready_{idx[s]}", f"cland_dn_fault_{idx[s]}"
            self.child_map[old] = (s, idx[s])
            idx[s] += 1
            L[s]["collector_children"].append(q)
        # collector child pins renumbered with their child
        for i in range(self.n):
            for p in L[i]["pins"]:
                cm = COLL_PIN.match(p["name"])
                if cm and p["name"].startswith(("cland_dn_", "fclk_in_cland_dn_")):
                    old = int(re.search(r"(\d+)$", p["name"]).group(1))
                    s, k = self.child_map[old]
                    if s != i:
                        raise SplitError(f"{self.tn}: pin {p['name']} in piece {i}, its child in piece {s}")
                    p["name"] = re.sub(r"\d+$", str(k), p["name"])
            for e in T[i]["clock"].get("edge_clocks", []):
                if e["port"].startswith("fclk_in_cland_dn_"):
                    old = int(re.search(r"(\d+)$", e["port"]).group(1))
                    e["port"] = "fclk_in_cland_dn_%d" % self.child_map[old][1]
        self.child_idx = idx
        # up pins: on the keep piece only (it keeps the parent link)
        up = {cut.ppiece(p["xy_um"]) for p in lc.get("pins", []) if p["name"].startswith(("cland_up_", "fclk_out_cland_up"))}
        if up and up != {self.keep}:
            raise SplitError(f"{self.tn}: collector up pins in pieces {sorted(up)}, keep piece {self.keep}")
        # the other pieces: collector children across the cut (same region: no seam clock), each of its neighbour
        # towards the keep piece (a chain when a piece is not adjacent to the keep piece: the neighbour relays it)
        self.coll_links = []
        order = sorted((i for i in range(self.n) if i != self.keep), key=lambda i: abs(i - self.keep))
        for i in order:
            to_keep = self.keep > i
            nb = i + 1 if to_keep else i - 1
            k = idx[nb]
            idx[nb] += 1
            # pin sites: on the cut face shared with the neighbour towards the keep piece, mid-span
            mid = rnd(round(((self.W if cut.ax == 1 else self.H) / 2) / 8.64) * 8.64)
            up_xy = [0.0, 0.0]
            up_xy[cut.ax] = rnd(cut.ext(i) - 2.656) if to_keep else 2.656
            up_xy[1 - cut.ax] = mid
            dn_xy = [0.0, 0.0]
            dn_xy[cut.ax] = 2.656 if to_keep else rnd(cut.ext(nb) - 2.656)
            dn_xy[1 - cut.ax] = mid
            L[i]["pins"] += [dict(name="cland_up_ready", dir="out", kind="ctl", layer="M7", xy_um=list(up_xy), epoch=False),
                             dict(name="cland_up_fault", dir="out", kind="ctl", layer="M7",
                                  xy_um=[up_xy[0] + (2.496 if cut.ax == 1 else 0), up_xy[1] + (0 if cut.ax == 1 else 2.496)],
                                  epoch=False)]
            L[nb]["pins"] += [
                dict(name=f"cland_dn_ready_{k}", dir="in", kind="ctl", layer="M7", xy_um=list(dn_xy), epoch=False),
                dict(name=f"cland_dn_fault_{k}", dir="in", kind="ctl", layer="M7",
                     xy_um=[dn_xy[0] + (2.112 if cut.ax == 1 else 0), dn_xy[1] + (0 if cut.ax == 1 else 2.112)],
                     epoch=False)]
            L[nb]["collector_children"].append(dict(
                part=None, node=None, xy_um=list(dn_xy), seam=False, index=k, ready=f"cland_dn_ready_{k}",
                fault=f"cland_dn_fault_{k}", tap=None, _piece=i))
            # count-aligned intra-region START relay (clock_landings: origin tx flop -> relay rx flop, 2 counts)
            rx_xy = list(up_xy)
            rx_xy[1 - cut.ax] = rnd(mid - 4.32)
            L[i]["pins"].append(dict(name="cland_rstart_in", dir="in", kind="ctl", layer="M7", xy_um=rx_xy,
                                     epoch=False))
            self.coll_links.append(dict(child_piece=i, parent_piece=nb, index=k, up_xy=up_xy, dn_xy=dn_xy, rx_xy=rx_xy))
        if self.coll_links:
            mid = rnd(round(((self.W if cut.ax == 1 else self.H) / 2) / 8.64) * 8.64)
            tx = [0.0, 0.0]
            tx[cut.ax] = rnd(round(cut.ext(self.keep) / 2 / 0.27) * 0.27)
            tx[1 - cut.ax] = rnd(mid - 4.32)
            L[self.keep]["pins"].append(dict(name="cland_rstart_out", dir="out", kind="ctl", layer="M7", xy_um=tx,
                                             epoch=False))
            self.tx_xy = tx
        self.infra_x = rnd(round(((self.W if cut.ax == 1 else self.H) / 2) / 8.64) * 8.64)

    # -------------------------------------------------------------- reset
    def _reset(self):
        t, cut, T = self.t, self.cut, self.T
        rs = t.get("reset")
        if rs is None:
            return
        unk = set(rs) - {"tap_um", "sync_stages", "start_role", "local_taps_um", "obstacle_model"}
        if unk:
            raise SplitError(f"{self.tn}: unhandled reset keys {sorted(unk)}")
        for i in range(self.n):
            r = T[i]["reset"] = copy.deepcopy(rs)
            centre = [rnd(round(v / 2 / 8.64) * 8.64) for v in T[i]["outline_um"]]
            if "tap_um" in rs:
                r["tap_um"] = cut.sh(rs["tap_um"], i) if cut.ppiece(rs["tap_um"]) == i else centre
            if "local_taps_um" in rs:
                r["local_taps_um"] = [cut.sh(p, i) for p in rs["local_taps_um"] if cut.ppiece(p) == i] or [[8.64, 8.64]]

    def _reset_spine_pins(self):
        """reset_spine_pins (bound-only ri_*/rs_* wrapper pins of a reset net, one interior site per bit): the pin goes
        to the piece of the content / hard core its name names (ri_<inst with __ -> _>_rst_n), else to the piece of its
        sites.  A site outside that piece is re-sited by the pin's own rule (nearest the piece's reset tap on the 8.64
        lattice, clear of the piece's hard cores) and reported."""
        t, cut, T = self.t, self.cut, self.T
        sp = t.get("reset_spine_pins")
        if sp is None:
            return
        for i in range(self.n):
            T[i]["reset_spine_pins"] = []
        insts = sorted({c["inst"] for c in t.get("contents", [])} | {h["inst"] for h in t.get("hard_cores", [])},
                       key=len, reverse=True)
        for q in sp:
            who = next((c for c in insts if c.replace("__", "_") in q["name"]), None)
            if who is not None:
                i = self.ev._local_piece(self, who)
            else:
                ps = {cut.ppiece(x, f"{self.tn} reset spine pin {q['name']}") for x in q["sites_um"]}
                if len(ps) != 1:
                    raise SplitError(f"{self.tn}: reset spine pin {q['name']} sites in pieces {sorted(ps)}")
                i = ps.pop()
            qq = copy.deepcopy(q)
            sites = []
            for x in q["sites_um"]:
                if cut.ppiece(x) == i:
                    sites.append(cut.sh(x, i))
                    continue
                tap = T[i].get("reset", {}).get("tap_um") or [v / 2 for v in T[i]["outline_um"]]
                boxes = [(h["origin_um"][0], h["origin_um"][1],
                          h["origin_um"][0] + h["outline_um"][h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90")],
                          h["origin_um"][1] + h["outline_um"][h.get("orient", "R0") not in ("R90", "R270", "MXR90", "MYR90")])
                         for h in T[i].get("hard_cores", [])]
                g = 8.64
                cands = sorted(((abs(gx * g - tap[0]) + abs(gy * g - tap[1]), gx * g, gy * g)
                                for gx in range(1, int(T[i]["outline_um"][0] / g))
                                for gy in range(1, int(T[i]["outline_um"][1] / g))
                                if abs(gx * g - tap[0]) + abs(gy * g - tap[1]) < 400), key=lambda c: c[0])
                site = next(([rnd(a), rnd(b)] for _, a, b in cands
                             if not any(b0 - 2.16 <= a <= b2 + 2.16 and b1 - 2.16 <= b <= b3 + 2.16
                                        for b0, b1, b2, b3 in boxes)
                             and [rnd(a), rnd(b)] not in sites), None)
                if site is None:
                    raise SplitError(f"{self.tn}: reset spine pin {q['name']}: no free site in piece {i}")
                sites.append(site)
                self.rep.setdefault("reset_spine_resited", []).append(dict(pin=q["name"], piece=i, old=x, new=site))
            qq["sites_um"] = sites
            if sites != [cut.sh(x, i) for x in q["sites_um"]]:
                qq["note"] = (qq.get("note", "") + f" | {self.ev.tag}: re-sited in piece {i} (its consumer's piece)")
            T[i]["reset_spine_pins"].append(qq)
        for i in range(self.n):
            if not T[i]["reset_spine_pins"]:
                del T[i]["reset_spine_pins"]

    def _pads(self):
        """pads (die IO pads a partition hosts): every pad goes to the keep piece unless spec pads_piece names it;
        a pad with a site goes by its site.  Shapes other than a list of dicts fail closed."""
        t, cut, T = self.t, self.cut, self.T
        pads = t["pads"]
        if not isinstance(pads, list) or not all(isinstance(p, dict) for p in pads):
            raise SplitError(f"{self.tn}: pads form {type(pads).__name__} not handled")
        want = (self.ev.spec.get("pads_piece") or {}).get(self.tn, {})
        for i in range(self.n):
            T[i]["pads"] = []
        for p in pads:
            pp = copy.deepcopy(p)
            xy = p.get("xy_um") or p.get("site_um")
            mp = (p.get("macro_pin") or {}).get("inst")
            if p.get("name") in want:
                i = int(want[p["name"]])
            elif mp:
                # the pad lands on a macro pin: the piece of that content (u_bound.<inst> -> content <inst>)
                segs = mp.split(".")
                i = None
                for k in range(len(segs)):
                    for cand in (".".join(segs[k:]), segs[-1].removeprefix("u_")):
                        try:
                            i = self.ev._local_piece(self, cand)
                            break
                        except SplitError:
                            continue
                    if i is not None:
                        break
                if i is None:
                    raise SplitError(f"{self.tn}: pad {p.get('name')} macro {mp} has no piece (spec pads_piece)")
            elif xy is not None:
                i = cut.ppiece(xy, f"{self.tn} pad {p.get('name')}")
            else:
                i = self.keep
            for k in ("xy_um", "site_um"):
                if k in pp:
                    if cut.ppiece(pp[k]) != i:
                        raise SplitError(f"{self.tn}: pad {p.get('name')} site is not in piece {i}")
                    pp[k] = cut.sh(pp[k], i)
            T[i]["pads"].append(pp)
        for i in range(self.n):
            if not T[i]["pads"]:
                del T[i]["pads"]

    # -------------------------------------------------------------- count straps
    def _count_straps(self):
        for i in range(self.n):
            self.T[i]["count_straps"] = []
        for st in self.t.get("count_straps", []):
            m = re.match(r"^strap_ca_k_(.*)$", st["name"])
            if m:
                self.T[self.bp(m.group(1))]["count_straps"].append(copy.deepcopy(st))
            else:
                for i in range(self.n):
                    self.T[i]["count_straps"].append(copy.deepcopy(st))


# --------------------------------------------------------------------------------------------------- cut-face windows
def _nearest(items, out, used, need, length, margin, gap):
    """place each item on the free spot nearest its preferred centre (inside its reach range if it has one)"""
    for it in items:
        k, b, x = it[:3]
        rng = it[3] if len(it) > 3 else None
        n = need(b)
        x = min(max(x, margin + n / 2), length - margin - n / 2)      # a preferred site on the edge slides inside
        # nearest free spot (either side) to the preferred centre
        free, cur = [], margin
        for u0, u1 in sorted(used):
            if u0 - gap > cur:
                free.append((cur, u0 - gap))
            cur = max(cur, u1 + gap)
        free.append((cur, length - margin))
        best = None
        for f0, f1 in free:
            if f1 - f0 < n:
                continue
            c = min(max(x - n / 2, f0), f1 - n)
            c = math.ceil(c / G - 1e-9) * G
            if c + n > f1 + 1e-9:
                c = math.floor((f1 - n) / G + 1e-9) * G
            if c < f0 - 1e-9:
                continue
            if rng is not None and not (rng[0] - 1e-9 <= c + n / 2 <= rng[1] + 1e-9):
                # nearest centre inside both the gap and the reach range
                lo_c, hi_c = max(f0 + n / 2, rng[0]), min(f1 - n / 2, rng[1])
                if lo_c > hi_c + 1e-9:
                    continue
                cc = min(max(x, lo_c), hi_c)
                c = math.ceil((cc - n / 2) / G - 1e-9) * G
                if c + n / 2 > hi_c + 1e-9:
                    c = math.floor((cc - n / 2) / G + 1e-9) * G
                if c < f0 - 1e-9 or c + n > f1 + 1e-9 or not (rng[0] - 1e-9 <= c + n / 2 <= rng[1] + 1e-9):
                    continue
            if best is None or abs(c + n / 2 - x) < abs(best + n / 2 - x):
                best = c
        if best is None:
            occ = sorted((round(u0, 1), round(u1, 1), kk) for kk, segs in out.items() for u0, u1, _ in segs
                         if rng and u1 > rng[0] and u0 < rng[1])
            raise SplitError(f"cut face: {k} ({b} pins, {n:.1f} um) does not fit near x {x}" +
                             (f" inside its reach range {rng}; taken there: {occ}" if rng else ""))
        lo = round(best, 6)
        out[k] = [(round(lo, 3), round(lo + n, 3), b)]
        used.append((lo, lo + n))


def windows_for(items, length, per_um, margin=8.64, gap=2.16):
    """items [(key, pins, x_pref or None[, (cmin, cmax)])] -> {key: [(lo, hi, pins), ...]}: disjoint windows on
    [margin, L - margin].  Fixed-position items first (one window centred on x_pref, shifted past the ones already
    placed); an optional (cmin, cmax) bounds the window centre (reach of the stations either side) -- those items are
    placed first, tightest first, and fail closed outside it; the others fill the free gaps left to right, split over
    several windows (port segments) where a gap is short."""
    def need(b):
        return max(2.16, math.ceil(b / per_um / G + 1) * G)

    def cap(Ln):
        return int(math.floor((Ln / G - 1) * G * per_um + 1e-9))
    out, used = {}, []
    fixed = [i for i in items if i[2] is not None]
    # reach-bounded items first, least slack (range width - window width) first
    fixed.sort(key=lambda i: ((0, i[3][1] - i[3][0] - need(i[1])) if len(i) > 3 and i[3] else (1, 0), i[2], i[0]))
    ranged = [i for i in fixed if len(i) > 3 and i[3]]
    plain = [i for i in fixed if not (len(i) > 3 and i[3])]
    try:
        _nearest(ranged, out, used, need, length, margin, gap)
    except SplitError:
        # nearest-to-preference packs too loosely: earliest-deadline-first left packing of the reach-bounded windows
        out.clear()
        used.clear()
        cur = margin
        for it in sorted(ranged, key=lambda i: (i[3][1] + need(i[1]) / 2, i[0])):
            k, b, x, rng = it[0], it[1], it[2], it[3]
            n = need(b)
            lo = max(cur, rng[0] - n / 2, margin)
            lo = math.ceil(lo / G - 1e-9) * G
            if lo + n / 2 > rng[1] + 1e-9 or lo + n > length - margin + 1e-9:
                occ = sorted((round(u0, 1), round(u1, 1), kk) for kk, segs in out.items() for u0, u1, _ in segs
                             if u1 > rng[0] and u0 < rng[1])
                raise SplitError(f"cut face: {k} ({b} pins, {n:.1f} um) does not fit inside its reach range {rng} "
                                 f"even packed left; taken there: {occ}")
            out[k] = [(round(lo, 3), round(lo + n, 3), b)]
            used.append((lo, lo + n))
            cur = lo + n + gap
    _nearest(plain, out, used, need, length, margin, gap)
    free, cur = [], margin
    for u0, u1 in sorted(used):
        if u0 - gap > cur:
            free.append([cur, u0 - gap])
        cur = max(cur, u1 + gap)
    if length - margin > cur:
        free.append([cur, length - margin])
    for k, b, x in [i[:3] for i in items if i[2] is None]:
        left, segs = b, []
        for f in free:
            if left <= 0:
                break
            Ln = f[1] - f[0]
            if Ln < 4.32:
                continue
            take = min(left, cap(Ln))
            if take <= 0:
                continue
            n = need(take) if take == left else Ln
            segs.append((round(f[0], 3), round(f[0] + n, 3), take))
            f[0] = f[0] + n + gap
            left -= take
        if left > 0:
            raise SplitError(f"cut face full: {k} has {left} of {b} pins without a window at {per_um}/um")
        out[k] = segs
    return out


# ================================================================================================ the plan-level event
CUT_LAYERS = ["M5", "M7"]          # N/S die faces carry the vertical port layers (plan convention: S/N ports M5+M7)
AXIS_LAYERS = {"y": ["M5", "M7"], "x": ["M4", "M6"]}


def _lane_num(raw):
    return max(int(m.group(1)) for m in (re.match(r"^L(\d+)$", l["id"]) for l in raw["lanes"]) if m)


class Event:
    """one split event over a family of types (all take the same cuts)"""

    def __init__(self, spec, spec_dir=None):
        self.spec = spec
        self.tag = spec.get("event", "TYPE-SPLIT")
        self.base_dir = Path(spec_dir) if spec_dir else ROOT
        self.plan_path = rpath(spec["plan"])
        self.raw = json.loads(self.plan_path.read_text())
        self.plan_dir = rpath(spec["plan_dir"]) if spec.get("plan_dir") else self.plan_path.parent
        self.side = json.loads(rpath(spec["sidecar"]).read_text()) if spec.get("sidecar") else None
        self.ab_path = rpath(spec["asbuilt"]) if spec.get("asbuilt") else None
        self.ab = json.loads(self.ab_path.read_text()) if self.ab_path else None
        self.census = json.loads(rpath(spec["census"]).read_text()) if spec.get("census") else None
        self.rep = dict(event=self.tag, base_plan=str(spec["plan"]),
                        base_md5=hashlib.md5(self.plan_path.read_bytes()).hexdigest(), types={}, lanes_added=[],
                        lanes_changed={}, ports_added=[], notes=[])
        fam = spec["family"]
        if len(set(fam)) != len(fam):
            raise SplitError("family lists a type twice")
        self._core_moves()
        lat = spec.get("lattice_um")
        if lat is None:
            import schema as S
            lat = S.Plan(self.raw, None).grid
        bad = [c for c in spec["cuts_um"] if abs(c / lat - round(c / lat)) > 1e-6]
        if bad:
            raise SplitError(f"cuts {bad} are not on the {lat:g}-um partition lattice (piece outlines / origins)")
        self.ts = {}
        for tn in fam:
            if tn not in self.raw["partition_types"]:
                raise SplitError(f"family type {tn} is not in the plan")
            self.ts[tn] = TypeSplit(self, tn)

    # ---------------------------------------------------------------- core moves (before the split)
    def _core_moves(self):
        """spec core_moves {type: {inst: [x, y]}}: a hard core MOVES (never re-shaped) to a new origin on the plan
        lattice, track_offset_um kept, so its pins shift by (new - old) and must stay on their layer tracks; its clock
        taps (name '<inst>.<pin>') move with it.  spec station_moves {type: {slot: {reg index: [dx, dy]}}} moves an ft
        station reg and its bit sites (bit_sites_um[j] belongs to regs_um[j + 1]) out of a moved box.
        Fail closed: a box outside the outline or overlapping another core, a pin off its track, a moved ft hop over
        reach, or any plan point (ft reg / bit site, internal-station reg, tap, reset / collector site) that the moves
        newly put inside a moved core box."""
        moves = self.spec.get("core_moves") or {}
        smoves = self.spec.get("station_moves") or {}
        if not moves and not smoves:
            return
        import schema as S
        P = S.Plan(self.raw, None)
        grid = P.grid
        reach = float(self.raw.get("budgets", {}).get("ft_station_max_um", 405.0))
        rec = []
        for tn in sorted(set(moves) | set(smoves)):
            t = self.raw["partition_types"].get(tn)
            if t is None:
                raise SplitError(f"core_moves: type {tn} is not in the plan")
            cores = {h["inst"]: h for h in t.get("hard_cores", [])}
            W, H = t["outline_um"]

            def box(h, org=None):
                ox, oy = org or h["origin_um"]
                dx, dy = h.get("track_offset_um", [0.0, 0.0])
                cw, chh = h["outline_um"]
                if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
                    cw, chh = chh, cw
                return (ox + dx, oy + dy, ox + dx + cw, oy + dy + chh)

            def inside(p, b):
                return b[0] + EPS < p[0] < b[2] - EPS and b[1] + EPS < p[1] < b[3] - EPS

            def points(tt):
                out = []
                for f in tt.get("ft_slots", []):
                    out += [(f"ft {f['name']} reg {j}", r) for j, r in enumerate(f["regs_um"])]
                    for j, st in enumerate(f.get("bit_sites_um") or []):
                        out += [(f"ft {f['name']} site {j}", p) for p in st]
                for r in tt.get("internal_stations", []):
                    out += [(f"istation {r['conn']} reg {j}", p) for j, p in enumerate(r["regs_um"])]
                ck = tt.get("clock") or {}
                out += [(f"tap {x['name']}", x["xy"]) for x in ck.get("taps", [])]
                ct = (ck.get("landing_contract") or {}).get("collector_tree") or {}
                out += [(f"collector relay {x['name']}", x["xy"]) for x in ct.get("relays", [])]
                rs = tt.get("reset") or {}
                if rs.get("tap_um"):
                    out.append(("reset tap", rs["tap_um"]))
                return out

            before = {nm for nm, p in points(t) if any(inside(p, box(h)) for h in cores.values())}
            mv = moves.get(tn, {})
            for inst, org in mv.items():
                h = cores.get(inst)
                if h is None:
                    raise SplitError(f"core_moves: {tn} has no hard core {inst}")
                old = list(h["origin_um"])
                d = [rnd(org[0] - old[0]), rnd(org[1] - old[1])]
                for v in org:
                    if abs(v / grid - round(v / grid)) > 1e-6:
                        raise SplitError(f"core_moves: {tn} {inst} origin {org} is not on the {grid:g}-um lattice")
                # pins keep their tracks: the shift is a whole pitch on every layer the core has pins on (V -> x)
                try:
                    from check import core_pins
                    layers = {ln for _, ln, _, _ in core_pins(h, self.plan_dir)}
                except Exception as e:  # noqa: BLE001  (fail closed below if we cannot prove the pins)
                    raise SplitError(f"core_moves: {tn} {inst}: cannot read the core pins ({e})")
                for ln in sorted(layers):
                    L = P.layers.get(ln)
                    if L is None or ln == "M1":
                        continue
                    sh = d[0] if L["dir"] == "V" else d[1]
                    k = sh / L["pitch_um"]
                    if abs(k - round(k)) > 1e-4:
                        raise SplitError(f"core_moves: {tn} {inst}: shift {d} moves the {ln} pins off track "
                                         f"(pitch {L['pitch_um']:g})")
                h["origin_um"] = [rnd(org[0]), rnd(org[1])]
                b = box(h)
                if b[0] < -EPS or b[1] < -EPS or b[2] > W + EPS or b[3] > H + EPS:
                    raise SplitError(f"core_moves: {tn} {inst} box {b} leaves the outline")
                for o in cores.values():
                    if o is not h:
                        ob = box(o)
                        if b[0] < ob[2] - EPS and ob[0] < b[2] - EPS and b[1] < ob[3] - EPS and ob[1] < b[3] - EPS:
                            raise SplitError(f"core_moves: {tn} {inst} box overlaps core {o['inst']}")
                ntap = 0
                for tp in (t.get("clock") or {}).get("taps", []):
                    if tp["name"].startswith(inst + "."):
                        tp["xy"] = [rnd(tp["xy"][0] + d[0]), rnd(tp["xy"][1] + d[1])]
                        ntap += 1
                h["note"] = (h.get("note", "") + f" | {self.tag}: moved {old} -> {h['origin_um']} (no re-shape)")
                rec.append(dict(type=tn, core=inst, old=old, new=h["origin_um"], shift=d, taps_moved=ntap,
                                pin_layers=sorted(layers)))
            slots = {f["name"]: f for f in t.get("ft_slots", [])}
            for sn, regs in (smoves.get(tn) or {}).items():
                f = slots.get(sn)
                if f is None:
                    raise SplitError(f"station_moves: {tn} has no ft slot {sn}")
                for j, dd in regs.items():
                    j = int(j)
                    old = list(f["regs_um"][j])
                    f["regs_um"][j] = [rnd(old[0] + dd[0]), rnd(old[1] + dd[1])]
                    if j >= 1 and f.get("bit_sites_um"):
                        f["bit_sites_um"][j - 1] = [[rnd(p[0] + dd[0]), rnd(p[1] + dd[1])] for p in f["bit_sites_um"][j - 1]]
                    for k in (j - 1, j + 1):
                        if 0 <= k < len(f["regs_um"]):
                            a, c = f["regs_um"][k], f["regs_um"][j]
                            hop = abs(a[0] - c[0]) + abs(a[1] - c[1])
                            if hop > reach + EPS:
                                raise SplitError(f"station_moves: {tn} {sn} reg {j} -> {k} hop {hop:.1f} > {reach:g}")
                    rec.append(dict(type=tn, slot=sn, reg=j, old=old, new=f["regs_um"][j], shift=dd))
            after = {nm for nm, p in points(t) if any(inside(p, box(h)) for h in cores.values())}
            new = sorted(after - before)
            if new:
                raise SplitError(f"core_moves: {tn}: {len(new)} plan points newly inside a core box: {new[:6]}")
        self.rep["core_moves"] = rec

    # ---------------------------------------------------------------- helpers
    def piece_origin(self, ts, p, i):
        o = p.get("orient", "R0")
        ox, oy = map(float, p["origin_um"])
        cut = ts.cut
        flip = o in (("MX", "R180") if cut.ax == 1 else ("MY", "R180"))
        org = [ox, oy]
        org[cut.ax] = rnd((org[cut.ax] + cut.L - cut.hi(i)) if flip else (org[cut.ax] + cut.lo(i)))
        return org

    def die_along(self, ts, p, i, v):
        """type-frame (piece frame) coordinate along the cut face -> die coordinate (x for a y cut)"""
        o = p.get("orient", "R0")
        org = float(p["origin_um"][1 - ts.cut.ax])
        flip = o in (("MY", "R180") if ts.cut.ax == 1 else ("MX", "R180"))
        L = ts.W if ts.cut.ax == 1 else ts.H
        return rnd(org + (L - v if flip else v)), flip

    def cut_face(self, ts, p, a, b):
        """die face of piece a toward piece b"""
        lf = ts.cut.high_face() if b > a else ts.cut.low_face()
        return die_face(p.get("orient", "R0"), lf)

    # ---------------------------------------------------------------- run
    def run(self):
        raw = copy.deepcopy(self.raw)
        self.out = raw
        spec = self.spec
        T = {}
        for tn, ts in self.ts.items():
            T[tn] = ts.split()
            self.rep["types"][tn] = ts.rep
        # piece sink bins: written now (the reset / tap models read them during the run) under the output folder,
        # absolute for the run; write() turns the path into the plan-relative one
        self.sink_abs = {}
        od = getattr(self, "out_dir", None)
        for tn, ts in self.ts.items():
            for i, t in enumerate(ts.T):
                ck = t.get("clock") or {}
                if ck.get("sink_bins_file") == ("__PIECE__", i):
                    if od is None:
                        raise SplitError(f"{ts.tnames[i]}: piece sink bins need the output folder before the run")
                    (Path(od) / "sink_bins").mkdir(parents=True, exist_ok=True)
                    f = Path(od) / "sink_bins" / f"{ts.tnames[i]}.json"
                    jdump(ts.sink_bins[i], f)
                    ck["sink_bins_file"] = str(f)
                    self.sink_abs[ts.tnames[i]] = str(f)
        # plan cells first: they add cut buses to the pieces
        self.pc_out = self._plan_cells(T) if self.ab else None
        # ---- partitions + types
        self.pmap = {}             # base partition -> [piece partitions]
        self.ppart = {}            # piece partition -> (base partition, piece index, type split)
        parts = []
        for p in raw["partitions"]:
            ts = self.ts.get(p["type"])
            if ts is None:
                parts.append(p)
                continue
            names = ts.pname[p["name"]]
            self.pmap[p["name"]] = names
            for i in range(ts.n):
                q = copy.deepcopy(p)
                q["name"], q["type"] = names[i], ts.tnames[i]
                q["origin_um"] = self.piece_origin(ts, p, i)
                parts.append(q)
                self.ppart[names[i]] = (p["name"], i, ts)
        raw["partitions"] = parts
        types = {}
        for tn, t in raw["partition_types"].items():
            if tn in self.ts:
                for i, nm in enumerate(self.ts[tn].tnames):
                    types[nm] = T[tn][i]
            else:
                types[tn] = t
        raw["partition_types"] = types
        self.T = T
        # ---- port ends
        ports = {pr["id"]: pr for pr in raw["ports"]}
        self.ports = ports
        moved = 0
        for pr in raw["ports"]:
            for e in ("src", "dst"):
                part = pr[e]["part"]
                if part in self.pmap:
                    ts = self.ts[self.raw_type(part)]
                    i = ts.bp(pr[e]["bus"])
                    pr[e]["part"] = self.pmap[part][i]
                    moved += i != ts.keep
        self.rep["port_ends_moved"] = moved
        # ---- cut crossings (collected first, windows per (partition, cut), then built)
        self.req = []
        self.lmax = _lane_num(raw)
        self._ft_cut_requests()
        self._leg_requests()
        self._census_requests()
        self._plancell_requests()
        self._build_cut_ports()
        # ---- the rest of the plan
        self._landing_network()
        self._reset_budgets()
        self._collector_children()
        self._latency()
        self._sidecar()
        self._straps()
        self._tap_repair()
        self._reset_trees()
        self._asbuilt()
        return raw

    def raw_type(self, part):
        return next(p["type"] for p in self.raw["partitions"] if p["name"] == part)

    # ---------------------------------------------------------------- crossing requests
    def _req(self, **k):
        k.setdefault("epoch", None)
        self.req.append(k)
        return k

    def _ft_cut_requests(self):
        """every lane through a crossing ft slot gets one port per cut the slot crosses"""
        raw = self.out
        for tn, ts in self.ts.items():
            for f in ts.ft_cut:
                for base, names in self.pmap.items():
                    if self.raw_type(base) != tn:
                        continue
                    pcs = f["pieces"]
                    for ln in raw["lanes"]:
                        ps = ln["ports"]
                        for k, q in enumerate(ps):
                            pr = self.ports[q]
                            if not (pr["dst"]["part"] in names and pr["dst"]["bus"] == f["slot"] + "_i"):
                                continue
                            nxt = self.ports[ps[k + 1]] if k + 1 < len(ps) else None
                            if nxt is None or nxt["src"]["bus"] != f["slot"] + "_o" or nxt["src"]["part"] not in names:
                                raise SplitError(f"lane {ln['id']}: {base}.{f['slot']}_i not followed by its _o")
                            ins = []
                            for j in range(len(pcs) - 1):
                                a, b = pcs[j]["piece"], pcs[j + 1]["piece"]
                                p = next(x for x in self.raw["partitions"] if x["name"] == base)
                                ins.append(self._req(kind_="ft", base=base, ts=ts, a=a, b=b, sbus=f["slot"] + "_o",
                                                     dbus=f["slot"] + "_i", width=int(pr["width"]),
                                                     kind=pr.get("kind", "data"), epoch=pr.get("epoch"),
                                                     xpref=pcs[j + 1]["xc"], key=f"ft:{f['slot']}:{ln['id']}:{j}",
                                                     slot=f["slot"],
                                                     lane=ln["id"], after=q, pid=f"{q}c{j}" if j else f"{q}c"))
                            break

    def _leg_requests(self):
        for tn, ts in self.ts.items():
            for leg in ts.legs:
                if len(leg["cuts"]) == 0:
                    continue
                for base in self.pmap:
                    if self.raw_type(base) != tn:
                        continue
                    for j, c in enumerate(leg["cuts"]):
                        self.lmax += 1
                        lid = f"L{self.lmax}"
                        self._req(kind_="leg", base=base, ts=ts, a=c["a"], b=c["b"], sbus=c["oname"], dbus=c["iname"],
                                  width=leg["width"], kind=leg["kind"], xpref=c["x"], key=f"leg:{c['a']}:{c['b']}:{c['oname']}",
                                  lane=lid, new_lane=True, pid=f"{lid}_0",
                                  note=f"{self.tag}: cut leg of {leg['conn']} piece {c['a']} -> {c['b']}"
                                       + (" (one station folded into the cut boundary)" if c["folded"] else ""))

    def _cut_bus_pair(self, ts, a, b, stem, width, kind):
        on = ts._new_bus_name(a, "o_" + stem)
        ts.new_bus[a].append(dict(name=on, dir="out", width=width, kind=kind))
        ts.T[a]["buses"].append(dict(name=on, dir="out", width=width, kind=kind))
        inn = ts._new_bus_name(b, "i_" + stem)
        ts.T[b]["buses"].append(dict(name=inn, dir="in", width=width, kind=kind))
        ts.bus_piece[on], ts.bus_piece[inn] = a, b
        return on, inn

    def _mid_slot(self, ts, piece, frm, to, width):
        """a new pass-through ft slot of `piece` from the face toward `frm` to the face toward `to`"""
        t = ts.T[piece]
        have = {f["name"] for x in ts.T for f in x.get("ft_slots", [])} | \
               {f["name"] for f in ts.t.get("ft_slots", [])}
        k = 0
        while f"ft{k}" in have:
            k += 1
        nm = f"ft{k}"
        lo_f, hi_f = ts.cut.low_face(), ts.cut.high_face()
        f = dict(name=nm, in_face=lo_f if frm < piece else hi_f, out_face=hi_f if to > piece else lo_f,
                 width=int(width), stations=1, regs_um=[], note=f"{self.tag}: pass-through slot piece {frm} -> {to}")
        t.setdefault("ft_slots", []).append(f)
        ts.bus_piece[nm + "_i"] = ts.bus_piece[nm + "_o"] = piece
        return f

    def _transit(self, base, ts, frm, to, stem, width, kind, how, pc=None):
        """a cut route from piece frm to piece to: one lane, through pass-through slots of the pieces between"""
        self.lmax += 1
        lid = f"L{self.lmax}"
        step = 1 if to > frm else -1
        path = list(range(frm, to + step, step))
        hops = []
        for a, b in zip(path, path[1:]):
            hops.append((a, b))
        sb = ts._new_bus_name(frm, "o_" + stem)
        ts.T[frm]["buses"].append(dict(name=sb, dir="out", width=width, kind=kind))
        db = ts._new_bus_name(to, "i_" + stem)
        ts.T[to]["buses"].append(dict(name=db, dir="in", width=width, kind=kind))
        ts.bus_piece[sb], ts.bus_piece[db] = frm, to
        slots = {}
        for m in path[1:-1]:
            slots[m] = self._mid_slot(ts, m, frm, to, width)
        for k, (a, b) in enumerate(hops):
            s = sb if a == frm else slots[a]["name"] + "_o"
            d = db if b == to else slots[b]["name"] + "_i"
            self._req(kind_="transit", base=base, ts=ts, a=a, b=b, sbus=s, dbus=d, width=width, kind=kind, xpref=None,
                      key=f"tr:{lid}:{k}", lane=lid, new_lane=k == 0, hop=k, pid=f"{lid}_{k}", slot_b=slots.get(b),
                      slot_a=slots.get(a), note=f"{self.tag}: cut route {how} piece {frm} -> {to}", plancell=pc)
        return sb, db, lid

    def _census_requests(self):
        """bits the base bind carried across what is now a cut and no crossing leg carries: one cut route each"""
        self.rep["census_routes"] = []
        if not self.census:
            return
        for tn, ts in self.ts.items():
            legs = defaultdict(list)
            for leg in ts.legs:
                if leg["cuts"] or leg.get("dead_cuts"):
                    # a row with dead cuts still covers its whole span: the bind carries its census bits on the
                    # crossing lanes it already uses (no new cut route for them)
                    bus = leg["conn"][4:]
                    legs[bus].append(tuple(leg["span"]) if leg.get("dead_cuts") else
                                     (leg["pieces"][0]["piece"], leg["pieces"][-1]["piece"]))
            for base in self.pmap:
                if self.raw_type(base) != tn:
                    continue
                for r in self.census.get("transit", []):
                    if r["hub"] != base:
                        continue
                    frm, to = int(r["frm"]), int(r["to"])
                    if (frm, to) in legs.get(r["bus"], []):
                        continue
                    stem = re.sub(r"^[oi]_", "", r["bus"])
                    sb, db, lid = self._transit(base, ts, frm, to, stem, int(r["bits"]), "data", f"{r['how']} {r['bus']}")
                    self.rep["census_routes"].append(dict(part=base, bus=r["bus"], how=r["how"], frm=frm, to=to,
                                                          bits=r["bits"], lane=lid, src_bus=sb, dst_bus=db))
                pin_rows = self.census.get("intra_pin_routes")
                intra_rows = ([r["hub"], r["src"], r["dst"], r["frm"], r["to"], r["bits"], r["port"]]
                              for r in pin_rows) if pin_rows is not None else (list(r) + [None] for r in self.census.get("intra", []))
                for h, sc, kc, frm, to, n, pin in intra_rows:
                    if h != base:
                        continue
                    stem = re.sub(r"_\d+__", "_N__", sc) + ("_" + pin if pin else "")
                    sb, db, lid = self._transit(base, ts, int(frm), int(to), stem, int(n), "data", f"leaf {sc} -> {kc}")
                    self.rep["census_routes"].append(dict(part=base, src=sc, dst=kc, frm=frm, to=to, bits=n, lane=lid,
                                                          src_bus=sb, dst_bus=db))

    def _plancell_requests(self):
        for (base, ts, frm, to, stem, width, kind, tag, cb) in getattr(self, "pc_routes", []):
            sb, db, lid = self._transit(base, ts, frm, to, stem, width, kind, tag, pc=True)
            cb(sb, db)

    # ---------------------------------------------------------------- windows + ports + lanes
    def _ft_station_on_window(self, ts, r):
        """the kit places a slot's station 0 at its in-window pin (face_flops.tcl): move the new in-face cut station
        of the crossing slot onto the allocated window centre, then re-check both hops at reach (fail closed)"""
        g, prev, nxt = ts.ft_in[(r["slot"], r["b"])]
        cut, b = ts.cut, r["b"]
        x = rnd(round(r["x_local"] / G) * G, 3)
        old = g["regs_um"][0][1 - cut.ax]
        xs = self.__dict__.setdefault("ft_xset", {})
        k = (ts.tn, r["slot"], b)
        if k in xs and abs(xs[k] - x) > 1e-6:
            raise SplitError(f"{ts.tn}.{r['slot']}: two instances put the piece {b} cut station at {xs[k]} and {x}")
        xs[k] = x
        g["regs_um"][0][1 - cut.ax] = x
        st = list(g["regs_um"][0])
        st_t = cut.unsh(st, b)                 # type frame
        reach = float(self.raw.get("budgets", {}).get("ft_station_max_um", 405.0))
        h1 = abs(prev[0] - st_t[0]) + abs(prev[1] - st_t[1])
        h2 = abs(nxt[0] - st_t[0]) + abs(nxt[1] - st_t[1])
        if max(h1, h2) > reach + 1e-6:
            raise SplitError(f"{ts.tn}.{r['slot']}: cut station on its window x {x} gives hops {h1:.0f}/{h2:.0f} um > "
                             f"reach {reach:.0f}")
        if abs(old - x) > 1e-6:
            self.rep.setdefault("cut_stations_on_window", []).append(
                dict(type=ts.tn, slot=r["slot"], piece=b, x_from=old, x_to=x, hops=[rnd(h1, 1), rnd(h2, 1)]))

    def _build_cut_ports(self):
        raw = self.out
        import schema as S
        cpu = self.spec.get("cut_pins_per_um", 8.0)
        layers = AXIS_LAYERS[self.spec["axis"]]
        groups = defaultdict(list)
        for r in self.req:
            j = min(r["a"], r["b"])               # cut j is between pieces j and j + 1
            groups[(r["base"], j)].append(r)
        self.windows = {}
        for (base, j), rs in sorted(groups.items()):
            ts = rs[0]["ts"]
            # "type": the type's own (G2-proven) face budget, capped at schema.FACE_PINS_HARD_CAP; else the die budget
            per_um = float(cpu) if cpu != "type" else min(
                float(ts.t.get("face_pins_per_um") or self.raw["budgets"]["face_pins_per_um"]), S.FACE_PINS_HARD_CAP)
            p = next(x for x in self.raw["partitions"] if x["name"] == base)
            items = []
            # infrastructure pins (collector / relay) sit on the cut face around infra_x: keep that span clear
            items.append(("infra", int(per_um * 17.28), ts.infra_x - 4.32 + 8.64))
            reach = float(self.raw.get("budgets", {}).get("ft_station_max_um", 405.0)) - 2.16
            for r in rs:
                pins = int(r["width"]) + (0 if r.get("epoch") is False else 1)
                rng = None
                if r["kind_"] == "ft":
                    g, prev, nxt = ts.ft_in[(r["slot"], r["b"])]
                    ax = ts.cut.ax
                    cpos = ts.cut.unsh(g["regs_um"][0], r["b"])[ax]
                    d1, d2 = abs(prev[ax] - cpos), abs(nxt[ax] - cpos)
                    o = 1 - ax
                    rng = (max(prev[o] - (reach - d1), nxt[o] - (reach - d2)),
                           min(prev[o] + (reach - d1), nxt[o] + (reach - d2)))
                    if rng[0] > rng[1]:
                        raise SplitError(f"{ts.tn}.{r['slot']}: no cut-station site within reach of both neighbours")
                items.append((r["key"], pins, r["xpref"], rng))
            L = ts.W if ts.cut.ax == 1 else ts.H
            try:
                win = windows_for(items, L, per_um)
            except SplitError as e:
                dem = sum(i[1] for i in items)
                raise SplitError(f"{base} cut {j}: {e} (demand {dem} pins on a {L:.1f} um face at {per_um}/um = "
                                 f"{dem / per_um:.0f} um; {len(items)} items)") from None
            self.windows[f"{base}:{j}"] = {k: v for k, v in win.items()}
            for r in rs:
                segs = win[r["key"]]
                a, b = r["a"], r["b"]
                names = self.pmap[base]
                dws = []
                for lo, hi, n in segs:
                    d0, flip = self.die_along(ts, p, a, lo)
                    d1, _ = self.die_along(ts, p, a, hi)
                    dws.append((min(d0, d1), max(d0, d1), n))
                pr = dict(id=r["pid"], src=dict(part=names[a], bus=r["sbus"]), dst=dict(part=names[b], bus=r["dbus"]),
                          width=int(r["width"]), kind=r["kind"], face=self.cut_face(ts, p, a, b), layers=list(layers),
                          window_um=[min(x[0] for x in dws), max(x[1] for x in dws)],
                          order="lsb_high" if flip else "lsb_low")
                if r.get("epoch") is not None:
                    pr["epoch"] = r["epoch"]
                if len(segs) > 1:
                    import schema as S
                    extra = S.port_pins_count(pr) - sum(x[2] for x in dws)
                    pr["segments"] = [dict(pins=x[2] + (extra if k == len(dws) - 1 else 0), window_um=[x[0], x[1]])
                                      for k, x in enumerate(sorted(dws))]
                pr["note"] = r.get("note", f"{self.tag}: cut face {a} -> {b}")
                raw["ports"].append(pr)
                self.ports[pr["id"]] = pr
                self.rep["ports_added"].append(pr["id"])
                r["x_local"] = (segs[0][0] + segs[-1][1]) / 2
                if r["kind_"] == "ft":
                    self._ft_station_on_window(ts, r)
                # station sites of new pass-through slots: the in-face station sits on its window
                for sl, side in ((r.get("slot_b"), "in"), (r.get("slot_a"), "out")):
                    if sl is None:
                        continue
                    sl.setdefault("_x", {})[side] = r["x_local"]
        # lanes
        lanes = {l["id"]: l for l in raw["lanes"]}
        bylane = defaultdict(list)
        for r in self.req:
            bylane[r["lane"]].append(r)
        for lid, rs in bylane.items():
            if lid in lanes:
                for r in rs:          # ft cut: insert after its in port (in order of the cuts)
                    ps = lanes[lid]["ports"]
                    k = ps.index(r["after"])
                    while k + 1 < len(ps) and ps[k + 1].startswith(r["after"] + "c"):
                        k += 1
                    ps.insert(k + 1, r["pid"])
                self.rep["lanes_changed"].setdefault(lid, {})["ft_cut_ports"] = [r["pid"] for r in rs]
            else:
                rs = sorted(rs, key=lambda r: r.get("hop", 0))
                ln = dict(id=lid, ports=[r["pid"] for r in rs], note=rs[0]["note"])
                raw["lanes"].append(ln)
                lanes[lid] = ln
                self.rep["lanes_added"].append(lid)
        # pass-through slot geometry
        reach = float(self.raw.get("budgets", {}).get("ft_station_max_um", 405.0))
        for ts in self.ts.values():
            for i, t in enumerate(ts.T):
                for f in t.get("ft_slots", []):
                    if "_x" not in f:
                        continue
                    xi, xo = f["_x"]["in"], f["_x"]["out"]
                    ext = ts.cut.ext(i)
                    y_in = 0.0 if f["in_face"] == ts.cut.low_face() else ext
                    y_out = ext - y_in
                    st = [[xi, y_in]] if ts.cut.ax == 1 else [[y_in, xi]]
                    span = abs(y_out - y_in) + abs(xo - xi)
                    n_more = max(0, math.ceil(span / (reach - 8.64)) - 1)
                    for k in range(1, n_more + 1):
                        fr = k / (n_more + 1)
                        pt = [rnd(xi + (xo - xi) * fr), rnd(y_in + (y_out - y_in) * fr)]
                        st.append(pt if ts.cut.ax == 1 else pt[::-1])
                    f["regs_um"] = [[rnd(a), rnd(b)] for a, b in st]
                    f["stations"] = len(st)
                    del f["_x"]

    # ---------------------------------------------------------------- plan cells
    def _plan_cells(self, T):
        """split asbuilt.plan_cells per piece.  Returns the new document; cut routes for cell drivers are queued."""
        src = self.ab.get("plan_cells")
        if not src:
            return None
        path = rpath(src)
        doc = json.loads(path.read_text())
        self.pc_path = path
        self.pc_routes = []
        out = copy.deepcopy(doc)
        TT = out["types"]
        self.rep["plan_cells"] = {}
        for tn, ts in self.ts.items():
            if tn not in TT:
                continue
            base_parts = [b for b in self.ts_parts(tn)]
            if len(base_parts) != 1:
                raise SplitError(f"{tn}: plan-cell split handles one partition per type ({base_parts})")
            base = base_parts[0]
            d = TT.pop(tn)
            if d.get("leaf_binds") or d.get("rewired"):
                raise SplitError(f"{tn}: plan cells with leaf_binds / rewired are not handled")
            new = [dict(bus_drivers=[], cells={}, leaf_binds=[], rewired=[], replicas=[]) for _ in range(ts.n)]
            for i in range(ts.n):
                # replicas: partitions sharing these cells; a replica of a split family type takes its own piece name
                allp = {b: nm for t2 in self.ts.values() for b, nm in t2.pname.items()}
                new[i]["replicas"] = [allp[r][i] if r in allp else r for r in d.get("replicas", [])]
            rec = dict(cells={}, bus_drivers={})

            def leaf_piece(inst):
                cores = {h["inst"]: h for h in ts.t.get("hard_cores", [])}
                if inst in cores:
                    return ts.core_piece(cores[inst])
                if inst in ts.content_piece:
                    return ts.content_piece[inst]
                rules = [(re.compile(rx), int(i)) for rx, i in self.spec.get("contents", {}).get(tn, [])]
                v = next((i for rx, i in rules if rx.fullmatch(inst)), None)
                if v is None:
                    raise SplitError(f"{tn}: plan-cell driver leaf {inst} has no piece")
                return v

            def route(frm, to, stem, width, kind, on_done):
                self.pc_routes.append((base, ts, frm, to, stem, width, kind, f"plan cell {stem}", on_done))

            self._efault_rewire = []
            for inst, c in d["cells"].items():
                if c["module"] == "ot_dp_efault":
                    self._split_efault(ts, base, inst, c, new, rec, route, d["cells"])
                    continue
                if (tn, inst) in getattr(self, "_efault_done", set()):
                    continue                        # an efault consumer, placed with its efault
                refs = {ts.bp(e["bus"]) for es in c["conns"].values() for e in es if "bus" in e} | \
                       {ts.bp(e["epoch"]) for es in c["conns"].values() for e in es if "epoch" in e} | \
                       {leaf_piece(e["inst"]) for es in c["conns"].values() for e in es if "inst" in e}
                if len(refs) != 1:
                    raise SplitError(f"{tn}: plan cell {inst} spans pieces {sorted(refs)}")
                i = refs.pop()
                new[i]["cells"][inst] = copy.deepcopy(c)
                rec["cells"][inst] = i
            for pf, inst, last in self._efault_rewire:
                # the fault consumer cell (in the fault piece) reads the end of the OR chain instead of the efault
                for nm, cc in new[pf]["cells"].items():
                    if nm == inst or nm.startswith(inst + "_or"):
                        continue
                    for es in cc["conns"].values():
                        for e in es:
                            if e.get("cell") == inst and e.get("port") == "fault":
                                e["cell"], e["port"] = last, "q"
            for bd in d.get("bus_drivers", []):
                pb = ts.bp(bd["bus"])
                drv_p = set()
                for e in bd["drivers"]:
                    if "inst" in e:
                        drv_p.add(leaf_piece(e["inst"]))
                    elif "bus" in e:
                        drv_p.add(ts.bp(e["bus"]))
                    elif "cell" in e:
                        drv_p.add(rec["cells"].get(e["cell"], ts.keep))
                if len(drv_p) != 1:
                    raise SplitError(f"{tn}: bus driver {bd['bus']} reads pieces {sorted(drv_p)}")
                pd = drv_p.pop()
                if pd == pb:
                    new[pb]["bus_drivers"].append(copy.deepcopy(bd))
                    rec["bus_drivers"][bd["bus"]] = pb
                    continue
                w = sum(int(e["bits"][1]) - int(e["bits"][0]) + 1 if "bits" in e else 1 for e in bd["drivers"])

                def done(sb, db, bd=bd, pd=pd, pb=pb, w=w, new=new):
                    new[pd]["bus_drivers"].append(dict(bus=sb, drivers=copy.deepcopy(bd["drivers"])))
                    new[pb]["bus_drivers"].append(dict(bus=bd["bus"], drivers=[dict(bus=db, bits=[0, w - 1])]))
                route(pd, pb, re.sub(r"^o_", "", bd["bus"]), w, "data", done)
                rec["bus_drivers"][bd["bus"]] = [pd, pb]
            for i in range(ts.n):
                TT[ts.tnames[i]] = new[i]
            self.rep["plan_cells"][tn] = rec
        return out

    def ts_parts(self, tn):
        return [p["name"] for p in self.raw["partitions"] if p["type"] == tn]

    def _split_efault(self, ts, base, inst, c, new, rec, route, cells=None):
        """ot_dp_efault over the in-bus epochs: one cell per piece over its own buses; the faults of the pieces without
        the fault bus ride cut routes to it and are ORed there (qkd_hp_or2, registered).  A fault that feeds a plan
        cell (no fault conn: e.g. u_fch.a) goes to that cell's piece; the cell then reads the OR chain end."""
        eqs = defaultdict(list)
        for e in c["conns"]["eq"]:
            eqs[ts.bp(e["epoch"])].append(e)
        fb = c["conns"].get("fault")
        consumer = None
        if fb is None:
            cons = [(nm, cc) for nm, cc in (cells or {}).items() if any(
                e.get("cell") == inst and e.get("port") == "fault" for es in cc["conns"].values() for e in es)]
            if len(cons) != 1:
                raise SplitError(f"{ts.tn}: efault {inst} has no fault bus and {len(cons)} consumer cells")
            consumer = cons[0][0]
            bdir = {b["name"]: b["dir"] for b in ts.t["buses"]}
            outs = {ts.bp(e["bus"]) for es in cons[0][1]["conns"].values() for e in es
                    if "bus" in e and bdir.get(e["bus"]) == "out"}
            if len(outs) != 1:
                raise SplitError(f"{ts.tn}: efault {inst} consumer {consumer} drives pieces {sorted(outs)}")
            pf = outs.pop()
            # the consumer sits in its output bus's piece; an input bus of another piece rides a cut route to it
            cc = copy.deepcopy(cons[0][1])
            new[pf]["cells"][consumer] = cc
            rec["cells"][consumer] = pf
            self._efault_done = getattr(self, "_efault_done", set()) | {(ts.tn, consumer)}
            for es in cc["conns"].values():
                for e in es:
                    if "bus" not in e or bdir.get(e["bus"]) != "in" or ts.bp(e["bus"]) == pf:
                        continue
                    pi = ts.bp(e["bus"])
                    w = int(e["bits"][1]) - int(e["bits"][0]) + 1 if "bits" in e else 1

                    def done_in(sb, db, e=e, pi=pi, w=w, src=dict(e)):
                        new[pi]["bus_drivers"].append(dict(bus=sb, drivers=[copy.deepcopy(src)]))
                        e["bus"], e["bits"] = db, [0, w - 1]
                    route(pi, pf, re.sub(r"^i_", "", e["bus"]), w, "data", done_in)
                    self.rep["notes"].append(f"{ts.tn}: plan cell {consumer} input {e['bus']} piece {pi} -> {pf} "
                                             "(cut route)")
        else:
            if len(fb) != 1 or "bus" not in fb[0]:
                raise SplitError(f"{ts.tn}: efault {inst} fault is not one bus")
            pf = ts.bp(fb[0]["bus"])
        rec["cells"][inst] = dict(pieces=sorted(eqs), fault_piece=pf)
        others = sorted(i for i in eqs if i != pf)
        for i, es in eqs.items():
            cc = copy.deepcopy(c)
            cc["conns"]["eq"] = es
            cc["params"] = dict(cc["params"], N=len(es))
            cc["age_rule"] = c.get("age_rule", "") + f" | {self.tag}: piece {i} of {len(eqs)} (AGE kept: max over a subset)"
            if i != pf:
                cc["conns"]["fault"] = []           # set by the cut route (done)
            elif consumer is not None:
                cc["conns"].pop("fault", None)
            new[i]["cells"][inst] = cc
        if pf not in eqs:
            raise SplitError(f"{ts.tn}: efault fault bus piece {pf} has no in bus (not handled)")
        prev = dict(cell=inst, port="fault", bits=[0, 0])
        if not others:
            return
        # the OR chain in the fault piece: or_k = qkd_hp_or2(a = previous, b = piece fault k)
        if consumer is None:
            new[pf]["cells"][inst]["conns"]["fault"] = []      # the efault output feeds the first OR (cell ref)
        chain = []
        for k, i in enumerate(others, 1):
            nm = f"{inst}_or{k}"
            chain.append(nm)
            new[pf]["cells"][nm] = dict(module="qkd_hp_or2", params={}, conns=dict(
                ck=[dict(net="clk")], a=[copy.deepcopy(prev)], b=[], q=[]))
            prev = dict(cell=nm, port="q", bits=[0, 0])

            def done(sb, db, i=i, nm=nm):
                new[i]["cells"][inst]["conns"]["fault"] = [dict(bus=sb, bits=[0, 0])]
                new[pf]["cells"][nm]["conns"]["b"] = [dict(bus=db, bits=[0, 0])]
            stem = re.sub(r"^o_", "", fb[0]["bus"]) if fb else f"{inst.removeprefix('u_')}_fault"
            route(i, pf, stem, 1, "data", done)
        if consumer is None:
            new[pf]["cells"][chain[-1]]["conns"]["q"] = copy.deepcopy(fb)
        else:
            new[pf]["cells"][chain[-1]]["conns"].pop("q")
            self._efault_rewire.append((pf, inst, chain[-1]))
            rec["cells"][inst]["consumer"] = consumer
        rec["cells"][inst]["or_chain"] = chain
        self.rep["notes"].append(f"{ts.tn}: {inst} split into {len(eqs)} pieces; fault OR chain {chain} in piece {pf} "
                                 f"(+{len(chain)} registered fault cycles)")

    # ---------------------------------------------------------------- landing network
    def _piece_of_pin(self, base, name):
        ts = self.ts[self.raw_type(base)]
        m = LAND_PIN.match(name)
        if name in START_PINS or name.startswith(("cland_up_", "fclk_out_cland_up")):
            return ts.keep, name
        cm = re.match(r"^(cland_dn_ready_|cland_dn_fault_|fclk_in_cland_dn_)(\d+)$", name)
        if cm:
            s, k = ts.child_map[int(cm.group(2))]
            return s, f"{cm.group(1)}{k}"
        if m:
            return ts.bp(m.group(2)), name
        raise SplitError(f"{base}: landing network pin {name} has no piece")

    def _landing_network(self):
        net = self.out["clock"].get("landing_network")
        if not net:
            return
        n = 0
        for e in net.get("edges", []):
            for side in ("src", "dst"):
                part = e[side]["part"]
                if part in self.pmap:
                    s, nm = self._piece_of_pin(part, e[side]["bus"])
                    e[side]["part"], e[side]["bus"] = self.pmap[part][s], nm
                    n += 1
        st = net.get("start_tree") or {}
        for u in st.get("uses", []):
            if u["part"] in self.pmap:
                ts = self.ts[self.raw_type(u["part"])]
                u["part"] = self.pmap[u["part"]][ts.keep]
        for o in st.get("open", []):
            if o.get("part") in self.pmap:
                raise SplitError(f"start tree open pin on a split partition {o}")
        add = []
        for base, names in self.pmap.items():
            ts = self.ts[self.raw_type(base)]
            keep = names[ts.keep]
            for c in ts.coll_links:
                ch = names[c["child_piece"]]
                for w in ("ready", "fault"):
                    add.append(dict(id=f"cland_mon_{w}__{ch}", src=dict(part=ch, bus=f"cland_up_{w}"),
                                    dst=dict(part=names[c["parent_piece"]], bus=f"cland_dn_{w}_{c['index']}"),
                                    kind="ctl", width=1,
                                    epoch=False, max_hop_um=405, source_registered=True, capture_registered=True))
                add.append(dict(id=f"cland_relay__{ch}", src=dict(part=keep, bus="cland_rstart_out"),
                                dst=dict(part=ch, bus="cland_rstart_in"), kind="ctl", width=1, epoch=False,
                                max_hop_um=405, source_registered=True, capture_registered=True))
        net["edges"] += add
        self.rep["landing_edges"] = dict(moved_ends=n, added=[e["id"] for e in add])

    def _collector_children(self):
        for base, names in self.pmap.items():
            ts = self.ts[self.raw_type(base)]
            for i, t in enumerate(ts.T):
                lc = t.get("clock", {}).get("landing_contract")
                if not lc:
                    continue
                for ch in lc.get("collector_children", []):
                    if "_piece" in ch:
                        ch["part"] = names[ch.pop("_piece")]

    def _reset_budgets(self):
        raw = self.out
        ins = raw["reset"].setdefault("in_sites", {})
        b = raw.setdefault("budgets", {})
        tw = raw["clock"].get("tap_window", {}).get("per_type_ps", {})
        for tn, ts in self.ts.items():
            old = ins.pop(tn, None)
            for i, nm in enumerate(ts.tnames):
                if old is not None and ts.cut.ppiece(old) == i:
                    ins[nm] = ts.cut.sh(old, i)
                else:
                    # a relay piece takes its reset from the keep piece across the shared cut (the collector link)
                    xy = [0.0, 0.0]
                    xy[1 - ts.cut.ax] = rnd(ts.infra_x + 12.96)
                    xy[ts.cut.ax] = rnd(ts.cut.ext(i) - 8.672) if i < ts.keep else 8.672
                    ins[nm] = xy
            if tn in b.get("id_straps_in_type_types", []):
                b["id_straps_in_type_types"] += [x for x in ts.tnames if x != tn]
            if tn in tw:
                for x in ts.tnames:
                    tw[x] = tw[tn]
            ist = (self.ab or {}).get("internal_stations_types")
        for k in ("cland_fit_resize_off_types", "dpl_legalizer_types", "cland_pinslot_dense_types", "cland_pinslot_off_types",
                  "cland_face_home_types"):
            for tn, ts in self.ts.items():
                if tn in b.get(k, []):
                    b[k] += [x for x in ts.tnames if x != tn]

    # ---------------------------------------------------------------- latency
    def _rows(self, raw, tn, bus, d):
        t = raw["partition_types"][tn]
        rows = [r for r in t.get("internal_stations", []) if r.get("conn") == "bus:" + bus]
        if d == "out":
            return max((len(r["regs_um"]) for r in rows), default=0)
        return max((len(r["regs_um"]) for r in rows), default=0)

    def _latency(self):
        import schema as S
        raw, base = self.out, self.raw
        bports = {p["id"]: p for p in base["ports"]}
        btype = {p["name"]: p["type"] for p in base["partitions"]}
        ntype = {p["name"]: p["type"] for p in raw["partitions"]}
        bdir = {}
        for tn, t in raw["partition_types"].items():
            for x in t.get("buses", []):
                bdir[(tn, x["name"])] = x["dir"]
        lanes = {l["id"]: l for l in raw["lanes"]}
        blanes = {l["id"]: l for l in base["lanes"]}
        # fixed cycles = source OUT stations + destination IN stations (native_istations rule): carry the moved ones
        for lid, ln in lanes.items():
            a, z = self.ports[ln["ports"][0]], self.ports[ln["ports"][-1]]
            sp, dp = a["src"]["part"], z["dst"]["part"]
            if sp not in self.ppart and dp not in self.ppart:
                continue
            new = self._rows(raw, ntype[sp], a["src"]["bus"], "out") if sp != "@die" and sp in ntype else 0
            new += self._rows(raw, ntype[dp], z["dst"]["bus"], "in") if dp != "@die" and dp in ntype else 0
            if lid in blanes:
                ba, bz = bports[blanes[lid]["ports"][0]], bports[blanes[lid]["ports"][-1]]
                bsp, bdp = ba["src"]["part"], bz["dst"]["part"]
                old = self._rows(base, btype[bsp], ba["src"]["bus"], "out") if bsp in btype else 0
                old += self._rows(base, btype[bdp], bz["dst"]["bus"], "in") if bdp in btype else 0
                f0 = int(ln.get("fixed_cycles", 0))
                if new != old:
                    if f0 < old:
                        raise SplitError(f"lane {lid}: fixed_cycles {f0} < its station rows {old}")
                    ln["fixed_cycles"] = f0 - old + new
                    ln["note"] = (ln.get("note", "") + f" | {self.tag}: fixed {f0} -> {ln['fixed_cycles']} (internal "
                                  f"stations {old} -> {new}: legs cut at the piece boundary)").lstrip(" |")
                    self.rep["lanes_changed"].setdefault(lid, {})["fixed"] = [f0, ln["fixed_cycles"]]
            elif new:
                ln["fixed_cycles"] = new
        P = S.Plan(json.loads(json.dumps(raw)), None)
        lat = raw["latency"]["lanes"]
        changed = {}
        for lid in lanes:
            d = P.lane_latency(lid)
            old = lat.get(lid)
            ent = dict(d)
            ent["param"] = old.get("param", f"LAT_{lid}") if old else f"LAT_{lid}"
            for k in list(ent):
                if old is not None and k not in old and k not in ("param",):
                    pass
            if old is not None and {k: v for k, v in old.items() if k != "param"} != \
                    {k: v for k, v in ent.items() if k != "param"}:
                changed[lid] = dict(old=old.get("cycles"), new=ent["cycles"])
            lat[lid] = ent
        touched = set(self.rep["lanes_changed"]) | set(self.rep["lanes_added"])
        bad = {l: v for l, v in changed.items() if l not in touched}
        self.rep["latency_changed"] = changed
        if bad:
            raise SplitError(f"latency of {len(bad)} untouched lanes changed: {dict(list(bad.items())[:5])}")
        def defect(lid):
            """BASE-DEFECT station delta of a base lane: its source OUT row + destination IN row corrections"""
            if lid not in blanes:
                return 0
            ba, bz = bports[blanes[lid]["ports"][0]], bports[blanes[lid]["ports"][-1]]
            d = 0
            for e in (ba["src"], bz["dst"]):
                ts = self.ts.get(btype.get(e["part"]))
                if ts is not None and e["bus"] in getattr(ts, "defect", {}):
                    o, n = ts.defect[e["bus"]]
                    d += n - o
            return d
        rows = []
        for lid in sorted(changed, key=lambda x: int(x[1:])):
            c = changed[lid]
            dd = defect(lid)
            rel = f"{self.spec['plan']} md5 {self.rep['base_md5']} {lid} {c['old']} cycles"
            if dd:
                rows.append(dict(id=f"{self.tag}:BASE-DEFECT:{lid}", lane=lid, parameter=lat[lid]["param"],
                                 added_cycles=dd, clock="clk_core (833 ps)", relative_to=rel,
                                 cycles=[c["old"], c["old"] + dd], kind="BASE-DEFECT",
                                 why="internal-station row corrected to its netlist core end (report.base_defect_rows)"))
            rows.append(dict(id=f"{self.tag}:{lid}", lane=lid, parameter=lat[lid]["param"],
                             added_cycles=c["new"] - c["old"] - dd, clock="clk_core (833 ps)",
                             relative_to=rel + (f" + BASE-DEFECT {dd:+d}" if dd else ""),
                             cycles=[c["old"] + dd, c["new"]], kind="SPLIT",
                             why="cut boundary registers / split internal stations"))
        for lid in self.rep["lanes_added"]:
            rows.append(dict(id=f"{self.tag}:{lid}", lane=lid, parameter=lat[lid]["param"], kind="SPLIT",
                             added_cycles=lat[lid]["cycles"], clock="clk_core (833 ps)",
                             relative_to="new cut lane (absent in the base plan): its whole latency is added on the "
                                         "paths it carries", cycles=[0, lat[lid]["cycles"]],
                             why=lanes[lid].get("note", "")))
        self.latency_rows = rows

    # ---------------------------------------------------------------- sidecar
    def _sidecar(self):
        if self.side is None:
            return
        sd = self.side = copy.deepcopy(self.side)
        for r in sd["regions"]:
            for p in list(r["parts"]):
                if p in self.pmap:
                    r["parts"] += [x for x in self.pmap[p] if x != p]
        moved = 0
        relay = {}
        for base, names in self.pmap.items():
            ts = self.ts[self.raw_type(base)]
            for i, nm in enumerate(names):
                if i != ts.keep:
                    relay[nm] = names[ts.keep]
        for r in sd["ports"]:
            pr = self.ports.get(r["port"])
            if pr is None:
                raise SplitError(f"sidecar row {r['port']}: no plan port")
            for k in ("src", "dst"):
                if r[k] != pr[k]["part"]:
                    r[k] = pr[k]["part"]
                    moved += 1
        ca = sd.get("count_aligned")
        kch = []
        if ca:
            from count_align_bind import RELAY_STAGES
            for nm, org in relay.items():
                ca["parts"][nm] = dict(region=ca["parts"][org]["region"], role="relay", src=org, stages=RELAY_STAGES)
            for r in sd["ports"]:
                c = ca["ports"].get(r["port"])
                if c is None:
                    continue
                dk = (-RELAY_STAGES if r["dst"] in relay else 0) + (RELAY_STAGES if r["src"] in relay else 0)
                if dk:
                    k0 = c["K"]
                    c["K"] = k0 + dk
                    kch.append([r["port"], k0, c["K"]])
        self.rep["sidecar"] = dict(rows_renamed=moved, relay_parts=relay, K_changed=len(kch),
                                   K_range=[min((x[2] for x in kch), default=None), max((x[2] for x in kch), default=None)])
        self.rep["K_changes"] = kch
        co = sd.get("collector")
        if co:
            for base, names in self.pmap.items():
                ts = self.ts[self.raw_type(base)]
                keep = names[ts.keep]
                bt = self.raw_type(base)
                row0 = co["types"].pop(bt)
                for i, nm in enumerate(names):
                    t = self.out["partition_types"][ts.tnames[i]]
                    lc = t["clock"]["landing_contract"]
                    row = copy.deepcopy(row0)
                    row["base_type"] = ts.tnames[i]
                    m = row["mask"]
                    m["inputs"] = [b for b in m["inputs"] if ts.bus_piece.get(b) == i]
                    m["outputs"] = [b for b in m["outputs"] if ts.bus_piece.get(b) == i]
                    m["children"] = len(lc.get("collector_children", []))
                    if i != ts.keep:
                        m["up_seam"] = False
                        up = [p["xy_um"] for p in lc["pins"] if p["name"] == "cland_up_ready"]
                        m["up_xy"] = list(up[0])
                        par = next((c["parent_piece"] for c in ts.coll_links if c["child_piece"] == i), ts.keep)
                        row["up_parent"] = names[par]
                    else:
                        m["up_xy"] = ts.cut.sh(m["up_xy"], i)
                    row["reset_entry_um"] = self.out["reset"]["in_sites"][ts.tnames[i]]
                    row["bands"] = copy.deepcopy(lc.get("bands", {}))
                    bg = {}
                    for b, g in row0.get("bus_geometry", {}).items():
                        if ts.bus_piece.get(b) != i:
                            continue
                        g = copy.deepcopy(g)
                        if g["face"] in (("E", "W") if ts.cut.ax == 1 else ("N", "S")):
                            g["window_um"] = [rnd(v - ts.cut.lo(i)) for v in g["window_um"]]
                        bg[b] = g
                    row["bus_geometry"] = bg
                    row["tree"] = None              # filled by _reset_trees
                    row["local_sources"] = []
                    row["children"] = []
                    co["types"][ts.tnames[i]] = row
                    if i != ts.keep:
                        par = next((c["parent_piece"] for c in ts.coll_links if c["child_piece"] == i), ts.keep)
                        co["parts"][nm] = dict(type=ts.tnames[i], parent=names[par], active=True)
                        co.setdefault("base_type_by_part", {})[nm] = ts.tnames[i]
                        bb = co.get("boot_budget", {}).get("local_registered_depths")
                        if isinstance(bb, dict) and base in bb:
                            bb[nm] = bb[base]
                    else:
                        co["parts"][nm]["type"] = ts.tnames[i]
                for e in co["edges"]:
                    if e["dst"] == base:
                        s, k = ts.child_map[int(e["dst_index"])]
                        e["dst"], e["dst_index"] = names[s], k
                for pn, p in co["parts"].items():
                    if p.get("parent") == base and pn not in names:
                        e = next(x for x in co["edges"] if x["src"] == pn)
                        p["parent"] = e["dst"]
                for c in ts.coll_links:
                    ch = names[c["child_piece"]]
                    hop = abs(c["up_xy"][0] - c["dn_xy"][0]) + abs(c["up_xy"][1] - c["dn_xy"][1])
                    co["edges"].append(dict(src=ch, dst=names[c["parent_piece"]], dst_index=c["index"], seam=False,
                                            hop_um=rnd(hop + 5.312, 3),
                                            data_cycles_added=0, boot_transport_extra_cycles=1))
        sd["note_type_split"] = (f"{self.tag}: {', '.join(self.ts)} split into pieces {[ts.tnames for ts in self.ts.values()]}; "
                                 "one landing region per base partition (origin = keep piece, the others count-aligned "
                                 "relays, K of their landed crossings shifted by the relay stages); cut ports are "
                                 "same-region (no landing row)")

    def _straps(self):
        if not self.side or not (self.side.get("count_aligned") or {}).get("strap_form"):
            return
        import count_align_bind as CAB
        st = CAB.strap_ties(self.side["count_aligned"], self.out)
        out = {}
        for tn, ts in self.ts.items():
            for nm in ts.tnames:
                info = st["types"].get(nm)
                if info is None:
                    raise SplitError(f"strap ties: no entry for {nm}")
                t = self.out["partition_types"][nm]
                want = [dict(name=sp, width=w, note="OWNER 12.15a count strap (tied at the parent)")
                        for sp, w in sorted(info["straps"].items())]
                have = t.get("count_straps", [])
                if [(x["name"], x["width"]) for x in have] != [(x["name"], x["width"]) for x in want]:
                    out[nm] = dict(was=len(have), now=len(want))
                if want:
                    t["count_straps"] = want
                elif "count_straps" in t:
                    del t["count_straps"]
        for tn, info in st["types"].items():
            if tn in self.out["partition_types"] and not any(tn in ts.tnames for ts in self.ts.values()):
                have = [(x["name"], int(x["width"])) for x in self.out["partition_types"][tn].get("count_straps", [])]
                if sorted(have) != sorted(info["straps"].items()):
                    self.rep["notes"].append(f"strap ties of untouched type {tn} differ from its count_straps")
        self.rep["count_straps_rederived"] = out

    # ---------------------------------------------------------------- reset trees + collector attach
    def _tap_repair(self):
        """grid+explicit pieces: the inherited clock.added_taps were placed for the whole type's sinks; a piece keeps
        them where they still serve (taps.grid_explicit_taps passes) and gets ADDED light taps where a tap is now over
        tap_max_sinks or reaches past tap_radius_um (x ADDED_TAP_RADIUS_SLACK): one new tap at the weighted centre of
        the sinks it cannot serve (the far ones, or the farther half of an over-full tap), on a legal site (outline
        margin, tap spacing, off the macro halos), appended (clk_t<n>: names of the existing taps never change).
        Types: every piece of this event plus spec tap_repair_types (pieces of an earlier split).  Fails closed on an
        empty inherited tap or no convergence."""
        import schema as S
        import taps as TP
        import reset_tree as RT
        from placement_obstacles import placement_boxes
        want = {nm for ts in self.ts.values() for nm in ts.tnames} | set(self.spec.get("tap_repair_types", []))
        want = sorted(t for t in want if (self.out["partition_types"].get(t, {}).get("clock") or {}).get("tap_mode")
                      == "grid+explicit")
        if not want:
            return
        P = S.Plan(json.loads(json.dumps(self.out)), self.plan_path)
        rep = {}
        for tn in want:
            ck_o = self.out["partition_types"][tn]["clock"]
            ck = P.types[tn]["clock"]
            cap, radius = int(ck.get("tap_max_sinks", 1500)), float(ck.get("tap_radius_um", 200.))
            lim = radius * TP.ADDED_TAP_RADIUS_SLACK
            w, h = P.types[tn]["outline_um"]
            clear = S.TAP_CLEAR_UM
            boxes = list(placement_boxes(P.types[tn], halo=clear).values())
            added = []
            for it in range(60):
                try:
                    TP.grid_explicit_taps(P, tn)
                    break
                except ValueError as e:
                    msg = str(e)
                out = TP.grid_explicit_sites(P, tn)
                n_grid = len(S._grid_taps(P, tn))
                sinks = TP.sink_sites(P, tn) + [(float(r["xy"][0]), float(r["xy"][1]), 1.0)
                                                 for r in RT.for_type(P, tn).get("relays", [])]
                load, far, who = TP.assign(out, sinks, cap, radius, max_distance_um=radius)
                bad = [i for i in range(n_grid, len(out)) if load[i] > cap or far[i] > lim + 1e-6 or load[i] == 0]
                if not bad:
                    raise SplitError(f"{tn}: tap repair: {msg} but no added tap is out of rule")
                i = bad[0]
                if load[i] == 0:
                    raise SplitError(f"{tn}: tap repair: added tap {out[i][0]} is empty ({msg})")
                tx, ty = out[i][1], out[i][2]
                mine = [(abs(sx - tx) + abs(sy - ty), sx, sy, sw) for (sx, sy, sw), k in zip(sinks, who) if k == i]
                if far[i] > lim + 1e-6:
                    grp = [m for m in mine if m[0] > radius]
                else:
                    mine.sort(reverse=True)
                    grp, acc = [], 0.0
                    for m in mine:
                        if acc >= load[i] / 2:
                            break
                        grp.append(m)
                        acc += m[3]
                W = sum(m[3] for m in grp)
                cx, cy = sum(m[1] * m[3] for m in grp) / W, sum(m[2] * m[3] for m in grp) / W
                taken = [(x, y) for _, x, y in out]
                site = None
                for r in range(0, 120):
                    ring = sorted({(dx, dy) for dx in range(-r, r + 1) for dy in (-(r - abs(dx)), r - abs(dx))})
                    for dx, dy in ring:
                        x, y = round(cx + dx * 2.16, 3), round(cy + dy * 2.16, 3)
                        if (clear <= x <= w - clear and clear <= y <= h - clear
                                and not any(abs(x - a) < clear and abs(y - b) < clear for a, b in taken)
                                and not any(a < x < c and b < y < d for a, b, c, d in boxes)):
                            site = [x, y]
                            break
                    if site:
                        break
                if site is None:
                    raise SplitError(f"{tn}: tap repair: no legal site near {cx:.1f},{cy:.1f}")
                nm = f"clk_t{len(out)}"
                for c in (ck, ck_o):
                    c.setdefault("added_taps", []).append(dict(name=nm, xy=site))
                added.append(dict(name=nm, xy=site, for_tap=out[i][0], why=msg.split(": ", 1)[-1]))
                TP._CACHE.clear()
                TP._clear_density_cache()
                P.__dict__.pop("_reset_tree_cache", None)
            else:
                raise SplitError(f"{tn}: tap repair did not converge in 60 added taps")
            if added:
                rep[tn] = added
        # proof on a fresh plan object (no cached trees / taps): every repaired type passes the grid+explicit rule
        TP._CACHE.clear()
        TP._clear_density_cache()
        P2 = S.Plan(json.loads(json.dumps(self.out)), self.plan_path)
        for tn in want:
            try:
                TP.grid_explicit_taps(P2, tn)
            except ValueError as e:
                raise SplitError(f"{tn}: tap repair proof failed: {e}") from None
        self.rep["tap_repair"] = rep

    def _reset_trees(self):
        import schema as S
        import reset_tree as RT
        raw = self.out
        P = S.Plan(json.loads(json.dumps(raw)), self.plan_path)
        Pb = S.Plan(json.loads(json.dumps(self.raw)), self.plan_path)
        reach = float(self.raw.get("budgets", {}).get("ft_station_max_um", 405.0))
        norm = lambda o: json.dumps(o, sort_keys=True)  # noqa: E731
        changed, new_types = [], []
        piece_types = {nm for ts in self.ts.values() for nm in ts.tnames}
        for tn, t in raw["partition_types"].items():
            lc = t.get("clock", {}).get("landing_contract")
            if not lc or lc.get("collector_tree") is None or t.get("hard") or lc["collector_tree"].get("hard"):
                continue
            tree = json.loads(json.dumps(RT.for_type(P, tn)))
            if tn in piece_types:
                lc["collector_tree"] = tree
                self._attach(tn, lc, tree, reach)
                new_types.append(tn)
                continue
            old = json.loads(json.dumps(RT.for_type(Pb, tn)))
            if norm(old) != norm(tree):
                changed.append(tn)
        if changed:
            import collector_reattach as CRA
            for tn in changed:
                t = raw["partition_types"][tn]
                t["clock"]["landing_contract"]["collector_tree"] = json.loads(json.dumps(RT.for_type(P, tn)))
            sub_b = {"partition_types": {tn: self.raw["partition_types"][tn] for tn in changed}}
            sub_n = {"partition_types": {tn: raw["partition_types"][tn] for tn in changed}}
            r = CRA.reattach_plan(sub_b, sub_n, reach)
            if r["over"]:
                raise SplitError(f"collector reattach over reach on untouched types: {r['over']}")
            self.rep["trees_republished_untouched"] = changed
        self.rep["piece_trees"] = {tn: dict(depth=raw["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"]["depth"],
                                            relays=len(raw["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"]["relays"]))
                                   for tn in new_types}
        # sidecar collector rows follow the plan
        if self.side and self.side.get("collector"):
            st = self.side["collector"]["types"]
            for tn in new_types + changed:
                lc = raw["partition_types"][tn]["clock"]["landing_contract"]
                if tn not in st:
                    continue
                st[tn]["tree"] = copy.deepcopy(lc["collector_tree"])
                st[tn]["local_sources"] = copy.deepcopy(lc.get("collector_local_sources", []))
                st[tn]["children"] = copy.deepcopy(lc.get("collector_children", []))
                st[tn]["collector_root_node"] = lc.get("collector_root_node", "rst_root_n")
                st[tn]["collector_root_xy"] = list(lc["collector_tree"]["root"])
        # wavefront parents of the pieces (die-wide solve)
        wf = RT.wf_solve(P)
        par = wf.get("parent") or {}
        self.rep["reset_parents"] = {nm: par.get(nm) for ts in self.ts.values() for b in self.pmap
                                     if self.raw_type(b) == ts.tn for nm in self.pmap[b]}

    def _attach(self, tn, lc, tree, reach):
        """collector sources / children of a piece type onto the piece's own reset tree: the nearest tap relay
        (rst_n_t<k>) within reach of the status pin (sources keep their tree-leaf form)"""
        nodes = [r for r in tree["relays"] if re.fullmatch(r"rst_n_t\d+", r["q"])]
        if not nodes:
            raise SplitError(f"{tn}: reset tree has no tap relays")
        for grp in ("collector_local_sources", "collector_children"):
            for s in lc.get(grp, []):
                pts = s.get("status_pins_xy_um") or [s["xy_um"]]
                d = lambda r: max(abs(p[0] - r["xy"][0]) + abs(p[1] - r["xy"][1]) for p in pts)  # noqa: E731
                best = min(nodes, key=lambda r: (d(r), r["q"]))
                if d(best) > reach + 1e-6:
                    raise SplitError(f"{tn}: collector source {s.get('name', s.get('part'))} has no tap relay within "
                                     f"{reach} um ({d(best):.1f})")
                s["node"] = best["q"]
                s["tap"] = int(best["q"][7:])
        lc["collector_root_node"] = "rst_root_n"

    # ---------------------------------------------------------------- as-built manifest
    def _asbuilt(self):
        if not self.ab:
            self.ab_out = None
            return
        ab = copy.deepcopy(self.ab)
        mf = {"parts": {}}
        if ab.get("map_file"):
            # the map file is relative to the asbuilt's folder, else to the plan folder (an event input outside it)
            cands = [self.ab_path.parent / ab["map_file"], self.plan_dir / ab["map_file"]]
            f = next((c for c in cands if c.exists()), None)
            if f is None:
                raise SplitError(f"asbuilt map_file {ab['map_file']} not found in {[str(c.parent) for c in cands]}")
            mf = json.loads(f.read_text())
            self.map_file_source = f.resolve()  # map_file is manifest-relative, unlike the repo-base paths
        inline = ab.setdefault("map", {}).setdefault("parts", {})
        moved = {}
        for src in (mf.get("parts", {}), dict(inline)):
            for k, v in src.items():
                if not isinstance(v, list) or v[0] not in self.pmap:
                    if isinstance(v, str) and v in self.pmap:
                        raise SplitError(f"map {k}: whole split partition {v} (needs a piece)")
                    continue
                base, loc = v
                ts = self.ts[self.raw_type(base)]
                i = self._local_piece(ts, loc)
                inline[k] = [self.pmap[base][i], loc]
                moved[k] = inline[k]
        ist = ab.get("internal_stations_types", [])
        for tn, ts in self.ts.items():
            if tn in ist:
                ab["internal_stations_types"] = ist = ist + [x for x in ts.tnames if x != tn]
        # native_station_exclude {type: [OUT bus]}: those OUT station chains stay KIT stations (asbuilt
        # internal_stations_buses scope = the type's other OUT station buses); a forward row whose plan lane the bind
        # does not use as an outgoing link cannot be realised natively (native_istations.annotate)
        for tn, ex in (self.spec.get("native_station_exclude") or {}).items():
            t = self.out["partition_types"].get(tn)
            if t is None or tn not in ab.get("internal_stations_types", []):
                raise SplitError(f"native_station_exclude: {tn} is not a natively stationed type of the output plan")
            bd = {b["name"]: b["dir"] for b in t["buses"]}
            outs = sorted({r["conn"][4:] for r in t.get("internal_stations", [])
                           if r["conn"].startswith("bus:") and bd.get(r["conn"][4:]) == "out"})
            if set(ex) - set(outs):
                raise SplitError(f"native_station_exclude {tn}: {sorted(set(ex) - set(outs))} are not OUT station buses")
            ab.setdefault("internal_stations_buses", {})[tn] = [b for b in outs if b not in ex]
            self.rep.setdefault("native_station_exclude", {})[tn] = list(ex)
        ab["note"] = f"{self.tag}: type split of {list(self.ts)} | " + ab.get("note", "")
        self.ab_out = ab
        self.rep["map_entries"] = len(moved)
        self.rep["map_pieces"] = dict(Counter(v[0] for v in moved.values()))

    def _census(self, out_dir):
        """G0 census coverage (census_cov): the as-built leaf -> partition map moves the split partitions' leaves to
        their pieces (longest as-built local instance that prefixes the leaf, else the spec content rules) and lets the
        pieces forward like the whole partition did.  The plan's census paths are re-based on the output dir."""
        import os
        spec = self.out.get("census")
        if not spec:
            return {}
        base_dir = rpath(self.spec["census_base"]) if self.spec.get("census_base") else self.plan_dir
        locs = defaultdict(set)
        akey = defaultdict(dict)        # piece partition -> {as-built name: local inst} (census leaves use as-built names)
        for k, v in (self.ab_out or {}).get("map", {}).get("parts", {}).items():
            if isinstance(v, list):
                locs[v[0]].add(v[1])
                akey[v[0]][k] = v[1]
        md5, moved = {}, Counter()
        for k, src in enumerate(spec):
            if not (base_dir / src["map"]).is_file():
                raise SplitError(f"census map {src['map']} not found under {base_dir} (set spec census_base to the "
                                 f"dir the plan's census paths are relative to)")
            mp = json.loads((base_dir / src["map"]).read_text())
            parts = mp.get("parts", {})
            for leaf, part in list(parts.items()):
                if part not in self.pmap:
                    continue
                ts = self.ts[self.raw_type(part)]
                cand = [loc for names in [self.pmap[part]] for pn in names for loc in locs.get(pn, ())
                        if leaf == loc or leaf.startswith(loc + "__")]
                acand = [(k2, loc) for pn in self.pmap[part] for k2, loc in akey.get(pn, {}).items()
                         if leaf == k2 or leaf.startswith(k2 + "__")]
                if cand:
                    i = self._local_piece(ts, max(cand, key=len))
                else:
                    try:
                        i = self._census_leaf_piece(ts, leaf)
                    except SplitError:
                        if not acand:
                            raise
                        i = self._local_piece(ts, max(acand, key=lambda c: len(c[0]))[1])
                parts[leaf] = self.pmap[part][i]
                moved[parts[leaf]] += 1
            fv = mp.get("forward_via", [])
            for j, rx in enumerate(fv):
                for base in self.pmap:
                    if rx == f"^{base}$":
                        fv[j] = f"^{base}(" + "|".join(re.escape(s) for s in self._suffixes()) + ")?$"
            for key in ("forward_routes", "bit_rules", "exempt"):
                if any(base in json.dumps(mp.get(key, [])) for base in self.pmap):
                    raise SplitError(f"census map {src['map']}: {key} names a split partition (not handled)")
            mp["note"] = f"{self.tag}: leaves of {sorted(self.pmap)} moved to their pieces | " + mp.get("note", "")
            name = f"census_map_split_{k}.json"
            md5[name] = jdump(mp, Path(out_dir) / name)
            for f in ("rows", "bitcon"):
                if src.get(f):
                    src[f] = os.path.relpath((base_dir / src[f]).resolve(), Path(out_dir).resolve())
            src["map"] = name
        self.rep["census_map_moved"] = dict(moved)
        return md5

    def _census_leaf_piece(self, ts, leaf):
        """a census leaf with no as-built map instance: its own name, then u_<leaf> (plan cells drop the u_ in the
        census), then spec census_alias {type: {leaf: local inst}}; a split plan cell answers with its fault piece"""
        alias = (self.spec.get("census_alias") or {}).get(ts.tn, {})
        for loc in (leaf, "u_" + leaf, alias.get(leaf)):
            if loc is None:
                continue
            cell = (self.rep.get("plan_cells", {}).get(ts.tn, {}).get("cells", {}) or {}).get(loc)
            if isinstance(cell, dict) and "fault_piece" in cell:
                return int(cell["fault_piece"])
            try:
                return self._local_piece(ts, loc)
            except SplitError:
                continue
        raise SplitError(f"{ts.tn}: census leaf {leaf} has no piece (add spec census_alias)")

    def _suffixes(self):
        ps = list(self.spec["parts"]) + [p for v in (self.spec.get("parts_by_type") or {}).values() for p in v]
        return sorted({p.get("suffix", "") for p in ps if p.get("suffix")}, key=len, reverse=True)

    def _local_piece(self, ts, loc):
        cores = {h["inst"]: h for h in ts.t.get("hard_cores", [])}
        if loc in cores:
            return ts.core_piece(cores[loc])
        if loc in ts.content_piece:
            return ts.content_piece[loc]
        rules = [(re.compile(rx), int(i)) for rx, i in self.spec.get("contents", {}).get(ts.tn, [])]
        v = next((i for rx, i in rules if rx.fullmatch(loc)), None)
        if v is None:
            raise SplitError(f"{ts.tn}: map local {loc} has no piece")
        return v

    # ---------------------------------------------------------------- write
    def write(self, out_dir, rel_dir):
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        md5 = self._census(out)
        cp = self.spec.get("cap_projection")
        if cp:
            # R-CAP per piece: placed movable cells ~= registers in the piece (sink bins by centre) x the anchor kit's
            # movable-per-register ratio x split overhead (hard cores excluded: the anchor's GPL movable count)
            rows = []
            for tn, ts in self.ts.items():
                for i, nm in enumerate(ts.tnames):
                    sb = getattr(ts, "sink_bins", None)
                    if not sb:
                        continue
                    regs = sum(int(b[2]) for b in sb[i]["bins"])
                    proj = int(round(regs * float(cp["movable_per_register"]) * float(cp.get("overhead", 1.03))))
                    rows.append(dict(type=nm, base=tn, piece=i, registers=regs, projected_movable=proj,
                                     verdict="OVER" if proj > 400_000 else "TARGET" if proj > 250_000 else "OK"))
            self.rep["cap_projection"] = dict(method=cp, rows=rows)
        for tn, ts in self.ts.items():
            for i, nm in enumerate(ts.tnames):
                ck = self.out["partition_types"][nm].get("clock") or {}
                if nm in getattr(self, "sink_abs", {}) and ck.get("sink_bins_file") == self.sink_abs[nm]:
                    (out / "sink_bins").mkdir(exist_ok=True)
                    md5[f"sink_bins/{nm}.json"] = jdump(ts.sink_bins[i], out / "sink_bins" / f"{nm}.json")
                    ck["sink_bins_file"] = f"{rel_dir}/sink_bins/{nm}.json"
        txt = json.dumps(self.out)
        p = out / "plan_c.json"
        if p.exists() or p.is_symlink():
            p.unlink()
        p.write_text(txt)
        md5["plan_c.json"] = hashlib.md5(txt.encode()).hexdigest()
        if self.side is not None:
            for r in self.side.get("collector", {}).get("types", {}).values():
                if r.get("tree") is None:
                    raise SplitError("sidecar collector row without a tree")
            txt = json.dumps(self.side, separators=(",", ":"))
            p = out / "eW_sidecar.json"
            if p.exists() or p.is_symlink():
                p.unlink()
            p.write_text(txt)
            md5["eW_sidecar.json"] = hashlib.md5(txt.encode()).hexdigest()
        if self.ab_out is not None:
            if getattr(self, "map_file_source", None) is not None:
                map_rel = Path("inputs") / self.map_file_source.name
                (out / map_rel).parent.mkdir(parents=True, exist_ok=True)
                md5[str(map_rel)] = jdump(json.loads(self.map_file_source.read_text()), out / map_rel)
                self.ab_out["map_file"] = str(map_rel)
            if self.pc_out is not None:
                md5["plan_cells.json"] = jdump(self.pc_out, out / "plan_cells.json")
                self.ab_out["plan_cells"] = f"{rel_dir}/plan_cells.json"
            self.ab_out["clock_landing_table"] = f"{rel_dir}/eW_sidecar.json"
            b = self.ab_out.get("base")
            if b and not Path(b).is_absolute():
                # the manifest base (repo root, relative to the plan folder): re-based on the output folder when it
                # sits at another depth (bind resolves it next to the --asbuilt file; manifest paths stay relative)
                import os
                want = (self.plan_dir / b).resolve()
                if (out / b).resolve() != want:
                    self.ab_out["base"] = os.path.relpath(want, out.resolve())
            md5["asbuilt_vN.json"] = jdump(self.ab_out, out / "asbuilt_vN.json")
        md5["latency_rows.json"] = jdump(dict(schema="opentallas.latency_rows.v1", rule="R-RTL-6", event=self.tag,
                                              rows=self.latency_rows), out / "latency_rows.json")
        self.rep["md5"] = md5
        jdump(self.rep, out / "report.json")
        return md5


def _ts_report_json(o):
    return json.loads(json.dumps(o, default=str))


def census(spec, bind_dir):
    """crossing bits of a base bind that the split cuts, per partition of the family (spec.census input):
      transit  [{hub: partition, bus, how: leaf | fwd:<in bus> | sink, frm, to, bits}]  bits whose bus window sits in
               another piece than their driver / sink
      intra    [[partition, src top, sink top, frm, to, bits]]  leaf -> leaf bits inside the partition across a cut
      ends     {partition: {bus: [[drv | fwd | sink, local inst or in bus, piece, bits]]}}  netlist ends of every bus
      drv_pins {partition: {bus: [[cell, port, bits]]}}  driver pins of the OUT buses
    A leaf's piece: the longest content / hard core that prefixes its as-built local instance, else the spec
    content rules on the local instance; '?<local>' when neither (reported, never routed)."""
    ev = Event({k: v for k, v in spec.items() if k != "census"})     # the census is this command's OUTPUT
    plan_dir = ev.plan_dir
    ab = ev.ab or {}
    mf = json.loads((plan_dir / ab["map_file"]).read_text()) if ab.get("map_file") else {}
    parts = {**mf.get("parts", {}), **ab.get("map", {}).get("parts", {})}
    rules = [(re.compile(a), b) for a, b in mf.get("rules", [])]
    TS, BP = {}, {}
    for tn, ts in ev.ts.items():
        ts.compute_bus_pieces()
        ts.content_pieces()
        for p in ev.raw["partitions"]:
            if p["type"] == tn:
                TS[p["name"]], BP[p["name"]] = ts, ts.bus_piece
    cache = {}

    def lookup(cell):
        if cell in cache:
            return cache[cell]
        p, res = cell, (None, None)
        while True:
            if p in parts:
                v = parts[p]
                res = (v[0], v[1]) if isinstance(v, list) else (v, None)
                break
            if "." not in p:
                break
            p = p.rsplit(".", 1)[0]
        if res[0] is None:
            res = next(((pt, None) for rx, pt in rules if rx.fullmatch(cell)), res)
        cache[cell] = res
        return res

    def piece(cell):
        pt, loc = lookup(cell)
        if pt not in TS:
            return pt, None
        nm = loc or cell
        segs = nm.split(".")
        for k in range(len(segs), 0, -1):
            try:
                return pt, ev._local_piece(TS[pt], ".".join(segs[:k]))
            except SplitError:
                continue
        return pt, "?" + nm

    lat = json.loads((Path(bind_dir) / "bind_latency.json").read_text())["buses"]
    byid = {L["lane"]: L for L in lat}
    T, ENDS, PINS, unk = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter), Counter()
    for L in lat:
        for side in ("src", "dst"):
            h = L[side]
            if h not in TS or side != "src":
                continue
            bus = L["bus_out"]
            if bus not in BP[h]:
                unk[("src-bus-not-planned", h, bus)] += 1
                continue
            bp = BP[h][bus]
            for it in L["source_bits"]:
                if it[0] == "leaf":
                    pt, pc = piece(it[1])
                    if pt != h:
                        unk[("leafsrc-notin", h, it[1][:40])] += 1
                        continue
                    ENDS[(h, bus)][("drv", lookup(it[1])[1] or it[1], pc)] += 1
                    PINS[(h, bus)][(it[1], it[2])] += 1
                    if pc != bp:
                        T[(h, bus, "leaf")][(pc, bp)] += 1
                else:
                    Li = byid[it[1]]
                    if Li["dst"] != h:
                        unk[("fwd-notin", h)] += 1
                        continue
                    pi = BP[h].get(Li["bus_in"])
                    if pi is None:
                        unk[("fwd-bus-not-planned", h, Li["bus_in"])] += 1
                        continue
                    ENDS[(h, bus)][("fwd", Li["bus_in"], pi)] += 1
                    if pi != bp:
                        T[(h, bus, "fwd:" + Li["bus_in"])][(pi, bp)] += 1
    inbits = defaultdict(set)
    for L in lat:
        if L["dst"] not in TS:
            continue
        for it in L["source_bits"]:
            if it[0] == "leaf":
                inbits[(L["dst"], f"{it[1]}.{it[2]}[{it[3]}]")].add(L["bus_in"])
            else:
                sb, hops = it, 0
                while sb and sb[0] != "leaf" and hops < 64:     # a forwarded bit: follow the forward chain to its leaf
                    Li = byid[sb[1]]
                    sb = Li["source_bits"][sb[2]] if sb[2] < len(Li["source_bits"]) else None
                    hops += 1
                if sb and sb[0] == "leaf":
                    inbits[(L["dst"], f"{sb[1]}.{sb[2]}[{sb[3]}]")].add(L["bus_in"])
    sinks = json.loads((Path(bind_dir) / "bind_sinks.json").read_text())
    intra, intra_pins, miss = Counter(), Counter(), Counter()
    for k, v in sinks.items():
        if len(v) < 2 or not isinstance(v[1], str):
            continue
        sc = v[1].split("[")[0].rsplit(".", 1)[0]
        kc = k.split("[")[0].rsplit(".", 1)[0]
        sp, spc = piece(sc)
        kp, kpc = piece(kc)
        if kp in TS and sp == kp:
            if spc != kpc:
                intra[(kp, sc.split(".")[0][:40], kc.split(".")[0][:40], spc, kpc)] += 1
                source_pin = v[1].split("[")[0].rsplit(".", 1)[1]
                intra_pins[(kp, sc.split(".")[0][:40], kc.split(".")[0][:40], spc, kpc, source_pin)] += 1
        elif kp in TS:
            buses = inbits.get((kp, v[1]))
            if not buses:
                miss[(kp, sp)] += 1
                continue
            for bus in buses:
                if bus not in BP[kp]:
                    unk[("sink-bus-not-planned", kp, bus)] += 1      # reset / strap nets bound outside the plan buses
                    continue
                bp = BP[kp][bus]
                ENDS[(kp, bus)][("sink", lookup(kc)[1] or kc, kpc)] += 1
                if bp != kpc:
                    T[(kp, bus, "sink")][(bp, kpc)] += 1
    transit = [dict(hub=h, bus=bus, how=how, frm=a, to=b, bits=n)
               for (h, bus, how), c in sorted(T.items()) for (a, b), n in sorted(c.items(), key=str)]
    ends, pins = defaultdict(dict), defaultdict(dict)
    for (h, bus), c in ENDS.items():
        ends[h][bus] = [[r, n, p, k] for (r, n, p), k in sorted(c.items(), key=str)]
    for (h, bus), c in PINS.items():
        pins[h][bus] = [[cell, port, n] for (cell, port), n in sorted(c.items(), key=str)]
    unplaced = sorted({x for r in transit for x in (r["frm"], r["to"]) if isinstance(x, str)} |
                      {x for k in intra for x in k[3:5] if isinstance(x, str)})
    return dict(ends=ends, drv_pins=pins, transit=transit, intra=[list(k) + [n] for k, n in intra.items()],
                intra_pin_routes=[dict(hub=h, src=sc, dst=kc, frm=a, to=b, port=pin, bits=n)
                                  for (h, sc, kc, a, b, pin), n in sorted(intra_pins.items())],
                unknown=[[*map(str, k), n] for k, n in unk.most_common()],
                missed_sinks=[[*map(str, k), n] for k, n in miss.most_common()], unplaced=unplaced)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split")
    s.add_argument("spec")
    s.add_argument("--out", required=True, help="plan dir (cp -al of the base plan dir; changed files are replaced)")
    s.add_argument("--rel", help="repo-relative path of --out for the manifest (default: derived)")
    c = sub.add_parser("census")
    c.add_argument("spec")
    c.add_argument("--bind", required=True, help="base bind output dir (bind_latency.json, bind_sinks.json)")
    c.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    spec = json.loads(Path(a.spec).read_text())
    if a.cmd == "census":
        try:
            cen = census(spec, a.bind)
        except SplitError as e:
            print(f"type_split: FAIL {e}", file=sys.stderr)
            return 2
        jdump(cen, Path(a.out))
        print(json.dumps(dict(transit=len(cen["transit"]), intra=len(cen["intra"]), unplaced=cen["unplaced"][:20],
                              unknown=cen["unknown"][:5], missed_sinks=cen["missed_sinks"][:5])))
        return 1 if cen["unplaced"] else 0
    try:
        ev = Event(spec)
        ev.out_dir = Path(a.out).resolve()
        ev.run()
        out = Path(a.out).resolve()
        rel = a.rel or str(out.relative_to(ROOT))
        md5 = ev.write(out, rel)
    except SplitError as e:
        print(f"type_split: FAIL {e}", file=sys.stderr)
        return 2
    r = ev.rep
    print(json.dumps(dict(types={tn: ts.tnames for tn, ts in ev.ts.items()}, ports_added=len(r["ports_added"]),
                          lanes_added=len(r["lanes_added"]), lanes_changed=len(r["lanes_changed"]),
                          latency_changed=len(r["latency_changed"]), md5=md5)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
