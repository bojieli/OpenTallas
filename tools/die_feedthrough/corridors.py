#!/usr/bin/env python3
"""Corridor policies for plan.py: quantised feedthrough slots so that replicated blocks share ft variants.

Policy "s81-shifted" (FT-CORR for FT-TOOL, owner 10-23; FT-S81 recipe results/arch/ft_s81_1023/RECIPE.md on
claude/ft-s81-1023, section 3 "Shifted corridors" and the 142a82bdf addendum section 6.1 "4-variant frame plan"):

* FRAMES.  The S81 frames are the u_f_* instances (per-instance rv_f_* stand-ins, base masters col_h9_l4_lp /
  col_h10_l4_lp, told apart by outline height).  They form a 5-column x 7-row array per side (W, E); the column index
  counts from the die edge (0 = outer), the hub direction is +x for the W array and -x for the E array.  Frames off
  the regular grid (u_f_3L01, u_f_4R01, "column 5") are OUTLIERS.
* ROW-ALIGNED LANES.  A frame <-> hub lane runs its horizontal leg in the frame's own row and its vertical leg at the
  hub (route_orders: frame -> hub "HV", hub -> frame "VH").  Lanes between two frames (xo -> x chains) and lanes
  between two non-frame blocks keep the plan default, except that a non-frame lane takes the L order that crosses
  no frame when one exists.
* STREETS (RECIPE 6.1).  The lanes of the outer n_street (2) columns ride their own row's street (the gap above the
  row; the top row uses the die-edge margin), so they cross no frame.  With tail_ret_street (default on) the 70-b
  ret lane of a chain TAIL (a frame whose x input comes from another frame, so it has no hub x lane) rides the
  street too: a corridor then always carries a whole bundle (x 1104 b + ret 70 b), never a ret alone.
* SHIFTED CORRIDORS (RECIPE 3).  A frame's own lanes leave its hub face at slot 0 (its own x / ret pins).  Slot k of
  bus t sits at master offset c_t + k * P on the W/E faces (c_t = own pin centre of bus t, P = slot pitch, 200 um:
  one bundle band of 147.4 + 9.5 um plus the x -> ret offset).  A corridor that enters a frame at slot k leaves it
  at slot k + 1, so every frame with the same populated corridors has the same port offsets (the variant depends on
  how many corridors are populated and from which upstream column, not on the frame's position).  A lane arriving
  from a frame with the opposite y flip lands on the MIRRORED ladder (H - c_t - k * P) and shifts along it.
  Arrivals that are on neither ladder (outlier frames: other y origin / height) pass with one uniform shift per
  frame, the smallest multiple of P that clears the frame's own pin band.
* VARIANT KEY = family + the exact master-frame ft port signature (dir, face, lo, hi, layer, bits) + path stages,
  i.e. plan.py's signature without the per-instance master name.  Because ports exist only where a lane passes, every
  port of a variant carries a lane in every instance (no tie-offs, no open inputs: guarantee (a)); the lane's die
  coordinate is the same on both sides of a street, so abutting ports line up (b).

Guarantees are checked by check_no_ties() / check_alignment(); evaluate() simulates the plan on real data.
Notes the policy reports rather than hides:
* Frames whose own pins face AWAY from the hub (W array MY/R180, E array R0/MX) are "class b": their own lanes must
  cross the frame itself, so the wrapper must place the own ports on the hub face (top-down pin assignment), and a
  class-b host is the face-mirrored master of a class-a host (separate variants).
* The in-frame jog of a shifted corridor makes the in-frame path W + P (1.64 mm for h9 at P = 200) > the 1.5-mm reach:
  plan.py's inout staging then puts 3 registers in a frame instead of 2 (+1 cycle per crossed frame).
* Street lanes are die channel wires on M6 + M8 (street_layer_factor 2, RECIPE 6.1 "~3.9k bits"); a street that is
  full, or blocked by an outlier frame, falls back to the street below the row, then to the corridor.
* The row leg past the array must not cross hard IP (u_phy_hbm, no ft / repeaters): it jogs vertically in the channel
  just before the IP and continues above it (band() returns that post-jog coordinate, refine() draws the jog).

Hooks (plan.py, run()):
    pol = make_policy(corridor, die, blocks, dump, cfg, dict(groups=cen["groups"], occupancy=occupancy,
                      ft_clock=ft_clock, kinds=kinds, forbid_re=forbid_re))          # once, after `blocks`
    orders = pol.route_orders(g) or <default orders>                                 # per lane, before candidates
    c = pol.band(g, horiz, c0, ntr, a, b)   # before each main-leg Tracks.place; not None -> tr.mark(...), no overflow
    pts = pol.refine(g, pts) or pts         # right after pts = dedupe([...]) in both HV and VH branches
    variant = pol.variant_of(rid, master, ports, paths) or <plan hash name>          # per ftspec
    summary["corridors"] = pol.report()

Dry run on S81 cap24 (10-23, census/plan/dump in /srv/opentallas-scratch/claude/ft-tool; evaluate outputs in
.../ft-tool/corridors/s81_eval_*.json; straight-policy plan today: 69 frame variants for 69 frame hosts):
    floorplan as is .......................... col_h9 10, col_h10 4 (2 regular + the 2 outliers)
    frames re-oriented to face the hub ....... col_h9 6,  col_h10 4
    + one y flip per frame row ............... col_h9 3,  col_h10 4   (ft2@slot0 x12, ft2@slot1 x5, ft4 x3)
    20 h9 + 6 h10 frames host ft, 46 stay base; (a)/(b) checks pass; 58 of 66 in-frame paths take 3 registers.

CLI:  corridors.py evaluate --plan PLAN.json --census CENSUS.json.gz --dump DUMPDIR [--orient as-is|hub|hub+row]
"""
import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom  # noqa: E402

