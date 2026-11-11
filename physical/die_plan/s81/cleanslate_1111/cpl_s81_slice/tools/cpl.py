#!/usr/bin/env python3
"""CPL-S81-SLICE 11-11 (DO_NOT_COUNT): intra-type hard-core placement model for S81 slice / kv_leaf types.

  model   : cores (pins per bus, orient-aware), fixed macros (contents with origin), faces/windows, ft slots, landing
            bands, internal stations, core clock taps, core_conns links (group prefixes resolved) + station links.
  score   : bit-mm (links), worst full cut H/V (bits crossing / tracks), route_supply p99 (in-process analyze_type),
            station-count check (EQ: needed stages <= sited stages on every relay/R3 station).
  bound   : intrinsic min-cut (fixed traffic + per-core best side, best-case supply) per cut line.
  render  : PNG of the type (outline, windows, ft, bands, macros, cores + pin groups per face, flylines by bits,
            reach circles, cut table).
  search  : B34-style legal local search on the 4.32 lattice (relocate / swap equal size / flip), keeps outline,
            faces, buses, ft slots, bands, clock tap and station counts.
"""
import copy
import json
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE / "repo"
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import route_supply as RS  # noqa: E402

DIE_DIR = (REPO / "physical" / "die_plan" / "s81").resolve()
RS.REF_DIRS[:] = [str(DIE_DIR)]
LAT = 4.32
REACH_STEP = 405.0 * 0.98
PITCH = {"M2": 0.0419, "M3": 0.0371, "M4": 0.048, "M5": 0.0503, "M6": 0.074, "M7": 0.0681}
DER = {"M2": .2914, "M3": .2573, "M4": .2568, "M5": .2599, "M6": .3118, "M7": .3239}
HL, VL = ("M2", "M4", "M6"), ("M3", "M5", "M7")
LORDER = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
CELL_FILL = 0.35
ENTRY_TPU = 25.6       # usable turn tracks per um of street beside a face window (M3/M5/M7 x 0.8, cell share off)       # share of M2-M5 used by std-cell wiring in open area (route_supply background, rounded)

_LEF_SIZE = {}


def lef_size(rel):
    if rel in _LEF_SIZE:
        return _LEF_SIZE[rel]
    for d in (DIE_DIR, REPO):
        p = Path(d) / rel
        if p.is_file():
            m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", p.read_text(errors="ignore"))
            if m:
                _LEF_SIZE[rel] = (float(m.group(1)), float(m.group(2)))
                return _LEF_SIZE[rel]
    _LEF_SIZE[rel] = None
    return None


_PINRAW = {}


def raw_pins(h):
    pf = h.get("pins_file")
    if pf not in _PINRAW:
        out = []
        for d in (DIE_DIR, REPO):
            p = Path(d) / pf
            if p.is_file():
                js = RS.read_json(p)
                for name, xy in RS._pin_iter(js):
                    out.append((re.sub(r"\[\d+\]$", "", name), float(xy[0]), float(xy[1])))
                break
        _PINRAW[pf] = out
    return _PINRAW[pf]


def opt(w, hh, o, x, y):
    X = w - x if o in ("MY", "R180") else x
    Y = hh - y if o in ("MX", "R180") else y
    return X, Y