EPS = 1e-6
TOL_UM = 0.5
ORIENT_OF_FLIPS = {(False, False): "R0", (False, True): "MX", (True, False): "MY", (True, True): "R180"}
FLIPS_OF_ORIENT = {v: k for k, v in ORIENT_OF_FLIPS.items()}

S81_DEFAULTS = dict(
    frame_re=r"^u_f_",
    families={3369.6: "col_h9_l4_lp", 3672.0: "col_h10_l4_lp"},   # base frame by outline height (RECIPE 1)
    n_street=2,                 # outer columns whose lanes ride the row street (RECIPE 6.1)
    tail_ret_street=True,       # ret of a chain tail rides the street (a corridor always carries a whole bundle)
    slot_pitch_um=200.0,        # multiple of the 0.08 M8 pitch; >= x band 147.4 + x->ret 107 - ... (see _slot_ok)
    x_bus="x", ret_bus="ret",
    own_buses=("x", "ret", "xo"),
    street_guard_um=2.0,
    street_layer_factor=2.0,    # street lanes are channel wires on M6 + M8 (RECIPE 6.1: ~3.9k bits per street at 0.6)
    occupancy=0.6,
    ft_clock="forwarded",
    forbid_re=r"(phy|serdes|ucie|hbm3e|pll|bump)",   # = plan.FORBID_RE: hard IP, no ft, no repeaters over it
    hard_ip_guard_um=20.0,
    min_col_frames=3,           # an x position with fewer frames than this is an outlier column
    orient_override=None,       # what-if: None | "hub" (every frame faces the hub) | "hub+row" (+ one y flip per row)
)


def n_tracks(bits, occupancy, ft_clock):
    return int(math.ceil((bits + (1 if ft_clock == "forwarded" else 0)) / occupancy - 1e-9))


def dedupe(pts):
    out = []
    for p in pts:
        p = (round(p[0], 3), round(p[1], 3))
        if not out or p != out[-1]:
            out.append(p)
    res = []
    for p in out:
        while len(res) >= 2 and ((res[-2][0] == res[-1][0] == p[0]) or (res[-2][1] == res[-1][1] == p[1])):
            res.pop()
        res.append(p)
    return res


class Policy:
    """default policy: every hook returns None (plan.py defaults)."""

    name = "default"

    def route_orders(self, lane):
        return None

    def band(self, lane, horiz, c0, ntr, a, b):
        return None

    def refine(self, lane, pts):
        return None

    def variant_of(self, block_inst, master, ports, paths):
        return None

    def report(self):
        return {}


class Frame:
    def __init__(self, inst, master, x, y, w, h, orient, family, buses):
        self.inst, self.master, self.x, self.y, self.w, self.h = inst, master, x, y, w, h
        self.family = family
        self.buses = buses or {}
        self.regular_orient = orient in FLIPS_OF_ORIENT
        self.flip_x, self.flip_y = FLIPS_OF_ORIENT.get(orient, (False, False))
        self.orient0 = orient
        self.side = None
        self.col = None
        self.row = None          # (side, row index) or None for an outlier
        self.hub_fed = None

    @property
    def orient(self):
        return ORIENT_OF_FLIPS[(self.flip_x, self.flip_y)] if self.regular_orient else self.orient0

    @property
    def xm(self):
        return self.x + self.w / 2.0

    def d2m(self, Y):
        return (self.y + self.h - Y) if self.flip_y else (Y - self.y)

    def m2d(self, m):
        return self.y + (self.h - m if self.flip_y else m)

    def bus_face_die(self, bus):
        b = self.buses.get(bus)
        if b is None or b.face not in ("E", "W"):
            return None
        f = b.face
        return geom.OPP[f] if self.flip_x else f

    def own_centre(self, bus):
        b = self.buses.get(bus)
        if b is None or b.face not in ("E", "W"):
            return None
        return (b.lo + b.hi) / 2.0

    def own_point(self, bus):
        b = self.buses.get(bus)
        if b is None or b.face not in ("E", "W"):
            return None
        px, py = geom.face_point(b.face, b.lo, b.hi, self.w, self.h)
        return geom.xform(px, py, self.w, self.h, self.orient, self.x, self.y)

    def faces_hub(self, x_bus):
        f = self.bus_face_die(x_bus)
        return f == ("E" if self.side == "W" else "W")


class S81ShiftedPolicy(Policy):
    name = "s81-shifted"

    def __init__(self, die, blocks, dump, cfg, opts):
        o = dict(S81_DEFAULTS)
        o.update({k: v for k, v in (opts or {}).items() if v is not None})
        self.o = o
        self.die = die
        self.cfg = cfg or {}
        self.blocks = blocks
        self.dump = dump
        self.P = float(o["slot_pitch_um"])
        self.occ = float(o["occupancy"])
        self.ft_clock = o["ft_clock"]
        L8 = dump.layer("M8") if dump is not None and hasattr(dump, "layer") else None
        self.pitch_h = (L8 or {}).get("pitch", 0.08)
        self.die_box = tuple(dump.die["die"])
        fre = re.compile(o["frame_re"])
        self.frames = {}
        for n, b in blocks.items():
            if not fre.search(n):
                continue
            inst = dump.insts.get(n)
            m = dump.masters.get(inst.master) if inst is not None else None
            fam = None
            for hh, nm in o["families"].items():
                if abs(b["h"] - float(hh)) < 1.0:
                    fam = nm
            fam = fam or b["master"]
            self.frames[n] = Frame(n, b["master"], b["x"], b["y"], b["w"], b["h"],
                                   inst.orient if inst is not None else "R0", fam, m.buses if m else {})
        self.variants = defaultdict(lambda: defaultdict(list))
        self.var_info = {}
        self.issues = []
        self._delta = {}
        self._build_arrays()
        self._apply_override(o["orient_override"])
        self._roles(o.get("groups"))
        self.rects = [(n, f.x, f.y, f.w, f.h) for n, f in self.frames.items()]
        ffre = re.compile(o["forbid_re"], re.I) if o.get("forbid_re") else None
        self.forbidden = [(n, b["x"], b["y"], b["w"], b["h"]) for n, b in blocks.items()
                          if ffre and any(ffre.search(m) for m in [b["master"]] + (b.get("member_masters") or []))]
        self._hip_cursor = defaultdict(float)
        self.street_iv = defaultdict(list)        # (side, i) -> used [(lo, hi)]; street i = the gap above row i
        self.street_bits = defaultdict(int)
        self.lps = {}
        self.host_lanes = defaultdict(list)
        if o.get("groups") is not None:
            self._precompute(o["groups"])

    # ---- frame arrays -----------------------------------------------------------------------------------------
    def _build_arrays(self):
        x0, y0, x1, y1 = self.die_box
        cx = (x0 + x1) / 2.0
        self.rows = {}           # (side, ri) -> dict(y, h, top, frames[by col], street (lo, hi))
        self.streets = {}        # (side, i) -> (lo, hi): i = row index below the street; -1 = bottom die margin
        for side in ("W", "E"):
            fs = [f for f in self.frames.values() if (f.xm < cx) == (side == "W")]
            for f in fs:
                f.side = side
            xs = Counter(round(f.x, 1) for f in fs)
            reg_x = sorted((x for x, n in xs.items() if n >= self.o["min_col_frames"]),
                           key=lambda x: (x - x0) if side == "W" else (x1 - x))
            colof = {x: i for i, x in enumerate(reg_x)}
            reg = [f for f in fs if round(f.x, 1) in colof]
            ys = sorted({round(f.y, 1) for f in reg})
            for f in reg:
                f.col = colof[round(f.x, 1)]
            for ri, yy in enumerate(ys):
                members = sorted((f for f in reg if round(f.y, 1) == yy), key=lambda f: f.col)
                for f in members:
                    f.row = (side, ri)
                hh = max(f.h for f in members)
                top = yy + hh
                nxt = ys[ri + 1] if ri + 1 < len(ys) else y1
                self.rows[(side, ri)] = dict(y=yy, h=hh, frames=[f.inst for f in members],
                                             street=(top + self.o["street_guard_um"], nxt - self.o["street_guard_um"]))
                self.streets[(side, ri)] = self.rows[(side, ri)]["street"]
                if ri == 0:
                    self.streets[(side, -1)] = (y0 + self.o["street_guard_um"], yy - self.o["street_guard_um"])
            for f in fs:
                if f.row is None:
                    f.col = len(reg_x)          # outlier: beyond the inner column

    def _apply_override(self, mode):
        if not mode:
            return
        for f in self.frames.values():
            if not f.regular_orient:
                continue
            if mode in ("hub", "hub+row") and not f.faces_hub(self.o["x_bus"]):
                f.flip_x = not f.flip_x
        if mode == "hub+row":
            for key, r in self.rows.items():
                fl = Counter(self.frames[n].flip_y for n in r["frames"])
                maj = fl.most_common(1)[0][0]
                for n in r["frames"]:
                    self.frames[n].flip_y = maj
        self.issues.append(f"orient_override={mode}: what-if orientation, not the current floorplan")

    def _roles(self, groups):
        if groups is None:
            return
        xb = self.o["x_bus"]
        for f in self.frames.values():
            f.hub_fed = False
        for g in groups:
            if g["dst"] in self.frames and g["dst_bus"] == xb and g["src"] not in self.frames:
                self.frames[g["dst"]].hub_fed = True

    # ---- per-lane plan ----------------------------------------------------------------------------------------
    @staticmethod
    def key(lane):
        return (lane["src"], lane["src_bus"], lane["dst"], lane["dst_bus"])

    def _frame_end(self, lane):
        fs, fd = lane["src"] in self.frames, lane["dst"] in self.frames
        if fs == fd:
            return None
        if fs:
            return self.frames[lane["src"]], lane["src_bus"], True
        return self.frames[lane["dst"]], lane["dst_bus"], False

    def _is_rider(self, U, bus):
        if U.row is None:
            return False
        if U.col < self.o["n_street"]:
            return True
        return bool(self.o["tail_ret_street"] and bus == self.o["ret_bus"] and U.hub_fed is False)

    def _street_slot(self, U, ntr, bits, xa, xb):
        """band centre in the row's street (the gap above the row), else in the gap below; never over a regular
        frame.  A band that would cross an outlier frame is taken only when no clear band is left in either street
        (the outlier then hosts it).  None when both streets are full (the lane then becomes a corridor lane)."""
        w = ntr * self.pitch_h / float(self.o["street_layer_factor"])
        side, ri = U.row
        outl = [(F.y, F.y + F.h) for F in self.frames.values()
                if F.row is None and F.x < max(xa, xb) - EPS and F.x + F.w > min(xa, xb) + EPS]
        fits = []
        for pref, sid in enumerate(((side, ri), (side, ri - 1))):
            if sid not in self.streets:
                continue
            lo, hi = self.streets[sid]
            used = sorted(self.street_iv[sid])
            gaps, cur = [], hi
            for a, b in sorted(used, key=lambda t: -t[1]):
                if cur - b >= w - EPS:
                    gaps.append((b, cur))
                cur = min(cur, a)
            if cur - lo >= w - EPS:
                gaps.append((lo, cur))
            for g0, g1 in gaps:                       # top-first; edges and outlier boundaries as candidate spots
                cands = [g1 - w / 2.0, g0 + w / 2.0] + [e + s_ * w / 2.0 for iv in outl for e in iv for s_ in (-1, 1)]
                for c in cands:
                    if c - w / 2.0 < g0 - EPS or c + w / 2.0 > g1 + EPS:
                        continue
                    hit = any(c - w / 2.0 < oh and c + w / 2.0 > ol for ol, oh in outl)
                    fits.append((hit, pref, -c, c, sid))
        if not fits:
            self.issues.append(f"street full for {U.inst} ({bits} b, row {U.row}): lane goes through the frames")
            return None
        hit, _, _, c, sid = min(fits)
        self.street_iv[sid].append((c - w / 2.0, c + w / 2.0))
        self.street_bits[sid] += bits
        return c

    def _own_band(self, F):
        """master-frame union of F's own lane bands on its hub face (pin ranges and their M8 track bands)."""
        segs = []
        for bn in self.o["own_buses"]:
            b = F.buses.get(bn)
            if b is None or b.face not in ("E", "W"):
                continue
            c = (b.lo + b.hi) / 2.0
            half = n_tracks(b.nbits, self.occ, self.ft_clock) * self.pitch_h / 2.0
            segs.append((min(b.lo, c - half), max(b.hi, c + half)))
        return segs

    def _ladder(self, F, m, bus):
        """-> ('b'|'t', k) when master offset m is slot k of F's bottom / mirrored ladder for bus, else None."""
        c = F.own_centre(bus)
        if c is None:
            c = F.own_centre(self.o["x_bus"])
        if c is None:
            return None
        kb = (m - c) / self.P
        if abs(kb - round(kb)) * self.P < TOL_UM and round(kb) >= 0:
            return ("b", int(round(kb)), c)
        kt = (F.h - c - m) / self.P
        if abs(kt - round(kt)) * self.P < TOL_UM and round(kt) >= 0:
            return ("t", int(round(kt)), c)
        return None

    def _shift(self, F, y, bus, half):
        m = F.d2m(y)
        lad = self._ladder(F, m, bus) if F.row is not None else None
        if lad is not None:
            side, k, c = lad
            m2 = c + (k + 1) * self.P if side == "b" else F.h - c - (k + 1) * self.P
            return F.m2d(m2), (side, k)
        return None, ("irr", None)

    def _fix_delta(self, F, arrivals):
        """uniform shift (multiple of P) for an off-ladder host: clears the own band, stays inside the outline."""
        own = self._own_band(F)
        cands = [0.0]
        for j in range(1, int(F.h / self.P) + 2):
            cands += [j * self.P, -j * self.P]
        g = self.o["street_guard_um"]
        for d in cands:
            ok = True
            for lo, hi in arrivals:
                a, b = lo + d, hi + d
                if a < g or b > F.h - g or any(a < oh and b > ol for ol, oh in own):
                    ok = False
                    break
            if ok:
                return d
        self.issues.append(f"{F.inst}: no uniform corridor shift clears the own band for {len(arrivals)} arrivals")
        return 0.0

    def _precompute(self, groups):
        kinds = set(self.o.get("kinds", ("data", "ctl")))
        lanes = []
        for g in groups:
            if g.get("kind", "data") not in kinds:
                continue
            fe = self._frame_end(g)
            if fe is None:
                continue
            U, bus, src_is = fe
            lanes.append((U.side or "", U.row[1] if U.row else 99, -g["bits"], U.col or 0, U.inst, bus, g))
        lanes.sort(key=lambda t: t[:6])      # widest first inside a row: streets pack without fragmenting
        pend = {}
        for *_, g in lanes:
            lp = self._start(g)
            self.lps[self.key(g)] = lp
            pend[self.key(g)] = lp
        # walk hosts; off-ladder hosts get their uniform shift once all arrivals at them are known
        while pend:
            waiting = defaultdict(list)
            for k, lp in list(pend.items()):
                if self._walk(lp):
                    del pend[k]
                else:
                    F = lp["blocked_at"]
                    waiting[F].append(lp)
            if not waiting:
                break
            for F, lps in waiting.items():
                fr = self.frames[F]
                arr = sorted((fr.d2m(lp["y"]) - lp["half"], fr.d2m(lp["y"]) + lp["half"]) for lp in lps)
                arr = [(min(a, b), max(a, b)) for a, b in arr]
                self._delta[F] = self._fix_delta(fr, arr)
        for k, lp in self.lps.items():
            for h in lp["hosts"]:
                self.host_lanes[h["F"]].append((k, h["how"], lp["bus"], lp["bits"]))

    def _start(self, g):
        U, bus, src_is = self._frame_end(g)
        P = tuple(g["src_pt"] if src_is else g["dst_pt"])
        if self.o["orient_override"]:
            q = U.own_point(bus)
            if q is not None:
                P = q
        Q = tuple(g["dst_pt"] if src_is else g["src_pt"])
        ntr = n_tracks(g["bits"], self.occ, self.ft_clock)
        half = ntr * self.pitch_h / 2.0
        rider = self._is_rider(U, bus)
        y = self._street_slot(U, ntr, g["bits"], P[0], Q[0]) if rider else None
        if y is None:
            rider, y = False, P[1]
        lo, hi = min(P[0], Q[0]), max(P[0], Q[0])
        cands = sorted((F for F in self.frames.values() if F is not U and F.x < hi - EPS and F.x + F.w > lo + EPS),
                       key=lambda F: abs(F.xm - P[0]))
        return dict(kind="street" if rider else "corridor", U=U.inst, bus=bus, src_is_frame=src_is, P=P, Q=Q,
                    bits=g["bits"], ntr=ntr, half=half, y_init=y, y=y, hosts=[], cands=[F.inst for F in cands],
                    ci=0, class_b=not U.faces_hub(self.o["x_bus"]), blocked_at=None)

    def _walk(self, lp):
        while lp["ci"] < len(lp["cands"]):
            F = self.frames[lp["cands"][lp["ci"]]]
            y = lp["y"]
            if not (F.y + EPS < y < F.y + F.h - EPS):
                lp["ci"] += 1
                continue
            y2, how = self._shift(F, y, lp["bus"], lp["half"])
            if y2 is None:
                if F.inst not in self._delta:
                    lp["blocked_at"] = F.inst
                    return False
                d = self._delta[F.inst]
                y2 = F.m2d(F.d2m(y) + d)
                how = ("irr", d)
            lp["hosts"].append(dict(F=F.inst, y_in=y, y_out=y2, how=how))
            lp["y"] = y2
            lp["ci"] += 1
        lp["y_final"] = lp["y"]
        self._hard_ip_detour(lp)
        return True

    def _hard_ip_detour(self, lp):
        """the row-aligned leg past the frame array must not cross hard IP (HBM PHY at the die bottom: no ft, no
        repeaters): jog vertically in the channel just before it and run the rest of the leg clear of it."""
        lp["y_hub"], lp["jog_x"] = lp["y_final"], None
        P, Q, y, half = lp["P"], lp["Q"], lp["y_final"], lp["half"]
        x0 = self.frames[lp["hosts"][-1]["F"]].xm if lp["hosts"] else P[0]
        hits = geom.seg_crossings((x0, y), (Q[0], y), self.forbidden)
        if not hits:
            return
        dirx = 1.0 if Q[0] > x0 else -1.0
        rid = min(hits, key=lambda h: h[4])[0]
        _, rx, ry, rw, rh = next(r for r in self.forbidden if r[0] == rid)
        g = self.o["hard_ip_guard_um"]
        up = Q[1] > ry + rh / 2.0
        ky, kx = (rid, "y", up), (rid, "x", dirx)
        lp["y_hub"] = (ry + rh + g + half + self._hip_cursor[ky]) if up else (ry - g - half - self._hip_cursor[ky])
        cx = self._hip_cursor[kx]
        lp["jog_x"] = (rx - g - half - cx) if dirx > 0 else (rx + rw + g + half + cx)
        self._hip_cursor[ky] += 2 * half
        self._hip_cursor[kx] += 2 * half
        self.issues.append(f"{lp['U']}/{lp['bus']}: row leg detours around hard IP {rid} (jog at x {lp['jog_x']:.0f})")

    def lane_plan(self, lane):
        return self.lps.get(self.key(lane))

    # ---- hooks --------------------------------------------------------------------------------------------------
    def route_orders(self, lane):
        lp = self.lane_plan(lane)
        if lp is not None:
            return ("HV",) if lp["src_is_frame"] else ("VH",)
        if lane["src"] in self.frames or lane["dst"] in self.frames:
            return None
        sp, dp = tuple(lane["src_pt"]), tuple(lane["dst_pt"])
        hit = {}
        for order in ("HV", "VH"):
            hit[order] = bool(geom.path_crossings(geom.l_route(sp, dp, order), self.rects, {lane["src"], lane["dst"]}))
        if hit["HV"] != hit["VH"]:
            return ("VH",) if hit["HV"] else ("HV",)
        return None

    def band(self, lane, horiz, c0, ntr, a, b):
        lp = self.lane_plan(lane)
        if lp is None or not horiz:
            return None
        return round(lp["y_hub"], 3)

    def array_path(self, lp):
        P = lp["P"]
        path = [P]
        if abs(lp["y_init"] - P[1]) > EPS:
            path.append((P[0], lp["y_init"]))
        for h in lp["hosts"]:
            xm = self.frames[h["F"]].xm
            path += [(xm, h["y_in"]), (xm, h["y_out"])]
        if lp.get("jog_x") is not None:
            path += [(lp["jog_x"], lp["y_final"]), (lp["jog_x"], lp["y_hub"])]
        return path

    def refine(self, lane, pts):
        lp = self.lane_plan(lane)
        if lp is None or not pts:
            return None
        pts = [tuple(p) for p in pts]
        P = lp["P"]
        yf = round(lp["y_hub"], 3)
        path = self.array_path(lp)
        if lp["src_is_frame"]:
            rest = list(pts[1:])
            while rest and abs(rest[0][0] - P[0]) < EPS:
                rest.pop(0)
            if not rest or abs(rest[0][1] - yf) > 1e-3:
                self.issues.append(f"refine: lane {self.key(lane)} H leg not at band {yf}")
                return None
            return dedupe(path + rest)
        head = list(pts[:-1])
        while head and abs(head[-1][0] - P[0]) < EPS:
            head.pop()
        if not head or abs(head[-1][1] - yf) > 1e-3:
            self.issues.append(f"refine: lane {self.key(lane)} H leg not at band {yf}")
            return None
        return dedupe(head + path[::-1])

    @staticmethod
    def signature(ports, paths):
        return sorted((p["dir"], p["face"], round(p["lo"], 1), round(p["hi"], 1), p["layer"], p["bits"])
                      for p in ports) + sorted((q["bits"], q["stages"]) for q in paths)

    def variant_of(self, block_inst, master, ports, paths):
        F = self.frames.get(block_inst)
        if F is None:
            return None
        have = {q["path"] for q in paths if q.get("lane")}
        bad = [p["name"] for p in ports if p["path"] not in have]
        if bad:
            self.issues.append(f"{block_inst}: ports without a lane {bad[:4]} (would be tie-offs)")
        h = hashlib.sha1(json.dumps(self.signature(ports, paths)).encode()).hexdigest()[:6]
        cls = "" if F.faces_hub(self.o["x_bus"]) else "b"
        name = f"{F.family}__ft{len(paths)}{cls}_{h}"
        self.variants[F.family][name].append(block_inst)
        desc = sorted(f"{lb}:{how[0]}{'' if how[1] is None else (how[1] if how[0] != 'irr' else int(how[1]))}"
                      for _, how, lb, _ in self.host_lanes.get(block_inst, []))
        self.var_info[name] = dict(family=F.family, n_paths=len(paths), class_b=bool(cls), outlier=F.row is None,
                                   corridors=desc)
        return name

    def report(self):
        fams = sorted({f.family for f in self.frames.values()})
        out = dict(policy=self.name, options={k: v for k, v in self.o.items() if k not in ("groups", "families")},
                   slot_pitch_um=self.P)
        per = {}
        for fam in fams:
            vs = self.variants.get(fam, {})
            hosts = sum(len(v) for v in vs.values())
            n_frames = sum(1 for f in self.frames.values() if f.family == fam)
            per[fam] = dict(frames=n_frames, ft_hosts=hosts, base_only=n_frames - hosts, n_variants=len(vs),
                            le4=len(vs) <= 4,
                            variants={k: dict(n=len(v), insts=sorted(v), **self.var_info.get(k, {}))
                                      for k, v in sorted(vs.items(), key=lambda t: -len(t[1]))},
                            why=self._why(fam, vs))
        out["families"] = per
        out["streets"] = {f"{k[0]}{k[1]}": dict(bits=self.street_bits[k],
                                                used_um=round(sum(b - a for a, b in self.street_iv[k]), 1),
                                                width_um=round(v[1] - v[0], 1),
                                                cap_bits=int((v[1] - v[0]) / self.pitch_h * self.occ *
                                                             self.o["street_layer_factor"]))
                          for k, v in sorted(self.streets.items()) if self.street_iv[k]}
        cb = sorted(f.inst for f in self.frames.values() if not f.faces_hub(self.o["x_bus"]))
        out["class_b_frames"] = dict(n=len(cb), insts=cb,
                                     note="own pins face away from the hub: wrapper must put own ports on the hub "
                                          "face (or re-orient the frame); a class-b host is a face-mirrored variant")
        jogs = [abs(h["y_out"] - h["y_in"]) for lp in self.lps.values() for h in lp["hosts"]]
        out["corridor_jogs_um"] = dict(n=len(jogs), max=round(max(jogs), 1) if jogs else 0,
                                       note="in-frame path = frame width + jog; > reach adds one register per frame")
        out["lanes"] = dict(total=len(self.lps), street=sum(1 for lp in self.lps.values() if lp["kind"] == "street"),
                            corridor=sum(1 for lp in self.lps.values() if lp["kind"] == "corridor"),
                            through_outlier=sum(1 for lp in self.lps.values()
                                                if any(self.frames[h["F"]].row is None for h in lp["hosts"])))
        out["issues"] = self.issues[:200]
        return out

    def _why(self, fam, vs):
        if len(vs) <= 4:
            return []
        why = []
        infos = [self.var_info.get(k, {}) for k in vs]
        nb = sum(1 for i in infos if i.get("class_b"))
        nt = sum(1 for i in infos if any(":t" in c for c in i.get("corridors", [])))
        no = sum(1 for i in infos if i.get("outlier"))
        pats = Counter(tuple(sorted({c.split(":")[1][0] + c.split(":")[1][1:] for c in i.get("corridors", [])}))
                       for i in infos)
        if nb:
            why.append(f"{nb} variants are class-b hosts (own pins face away from the hub; face-mirrored masters)")
        if nt:
            why.append(f"{nt} variants carry lanes from a frame with the opposite y flip (mirrored-ladder slots)")
        if no:
            why.append(f"{no} variants are outlier frames (off-grid y origin, irregular slots)")
        why.append(f"{len(pats)} distinct corridor-slot patterns (which upstream columns are hub-fed)")
        return why