def face_of(w, hh, x, y):
    d = {"W": x, "E": w - x, "S": y, "N": hh - y}
    return min(d, key=d.get)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Model:
    def __init__(self, P, tname, conns, bound=None):
        self.P, self.name = P, tname
        self.t = P["partition_types"][tname]
        t = self.t
        self.W, self.H = map(float, t["outline_um"])
        self.cores = [dict(h) for h in t.get("hard_cores", [])]
        self.ix = {h["inst"]: i for i, h in enumerate(self.cores)}
        self.pins = {}       # module -> {bus: [(x,y) R0 local]}
        for h in self.cores:
            if h["module"] not in self.pins:
                d = defaultdict(list)
                for bus, x, y in raw_pins(h):
                    d[bus].append((x, y))
                self.pins[h["module"]] = dict(d)
        self.buses = {b["name"]: b for b in t.get("buses", []) or [] if b.get("face")}
        # fixed macros: contents with origin
        self.fixed = []
        for c in t.get("contents", []) or []:
            if c.get("origin_um") and c.get("lef"):
                sz = lef_size(c["lef"])
                if sz:
                    o = c.get("orient", "R0")
                    w, hh = (sz[1], sz[0]) if o in ("R90", "R270", "MXR90", "MYR90") else sz
                    self.fixed.append((c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + w,
                                       c["origin_um"][1] + hh, c["inst"], c["module"]))
        self.bands = []
        for k, bd in (((t.get("clock") or {}).get("landing_contract") or {}).get("bands") or {}).items():
            if bd.get("rect_um"):
                self.bands.append((tuple(bd["rect_um"]), k, bd.get("width", 0)))
        self.ft = t.get("ft_slots", []) or []
        self.tap = tuple((t.get("clock") or {}).get("tap_um") or (self.W / 2, self.H / 2))
        self.stations = t.get("internal_stations", []) or []
        cc_key = next((k for k in (tname, re.sub(r"__cl[0-9a-f]{8}.*$", "", tname), re.sub(r"__.*$", "", tname))
                       if conns.get(k)), None)
        self.cc = conns.get(cc_key, {}) if cc_key else {}
        self.bound = bound
        self.soft = {}
        self._build_links()
        self.blk = self._blockers()

    # ------------------------------------------------------------------ geometry helpers
    def rect(self, i, pl=None):
        h = self.cores[i]
        (x, y, o) = pl[i] if pl else (h["origin_um"][0], h["origin_um"][1], h.get("orient", "R0"))
        w, hh = h["outline_um"]
        return (x, y, x + w, y + hh)

    def pin_pts(self, i, bus, pl=None):
        h = self.cores[i]
        (x0, y0, o) = pl[i] if pl else (h["origin_um"][0], h["origin_um"][1], h.get("orient", "R0"))
        w, hh = h["outline_um"]
        return [(x0 + X, y0 + Y) for (X, Y) in (opt(w, hh, o, px, py) for px, py in self.pins[h["module"]].get(bus, []))]

    def bus_cen(self, i, bus, pl=None):
        h = self.cores[i]
        key = (h["module"], bus)
        lc = self._lc.get(key) if hasattr(self, "_lc") else None
        if lc is None:
            if not hasattr(self, "_lc"):
                self._lc = {}
            pts = self.pins[h["module"]].get(bus, []) if bus else []
            w, hh = h["outline_um"]
            lc = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)) if pts else (w / 2, hh / 2)
            self._lc[key] = lc
        (x0, y0, o) = pl[i] if pl else (h["origin_um"][0], h["origin_um"][1], h.get("orient", "R0"))
        w, hh = h["outline_um"]
        X, Y = opt(w, hh, o, lc[0], lc[1])
        return (x0 + X, y0 + Y)

    def entry(self, pl):
        """face-window entry: per core and face, the bits of the windows whose span overlaps the core (+-20 um) need a
        street of bits / ENTRY_TPU um between face and core; returns (penalty, worst [req, street, core, face])"""
        pen, worst = 0.0, None
        for i, h in enumerate(self.cores):
            r = self.rect(i, pl)
            for f in "NSEW":
                if f in "EW":
                    lo, hi = r[1] - 20, r[3] + 20
                    street = (self.W - r[2]) if f == "E" else r[0]
                else:
                    lo, hi = r[0] - 20, r[2] + 20
                    street = (self.H - r[3]) if f == "N" else r[1]
                bits = sum(b.get("width", 1) for b in self.buses.values()
                           if b["face"] == f and b["window_um"][0] < hi and b["window_um"][1] > lo)
                bits += sum(ft.get("width", 1) for ft in self.ft for (ff, w_) in
                            ((ft.get("in_face"), ft.get("in_window_um")), (ft.get("out_face"), ft.get("out_window_um")))
                            if ff == f and w_ and w_[0] < hi and w_[1] > lo)
                if bits < 64 or street > 250:
                    continue
                req = bits / ENTRY_TPU
                if street < req:
                    p = (req - street) / req * bits / 1000.0
                    pen += p
                    if worst is None or p > worst[0]:
                        worst = (round(p, 3), round(req), round(street, 1), h["inst"], f, bits)
        return pen, worst

    def win_pt(self, bname):
        b = self.buses[bname]
        m = 0.5 * sum(b["window_um"][:2])
        return dict(N=(m, self.H), S=(m, 0.0), E=(self.W, m), W=(0.0, m))[b["face"]]

    def group(self, key):
        """cores named by a core_conns key / core ref: exact inst, inst.port, or group prefix"""
        if key in self.ix:
            return [self.ix[key]], None
        a, _, port = key.rpartition(".")
        if a in self.ix:
            return [self.ix[a]], port
        g = [i for i, h in enumerate(self.cores) if h["inst"].startswith(key + ".")]
        return g, None

    # ------------------------------------------------------------------ links
    def _norm(self, inst):
        parts = inst.split(".")
        return re.sub(r"[\[\]\.]+", "_", ".".join(parts[1:]) if len(parts) > 1 else inst).strip("_")

    def _bound_links(self, L, seen):
        import bindconn as BC
        hm = set(h["module"] for h in self.cores)
        # macro owners: soft instances whose (bound-style) name prefixes fixed macros
        owners = set()
        res0, names = BC.build(self.bound, hm, set())
        bnames = set()
        for m in re.finditer(r"\n\s*\w+\s*(?:#\s*\(.*?\))?\s+(u_\w+)\s*\(", self.bound[:2000000]):
            bnames.add(m.group(1))
        fx_names = [f[4] for f in self.fixed]
        for bn in bnames:
            if bn not in names and any(bn in fx.replace(".", "_") or ("." + bn + ".") in ("." + fx) for fx in fx_names):
                owners.add(bn)
        res, names = BC.build(self.bound, hm, owners)
        # bound inst -> plan core index
        bmap = {}
        for bn, mod in names.items():
            best = None
            for i, h in enumerate(self.cores):
                if h["module"] != mod:
                    continue
                k = self._norm(h["inst"])
                if bn.endswith(k) and (best is None or len(k) > best[0]):
                    best = (len(k), i)
            if best:
                bmap[bn] = best[1]
        self.bmap = bmap
        own_pts = {}
        for o in owners:
            rs = [f for f in self.fixed if o in f[4].replace(".", "_") or ("." + o + ".") in ("." + f[4])]
            if rs:
                own_pts[o] = (sum((f[0] + f[2]) / 2 for f in rs) / len(rs), sum((f[1] + f[3]) / 2 for f in rs) / len(rs))
        soft = defaultdict(list)
        agg = {}
        for bn, ports in res.items():
            i = bmap.get(bn)
            if i is None:
                continue
            for port, tg in ports.items():
                n = len(self.pins[self.cores[i]["module"]].get(port, []))
                if not n:
                    continue
                tg = [x for x in tg if not x.startswith("soft:")] or tg
                share = max(1, round(n / len(tg)))
                for x in tg:
                    k, _, v = x.partition(":")
                    if k == "face":
                        if v in self.buses and (i, port, "face", v) not in seen:
                            seen.add((i, port, "face", v))
                            L.append(dict(a=(i, port), b=("face", v), bits=share, kind="bind"))
                    elif k == "core":
                        b2, _, p2 = v.rpartition(".")
                        j = bmap.get(b2)
                        if j is None or j == i:
                            continue
                        # one link per (core port, partner core); the reverse direction is the same wires
                        if ("cc", j, i) in seen and ("ccp", j, i, p2) in seen:
                            continue
                        kk = ("cc", i, port, j)
                        if kk in agg:
                            agg[kk]["bits"] = max(agg[kk]["bits"], share)
                            continue
                        seen.add(("cc", i, j))
                        seen.add(("ccp", i, j, port))
                        agg[kk] = dict(a=(i, port), b=("core", j, p2), bits=share, kind="bind")
                        L.append(agg[kk])
                    elif k == "macro":
                        o = v.split(".")[0]
                        if o in own_pts and ("mac", i, port, o) not in seen:
                            seen.add(("mac", i, port, o))
                            L.append(dict(a=(i, port), b=("pt", own_pts[o]), bits=share, kind="bind"))
                    elif k == "soft":
                        soft[v].append((i, port, share))
        self.soft = {k: v for k, v in soft.items() if len(set(e[0] for e in v)) > 1}
        for k, v in self.soft.items():
            for (i, port, share) in v:
                L.append(dict(a=(i, port), b=("soft", k), bits=share, kind="soft"))

    def _build_links(self):
        """link = dict(a=(core i, bus) , b=('core', j, bus|None) | ('face', bus), bits, kind)"""
        L = []
        seen = set()
        if self.bound:
            self._bound_links(L, seen)
        for key, buses in ({} if self.bound else self.cc).items():
            src, _ = self.group(key)
            for bus, dests in (buses or {}).items():
                for i in src:
                    n = len(self.pins[self.cores[i]["module"]].get(bus, []))
                    if not n:
                        continue
                    for d in dests or []:
                        k, _, v = str(d).partition(":")
                        if k == "bus" and v in self.buses:
                            kk = (i, bus, "face", v)
                            if kk not in seen:
                                seen.add(kk)
                                L.append(dict(a=(i, bus), b=("face", v), bits=n, kind="cc"))
                        elif k == "core":
                            dst, port = self.group(v)
                            dst = [j for j in dst if j != i]
                            if not dst:
                                continue
                            # partner bus on the dest: named port, else buses whose cc entry names us back
                            for j in dst:
                                pb = port
                                if pb is None:
                                    back = []
                                    for kj, bj in self.cc.items():
                                        gj, _ = self.group(kj)
                                        if j in gj:
                                            for bb, dd in (bj or {}).items():
                                                for d2 in dd or []:
                                                    k2, _, v2 = str(d2).partition(":")
                                                    if k2 == "core" and i in self.group(v2)[0]:
                                                        back.append(bb)
                                    pb = back[0] if back else None
                                kk = (min(i, j), max(i, j), bus if i < j else pb, pb if i < j else bus)
                                if kk in seen:
                                    continue
                                seen.add(kk)
                                L.append(dict(a=(i, bus), b=("core", j, pb), bits=max(1, n // len(dst)), kind="cc"))
        # internal stations: face <-> core relays and core <-> core R3 stations
        self.st = []
        for si, s in enumerate(self.stations):
            ends = []
            for ref in (s.get("launch", ""), s.get("capture", "")):
                ref = str(ref)
                if ref.startswith("core:"):
                    ref = ref[5:]
                g, port = self.group(ref)
                if g and len(g) == 1:
                    ends.append(("core", g[0], port))
                else:
                    ends.append(None)
            conn = str(s.get("conn", ""))
            face = conn[4:] if conn.startswith("bus:") and conn[4:] in self.buses else None
            bits = s.get("bits") or (self.buses[face]["width"] if face else 1)
            extra = []
            note = str(s.get("note", ""))
            m = re.search(r"relay: (.*?) (?:->|$)", note) if "relay:" in note else None
            refs = re.findall(r"(u_[\w.\[\]]+)", note.split("relay:")[1] if "relay:" in note else "")
            for r in refs:
                g, port = self.group(r)
                if g and len(g) == 1 and port:
                    extra.append((g[0], port))
            core_ends = [e for e in ends if e]
            rec = dict(si=si, face=face, bits=bits, n=len(s.get("regs_um") or []), core_ends=core_ends,
                       pins=extra or [(e[1], e[2]) for e in core_ends if e[2]],
                       from_is_face=bool(face) and abs(man(s.get("from_um", [0, 0]), self.win_pt(face))) < 1.0)
            self.st.append(rec)
            if face and core_ends:
                i, port = core_ends[0][1], core_ends[0][2]
                kk = (i, port, "face", face)
                if kk not in seen:
                    seen.add(kk)
                    L.append(dict(a=(i, port), b=("face", face), bits=bits, kind="st"))
            elif len(core_ends) == 2:
                (_, i, pa), (_, j, pb) = core_ends
                kk = ("st", min(i, j), max(i, j), pa, pb)
                if kk not in seen and i != j:
                    seen.add(kk)
                    L.append(dict(a=(i, pa), b=("core", j, pb), bits=bits, kind="st"))
        self.links = L

    def soft_pt(self, k, pl):
        v = self.soft[k]
        tot = sum(e[2] for e in v)
        xs = [(self.bus_cen(i, port, pl), w) for (i, port, w) in v]
        return (sum(p[0] * w for p, w in xs) / tot, sum(p[1] * w for p, w in xs) / tot)

    def link_pts(self, l, pl=None, cache=None):
        i, bus = l["a"]
        pa = self.bus_cen(i, bus, pl) if bus else self.bus_cen(i, None, pl)
        if l["b"][0] == "face":
            pb = self.win_pt(l["b"][1])
        elif l["b"][0] == "pt":
            pb = l["b"][1]
        elif l["b"][0] == "soft":
            if cache is not None:
                if l["b"][1] not in cache:
                    cache[l["b"][1]] = self.soft_pt(l["b"][1], pl)
                pb = cache[l["b"][1]]
            else:
                pb = self.soft_pt(l["b"][1], pl)
        else:
            _, j, bb = l["b"]
            pb = self.bus_cen(j, bb, pl) if bb else self.bus_cen(j, None, pl)
        return pa, pb

    # ------------------------------------------------------------------ blockers / legality
    def _blockers(self):
        B = []
        for (r, k, w) in self.bands:
            B.append((r[0], r[1], r[2], r[3], "band:" + k))
        for f in self.ft:
            # station regs with their bit-site cloud
            # check.py geometry: stage j>0 cells sit at bit_sites_um[j-1][bit] with size bit_site_cell_um; without
            # bit sites, at regs_um[j] (centre).  Block every bit-site cloud (+cell) and every reg point.
            bs = f.get("bit_sites_um") or []
            cw, ch = (f.get("bit_site_cell_um") or [2.0, 2.0])[:2]
            for k, pts in enumerate(bs):
                if not pts:
                    continue
                xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                B.append((min(xs) - 1, min(ys) - 1, max(xs) + cw + 1, max(ys) + ch + 1, "ftreg:%s:s%d" % (f["name"], k + 1)))
            for k, r in enumerate(f.get("regs_um") or []):
                B.append((r[0] - 2, r[1] - 2, r[0] + 2, r[1] + 2, "ftreg:%s:r%d" % (f["name"], k)))
            # ft lane: window -> regs -> window polyline, each leg as a band of the window half-width (min 5 um)
            iw, ow = f.get("in_window_um"), f.get("out_window_um")
            if not (iw and ow):
                continue

            def wp(face, w):
                m = 0.5 * (w[0] + w[1])
                return dict(N=(m, self.H), S=(m, 0.0), E=(self.W, m), W=(0.0, m))[face]
            hw = max(5.0, 0.5 * max(iw[1] - iw[0], ow[1] - ow[0]))
            pts = [wp(f["in_face"], iw)] + [tuple(r) for r in (f.get("regs_um") or [])] + [wp(f["out_face"], ow)]
            for (ax, ay), (cx, cy) in zip(pts, pts[1:]):
                # L leg: horizontal at ay then vertical at cx
                B.append((min(ax, cx) - hw, ay - hw, max(ax, cx) + hw, ay + hw, "ftlane:" + f["name"]))
                B.append((cx - hw, min(ay, cy) - hw, cx + hw, max(ay, cy) + hw, "ftlane:" + f["name"]))
        for fx in self.fixed:
            B.append((fx[0], fx[1], fx[2], fx[3], "macro:" + fx[4]))
        tx, ty = self.tap
        B.append((tx - 1, ty - 1, tx + 1, ty + 1, "tap"))
        # clock.added_taps (grid+explicit): taps.grid_explicit_sites rejects a tap strictly inside a core box grown
        # by schema.TAP_CLEAR_UM (8.64) -> fixed blocker of that half-size
        for p in (self.t.get("clock", {}) or {}).get("added_taps", []) or []:
            ax, ay = map(float, p["xy"])
            B.append((ax - 9.2, ay - 9.2, ax + 9.2, ay + 9.2, "addtap:" + p["name"]))  # 8.64 + track offset margin
        return B

    def current(self):
        return [(h["origin_um"][0], h["origin_um"][1], h.get("orient", "R0")) for h in self.cores]

    def legality_params(self):
        """edge margin / gap from the current placement (never tighter than the current plan, never above B34)"""
        pl = self.current()
        R = [self.rect(i, pl) for i in range(len(self.cores))]
        edge = min([min(r[0], r[1], self.W - r[2], self.H - r[3]) for r in R] + [17.28])
        gaps = []
        for i in range(len(R)):
            for j in range(i + 1, len(R)):
                a, b = R[i], R[j]
                dx = max(b[0] - a[2], a[0] - b[2])
                dy = max(b[1] - a[3], a[1] - b[3])
                gaps.append(max(dx, dy))
        gap = min(gaps + [34.56]) if gaps else 34.56
        return max(0.0, round(edge, 3)), max(4.32, round(gap, 3))

    def violations(self, pl, edge, gap, ignore=()):
        v = []
        R = [self.rect(i, pl) for i in range(len(self.cores))]
        for i, r in enumerate(R):
            if r[0] < edge - 1e-6 or r[1] < edge - 1e-6 or r[2] > self.W - edge + 1e-6 or r[3] > self.H - edge + 1e-6:
                v.append((i, "outline"))
            for b in self.blk:
                if b[4] in ignore:
                    continue
                if r[0] < b[2] and b[0] < r[2] and r[1] < b[3] and b[1] < r[3]:
                    v.append((i, b[4]))
            for j in range(i + 1, len(R)):
                a, b = r, R[j]
                if a[0] - gap < b[2] - 1e-6 and b[0] < a[2] + gap - 1e-6 and a[1] - gap < b[3] - 1e-6 and b[1] < a[3] + gap - 1e-6:
                    v.append((i, "gap:%s" % self.cores[j]["inst"]))
        return v

    # ------------------------------------------------------------------ scores
    def bitmm(self, pl):
        c = {}
        return sum(l["bits"] * man(*self.link_pts(l, pl, c)) for l in self.links) / 1000.0

    def station_check(self, pl):
        """per station: worst-bit distance window/core -> core pins, stages needed vs sited (EQ: needed <= sited)"""
        bad = []
        for s in self.st:
            if s["face"] and s["pins"]:
                a = self.win_pt(s["face"])
                pts = [p for (i, bus) in s["pins"] for p in self.pin_pts(i, bus, pl)]
                if not pts:
                    continue
                d = max(man(a, p) for p in pts)
            elif len(s["core_ends"]) == 2:
                (_, i, pa), (_, j, pb) = s["core_ends"]
                A = self.pin_pts(i, pa, pl) if pa else [self.bus_cen(i, None, pl)]
                Bp = self.pin_pts(j, pb, pl) if pb else [self.bus_cen(j, None, pl)]
                if not A or not Bp:
                    continue
                d = max(man(a, b) for a in A[:: max(1, len(A) // 16)] for b in Bp[:: max(1, len(Bp) // 16)])
            else:
                continue
            need = max(0, math.ceil(d / REACH_STEP) - 1)
            if need > s["n"]:
                bad.append((s["si"], round(d), need, s["n"]))
        return bad

    def supply_maps(self, pl, b=10.8, with_cores=True):
        import numpy as np
        nx, ny = int(math.ceil(self.W / b)), int(math.ceil(self.H / b))
        obs = {L: np.zeros((ny, nx)) for L in LORDER}
        rects = []
        if with_cores:
            for i, h in enumerate(self.cores):
                rects.append((self.rect(i, pl), h.get("obs_max") or "M5"))
        for fx in self.fixed:
            rects.append(((fx[0], fx[1], fx[2], fx[3]), "M4"))
        xs = np.arange(nx) * b
        ys = np.arange(ny) * b
        for (r, top) in rects:
            cx = np.clip(np.minimum(xs + b, r[2]) - np.maximum(xs, r[0]), 0, None) / b
            cy = np.clip(np.minimum(ys + b, r[3]) - np.maximum(ys, r[1]), 0, None) / b
            c = np.outer(cy, cx)
            for L in LORDER[: LORDER.index(top) + 1]:
                obs[L] = np.maximum(obs[L], c)
        open_ = 1 - np.maximum.reduce([obs[L] for L in LORDER])
        sup = {}
        for L in HL + VL:
            s = b / PITCH[L] * (1 - DER[L]) * (1 - obs[L])
            below = LORDER[LORDER.index(L) - 1]
            if L != "M2":
                s = s * (1 - 0.5 * obs[below])
            if L in ("M2", "M3", "M4", "M5"):
                s = s * (1 - CELL_FILL * open_)
            sup[L] = s
        return sup, nx, ny

    def cut_table(self, pl, b=10.8, with_cores=True, demand=None):
        """full-outline cut lines: V cut at x (bits crossing W<->E vs H tracks), H cut at y (bits S<->N vs V tracks)"""
        import numpy as np
        sup, nx, ny = self.supply_maps(pl, b, with_cores)
        H_tr = sup["M2"] + sup["M4"] + sup["M6"]       # per bin, tracks crossing a vertical line in that bin
        V_tr = sup["M3"] + sup["M5"] + sup["M7"]
        segs = demand if demand is not None else self.demand_segments(pl)
        A = np.array([[p[0], p[1], q[0], q[1], bits] for (p, q, bits) in segs] or [[0, 0, 0, 0, 0]], dtype=float)
        x0, x1 = np.minimum(A[:, 0], A[:, 2]), np.maximum(A[:, 0], A[:, 2])
        y0, y1 = np.minimum(A[:, 1], A[:, 3]), np.maximum(A[:, 1], A[:, 3])
        cx = np.arange(1, nx) * b
        cy = np.arange(1, ny) * b
        dV = ((x0[:, None] < cx[None, :]) & (cx[None, :] < x1[:, None])) * A[:, 4:5]
        dH = ((y0[:, None] < cy[None, :]) & (cy[None, :] < y1[:, None])) * A[:, 4:5]
        dV, dH = dV.sum(0), dH.sum(0)
        sV, sH = H_tr[:, 1:nx].sum(0), V_tr[1:ny, :].sum(1)
        res = {"V": [(round(float(x), 1), int(d), int(round(sv)), float(d / sv) if sv else 9.0)
                     for x, d, sv in zip(cx, dV, sV)],
               "H": [(round(float(y), 1), int(d), int(round(sv)), float(d / sv) if sv else 9.0)
                     for y, d, sv in zip(cy, dH, sH)]}
        return res

    def fixed_segments(self):
        """ft slot traffic: in window -> regs -> out window (fixed, arrangement-independent)"""
        S = []
        for f in self.ft:
            iw, ow = f.get("in_window_um"), f.get("out_window_um")
            if not (iw and ow):
                continue

            def wp(face, w):
                m = 0.5 * (w[0] + w[1])
                return dict(N=(m, self.H), S=(m, 0.0), E=(self.W, m), W=(0.0, m))[face]
            pts = [wp(f["in_face"], iw)] + [tuple(r) for r in (f.get("regs_um") or [])] + [wp(f["out_face"], ow)]
            for a, c in zip(pts, pts[1:]):
                S.append((a, c, f.get("width", 1)))
        # face buses with no core link: soft traffic to the fixed-macro centroid (type centre without macros)
        linked = set(l["b"][1] for l in self.links if l["b"][0] == "face")
        if self.fixed:
            cen = (sum((f[0] + f[2]) / 2 for f in self.fixed) / len(self.fixed),
                   sum((f[1] + f[3]) / 2 for f in self.fixed) / len(self.fixed))
        else:
            cen = (self.W / 2, self.H / 2)
        for bn, b in self.buses.items():
            if bn not in linked and b.get("width", 1) >= 8:
                S.append((self.win_pt(bn), cen, b["width"]))
        return S

    def demand_segments(self, pl):
        S = list(self.fixed_segments())
        cc = {}
        for l in self.links:
            a, c = self.link_pts(l, pl, cc)
            S.append((a, c, l["bits"]))
        return S

    def worst_cut(self, pl):
        ct = self.cut_table(pl)
        wv = max(ct["V"], key=lambda r: r[3]) if ct["V"] else (0, 0, 1, 0)
        wh = max(ct["H"], key=lambda r: r[3]) if ct["H"] else (0, 0, 1, 0)
        return wv, wh

    def intrinsic(self):
        """best case per cut line: fixed ft traffic + every core link at its best side (cores may sit on either
        side; core-core links can always be kept on one side) vs supply with no hard core on the line"""
        segs_fixed = self.fixed_segments()
        sup_ct = self.cut_table(self.current(), with_cores=False, demand=segs_fixed)
        # core->face links: a core on the face's side need not cross; lower bound adds nothing for them unless the
        # face window spans the cut (never for full lines). So the LB is the fixed traffic.
        wv = max(sup_ct["V"], key=lambda r: r[3])
        wh = max(sup_ct["H"], key=lambda r: r[3])
        return wv, wh

    # ------------------------------------------------------------------ route_supply
    def plan_with(self, pl, resite=True):
        t = copy.deepcopy(self.t)
        for i, (x, y, o) in enumerate(pl):
            h0 = self.cores[i]
            t["hard_cores"][i]["origin_um"] = [round(x, 3), round(y, 3)]
            t["hard_cores"][i]["orient"] = o
        if resite:
            self._resite(t, pl)
        return t

    def _resite(self, t, pl):
        import ts_relay_event as TR
        cur = self.current()
        for s in self.st:
            e = t["internal_stations"][s["si"]]
            n = s["n"]
            if s["face"] and s["pins"]:
                a = self.win_pt(s["face"])
                pts = [p for (i, bus) in s["pins"] for p in self.pin_pts(i, bus, pl)]
                if not pts:
                    continue
                b = max(pts, key=lambda p: man(a, p))
                if s["from_is_face"]:
                    e["from_um"], e["to_um"] = [round(a[0], 3), round(a[1], 3)], [round(b[0], 3), round(b[1], 3)]
                    e["regs_um"] = TR.sites(t, a, b, n) if n else []
                else:
                    e["from_um"], e["to_um"] = [round(b[0], 3), round(b[1], 3)], [round(a[0], 3), round(a[1], 3)]
                    e["regs_um"] = TR.sites(t, b, a, n) if n else []
            elif len(s["core_ends"]) == 2:
                (_, i, pa), (_, j, pb) = s["core_ends"]
                # shift endpoints and regs with the cores (rigid move of each end), then re-site regs on the L
                def mv(pt, k):
                    (x0, y0, o0), (x1, y1, o1) = cur[k], pl[k]
                    h = self.cores[k]
                    w, hh = h["outline_um"]
                    lx, ly = opt(w, hh, o0, pt[0] - x0, pt[1] - y0)     # back to R0 local (opt is an involution)
                    X, Y = opt(w, hh, o1, lx, ly)
                    return [round(x1 + X, 3), round(y1 + Y, 3)]
                a = mv(e["from_um"], i)
                b = mv(e["to_um"], j)
                e["from_um"], e["to_um"] = a, b
                if n and (cur[i] != pl[i] or cur[j] != pl[j]):
                    e["regs_um"] = TR.sites(t, a, b, n)
        # core clock taps move with their core
        taps = (t.get("clock") or {}).get("taps") or []
        for tp in taps:
            if tp.get("kind") != "core":
                continue
            g, port = self.group(tp["name"])
            if len(g) != 1:
                continue
            k = g[0]
            (x0, y0, o0), (x1, y1, o1) = cur[k], pl[k]
            if (x0, y0, o0) == (x1, y1, o1):
                continue
            h = self.cores[k]
            w, hh = h["outline_um"]
            lx, ly = opt(w, hh, o0, tp["xy"][0] - x0, tp["xy"][1] - y0)
            X, Y = opt(w, hh, o1, lx, ly)
            tp["xy"] = [round(x1 + X, 3), round(y1 + Y, 3)]

    def rs(self, pl, cfg, conns, resite=True):
        t = self.plan_with(pl, resite)
        r = RS.analyze_type(self.name, t, DIE_DIR, REPO, conns, cfg)
        if r is None:
            return None
        r.pop("_maps", None)
        return r


def rs_cfg():
    cfg = dict(RS.DEFAULTS, derate=dict(RS.DERATE))
    cfg.update(signed_modules=None, core_fill={}, views={}, kit_views={})
    try:
        cfg["views"] = json.loads((REPO / "tools/die_plan/route_supply_views.json").read_text()).get("views", {})
    except (OSError, ValueError):
        pass
    try:
        cfg["kit_views"] = json.loads((REPO / "tools/die_plan/route_supply_kit_views.json").read_text()).get("s81", {})
    except (OSError, ValueError, AttributeError):
        pass
    return cfg


def load(plan_path):
    P = RS.read_json(plan_path)
    conns = RS.load_conns(DIE_DIR, None, DIE_DIR, [])
    return P, conns


def rs_summary(r):
    if r is None:
        return {}
    w = r["worst"]
    return dict(p99=w["p99"], region=w["region"], dir=w["dir"], hot=r["hot_bins"],
                regions={k: v.get("p99") for k, v in r["regions"].items()})