POLICIES = {"s81-shifted": S81ShiftedPolicy}


def make_policy(name, die, blocks, dump, cfg, opts=None):
    """-> Policy or None.  opts["groups"] = the census lane groups (required by s81-shifted: corridor slots and
    street packing are precomputed from all frame lanes, so the result does not depend on plan.py's lane order)."""
    if not name or name in ("none", "default"):
        return None
    if name not in POLICIES:
        raise ValueError(f"unknown corridor policy {name!r} (have {sorted(POLICIES)})")
    return POLICIES[name](die, blocks, dump, cfg, opts or {})


# ---- checks -----------------------------------------------------------------------------------------------------
def check_no_ties(specs, variant_of):
    """(a): every instance of a variant has the identical port signature and every port carries a lane.
    specs: {inst: dict(ports, paths)}; variant_of: {inst: variant}.  -> list of failures."""
    fails = []
    by = defaultdict(list)
    for inst, v in variant_of.items():
        by[v].append(inst)
    for v, insts in by.items():
        sigs = {json.dumps(S81ShiftedPolicy.signature(specs[i]["ports"], specs[i]["paths"])) for i in insts}
        if len(sigs) > 1:
            fails.append(f"{v}: {len(sigs)} different port signatures")
        for i in insts:
            have = {q["path"] for q in specs[i]["paths"] if q.get("lane")}
            for p in specs[i]["ports"]:
                if p["path"] not in have:
                    fails.append(f"{v}/{i}: port {p['name']} has no lane")
    return fails


def check_alignment(lane_hosts, frames, tol=1e-3):
    """(b): along every lane, the out port of a host and the in port of the next host / the lane's continuing leg
    are at the same die coordinate.  lane_hosts: {lane: [dict(F, p_in, p_out)]} in path order (die points)."""
    fails = []
    for lk, hs in lane_hosts.items():
        for a, b in zip(hs, hs[1:]):
            fa, fb = frames[a["F"]], frames[b["F"]]
            gap = abs(fb.xm - fa.xm) - (fa.w + fb.w) / 2.0
            if gap > 400.0:      # not abutting across a street
                continue
            ax = 1 if a.get("face_out", "E") in ("E", "W") else 0      # along-face coordinate
            if abs(a["p_out"][ax] - b["p_in"][ax]) > tol:
                fails.append(f"{lk}: {a['F']} out {'xy'[ax]} {a['p_out'][ax]} != {b['F']} in {b['p_in'][ax]}")
    return fails


# ---- simulation on real data --------------------------------------------------------------------------------------
def _load(p):
    import gzip
    return json.load(gzip.open(p, "rt") if str(p).endswith(".gz") else open(p))


def simulate(pol, groups, reach, rep, ft_reg="inout", kinds=("data", "ctl"), pitch_v=0.08,
             include_chain_crossings=False):
    """plan.py's ft-spec construction for the frame hosts with the policy hooks applied (frames only).
    -> (specs {inst: {ports, paths}}, variant {inst: name}, lane_hosts, misc)"""
    import plan as plan_mod
    specs = defaultdict(lambda: dict(ports=[], paths=[]))
    lane_hosts = {}
    misc = Counter()
    fre = re.compile(plan_mod.FORBID_RE, re.I)
    forb = [(n, b["x"], b["y"], b["w"], b["h"]) for n, b in pol.blocks.items()
            if fre.search(b["master"]) or any(fre.search(m) for m in (b.get("member_masters") or []))]
    for g in groups:
        if g.get("kind", "data") not in kinds:
            continue
        sp, dp = tuple(g["src_pt"]), tuple(g["dst_pt"])
        orders = pol.route_orders(g)
        lp = pol.lane_plan(g)
        if lp is not None:
            P = lp["P"]
            if lp["src_is_frame"]:
                sp = P
            else:
                dp = P
            y = pol.band(g, True, None, lp["ntr"], sp[0], dp[0])
            # HV (frame -> hub): pin jog at sp.x, H leg at the band, V leg at the hub x;
            # VH (hub -> frame): V leg at the hub x, H leg at the band, pin jog at dp.x: the same corner list
            pts = dedupe([sp, (sp[0], y), (dp[0], y), dp])
            r = pol.refine(g, pts)
            if r is None:
                misc["refine_fail"] += 1
                continue
            pts = r
            if geom.path_crossings(pts, forb, {g["src"], g["dst"]}):
                misc["policy_lanes_over_hard_ip"] += 1     # plan.py would keep these on their channel route
        else:
            chain = g["src"] in pol.frames and g["dst"] in pol.frames
            pts = geom.l_route(sp, dp, (orders or ("VH" if chain else "HV",))[0])
        cr = geom.path_crossings([tuple(p) for p in pts], pol.rects, {g["src"], g["dst"]})
        if not cr:
            continue
        if lp is None:
            if chain:
                # frame -> frame (xo -> x) chains that cross frames are the 26-mm / 5-mm slot-pair bugs (COORD
                # ruling 4: slot swap); counted, not hosted, unless include_chain_crossings
                misc["chain_lanes_crossing_frames"] += 1
                misc.setdefault("chain_lanes", []).append(f"{g['src']}->{g['dst']}")
                if not include_chain_crossings:
                    continue
            else:
                misc["other_lanes_crossing_frames"] += 1
        L = geom.polyline_len(pts)
        hs = []
        for rid, ln, fi, fo, ti, to in cr:
            F = pol.frames[rid]
            regs, _ = plan_mod.stage_plan(L, [(rid, ti, to)], reach, rep, ft_reg)
            stages = sum(1 for t, w in regs if w == rid)
            pin, pout = geom.point_at(pts, ti), geom.point_at(pts, to)
            sp_ = specs[rid]
            k = len(sp_["paths"])
            ports = []
            for nm, d, p in ((f"ft{k}_i", "input", pin), (f"ft{k}_o", "output", pout)):
                mx, my = plan_mod.inv_xform(p[0], p[1], F.w, F.h, F.orient, F.x, F.y)
                face = geom.nearest_face(mx, my, 0, 0, F.w, F.h)
                horiz = face in ("W", "E")
                width = n_tracks(g["bits"], pol.occ, pol.ft_clock) * (pol.pitch_h if horiz else pitch_v)
                off = my if horiz else mx
                ports.append(dict(name=nm, path=k, dir=d, face=face, lo=round(off - width / 2, 3),
                                  hi=round(off + width / 2, 3), layer="M8" if horiz else "M9", bits=g["bits"]))
            sp_["ports"] += ports
            sp_["paths"].append(dict(path=k, lane=f"{g['src']}/{g['src_bus']}->{g['dst']}/{g['dst_bus']}",
                                     bits=g["bits"], stages=stages, len_um=round(ln, 1)))
            hs.append(dict(F=rid, p_in=pin, p_out=pout, face_in=fi, face_out=fo))
        lane_hosts[pol.key(g)] = hs
    variant = {inst: pol.variant_of(inst, pol.frames[inst].master, s["ports"], s["paths"]) for inst, s in specs.items()}
    return specs, variant, lane_hosts, misc


def evaluate(plan_json, census_json, dump_dir, die="s81", **opts):
    """dry run on real data without plan.py changes: re-routes the frame lanes with the policy, rebuilds the frame
    ftspecs the way plan.py does, keys them by the corridor signature.  -> dict (report + checks + baseline)."""
    import dies
    from dump_io import Dump
    cen = _load(census_json)
    pl = _load(plan_json) if plan_json else None
    dump = Dump(dump_dir)
    cfg = dies.get(die)
    blocks = {b["inst"]: b for b in cen["blocks"]}
    o = dict(opts)
    o["groups"] = cen["groups"]
    if pl:
        o.setdefault("ft_clock", pl["summary"].get("ft_clock"))
        o.setdefault("occupancy", pl["summary"].get("occupancy"))
    pol = make_policy("s81-shifted", die, blocks, dump, cfg, o)
    reach = (pl or {}).get("summary", {}).get("reach_um") or cen["summary"]["reach_um"]
    rep = (pl or {}).get("summary", {}).get("rep_um") or cfg["rep_um"]
    specs, variant, lane_hosts, misc = simulate(pol, cen["groups"], reach, rep,
                                                include_chain_crossings=bool(opts.get("include_chain_crossings")))
    rep_ = pol.report()
    rep_["checks"] = dict(no_ties=check_no_ties(specs, variant)[:20],
                          alignment=check_alignment(lane_hosts, pol.frames)[:20])
    rep_["checks"]["pass"] = not rep_["checks"]["no_ties"] and not rep_["checks"]["alignment"]
    rep_["sim"] = dict(misc)
    stg = Counter(q["stages"] for s in specs.values() for q in s["paths"])
    rep_["sim"]["frame_path_stages"] = dict(sorted(stg.items()))
    if pl:
        base = {k: v for k, v in pl["variants"].items() if re.search(pol.o["frame_re"].replace("^u_", "^rv_"), k)}
        rep_["baseline_plan"] = dict(policy=pl["summary"].get("policy"),
                                     frame_variants=sum(len(v) for v in base.values()),
                                     frame_hosts=sum(len(x) for v in base.values() for x in v.values()))
    rep_["summary"] = {fam: d["n_variants"] for fam, d in rep_["families"].items()}
    return rep_


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--plan")
    e.add_argument("--census", required=True)
    e.add_argument("--dump", required=True)
    e.add_argument("--die", default="s81")
    e.add_argument("--orient", default="as-is", choices=("as-is", "hub", "hub+row"))
    e.add_argument("--n-street", type=int, default=None)
    e.add_argument("--no-tail-ret-street", action="store_true")
    e.add_argument("--slot-pitch-um", type=float, default=None)
    e.add_argument("--street-layer-factor", type=float, default=None, help="2 = M6+M8 (default), 1 = M8 only")
    e.add_argument("--out")
    e.add_argument("--full", action="store_true", help="print the full report (default: summary)")
    a = ap.parse_args(argv)
    r = evaluate(a.plan, a.census, a.dump, die=a.die, orient_override=None if a.orient == "as-is" else a.orient,
                 n_street=a.n_street, tail_ret_street=False if a.no_tail_ret_street else None,
                 slot_pitch_um=a.slot_pitch_um, street_layer_factor=a.street_layer_factor)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(r, f, indent=1, default=str)
    if a.full:
        print(json.dumps(r, indent=1, default=str))
    else:
        short = dict(summary=r["summary"], checks_pass=r["checks"]["pass"], baseline=r.get("baseline_plan"),
                     streets=r["streets"], lanes=r["lanes"],
                     class_b=r["class_b_frames"]["n"], jogs=r["corridor_jogs_um"], sim=r["sim"],
                     why={k: v["why"] for k, v in r["families"].items()},
                     variants={k: {n: (v["n"], v["corridors"]) for n, v in d["variants"].items()}
                               for k, d in r["families"].items()}, issues=r["issues"][:10])
        print(json.dumps(short, indent=1, default=str))
    return r


if __name__ == "__main__":
    main()
