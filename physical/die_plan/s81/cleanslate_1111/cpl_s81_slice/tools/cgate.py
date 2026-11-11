#!/usr/bin/env python3
"""CPL-S81-SLICE composer gate (DS85-COMPOSE-1111 legality, copied rule for rule from
physical/die_plan/s81/compose_cleanslate_1111.py legality()/phys()): per type, findings over hard_cores + lef
contents: in_outline, overlap, street (abutted 0 or >= 34.56), sites (clock tap, plain taps, ft regs, internal
station regs, core taps of other cores) strictly under a core box; plus the kit tap rule
(taps.grid_explicit_taps: added tap load <= cap, radius <= 1.10 x tap_radius_um, non-empty) and
gen_phys.core_tap_pins inside the outline.  A candidate passes when it has no finding absent from the plan."""
import copy
import os
import sys
from pathlib import Path

REPO = Path(os.environ.get("CPL_REPO", "/srv/opentallas-scratch3/claude/cpl-s81-slice/repo"))
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
EPS = 1e-6
GAP = 34.56


def box(hc):
    (x, y), (dx, dy), (w, h) = hc["origin_um"], hc.get("track_offset_um", [0.0, 0.0]), hc["outline_um"]
    return (x + dx, y + dy, x + dx + w, y + dy + h)


def core_tap_inst(name, insts):
    for i in sorted(insts, key=len, reverse=True):
        if name == i or name.startswith(i + "."):
            return i
    return None


def legality(t, gap=GAP, edge=0.0):
    W, H = t["outline_um"]
    cores = [(e["inst"], box(e)) for k in ("hard_cores", "contents") for e in t.get(k) or []
             if "origin_um" in e and "outline_um" in e and (k == "hard_cores" or e.get("lef"))]
    f = {}
    for i, (x0, y0, x1, y1) in cores:
        if x0 < edge - EPS or y0 < edge - EPS or x1 > W - edge + EPS or y1 > H - edge + EPS:
            f[("in_outline", i)] = "%s outside" % i
    cs = sorted(cores, key=lambda c: c[1][0])
    for a in range(len(cs)):
        ia, A = cs[a]
        for b in range(a + 1, len(cs)):
            ib, Bx = cs[b]
            if Bx[0] - A[2] >= gap - EPS:
                break
            gx = max(Bx[0] - A[2], A[0] - Bx[2])
            gy = max(Bx[1] - A[3], A[1] - Bx[3])
            key = tuple(sorted((ia, ib)))
            if gx < -EPS and gy < -EPS:
                f[("overlap",) + key] = "%s / %s overlap" % key
                continue
            g = max(gx, gy)
            if EPS < g < gap - EPS:
                f[("street",) + key] = "%s / %s gap %.3f" % (key + (g,))
    pts = []
    ck = t.get("clock") or {}
    if ck.get("tap_um"):
        pts.append(("clock.tap_um", ck["tap_um"]))
    pts += [("tap " + tp["name"], tp["xy"]) for tp in ck.get("taps", []) or [] if tp.get("kind") != "core"]
    for s in t.get("ft_slots") or []:
        pts += [("ft %s reg %d" % (s["name"], k), r) for k, r in enumerate(s.get("regs_um") or [])]
    for k, s in enumerate(t.get("internal_stations") or []):
        pts += [("istation %s reg %d" % (s.get("conn", k), j), r) for j, r in enumerate(s.get("regs_um") or [])]
    hcs = {e["inst"] for e in t.get("hard_cores") or []}
    for tp in ck.get("taps", []) or []:
        if tp.get("kind") == "core":
            pts.append(("core tap %s|%s" % (tp["name"], core_tap_inst(tp["name"], hcs)), tp["xy"]))
    for nm, (px, py) in pts:
        own = nm.split("|")[1] if "|" in nm else None
        for i, (x0, y0, x1, y1) in cores:
            if i != own and x0 + EPS < px < x1 - EPS and y0 + EPS < py < y1 - EPS:
                f[("site", nm.split("|")[0], i)] = "%s under %s" % (nm.split("|")[0], i)
    return f


class Gate:
    def __init__(self, plan_path, tn, t0):
        self.tn = tn
        self.base = set(legality(t0))
        self.P = None
        self.plan_path = plan_path
        self.t0 = t0
        self.tap0 = self.taps(t0)

    def new(self, t):
        f = legality(t)
        return [v for k, v in f.items() if k not in self.base]

    def taps(self, t):
        """None = pass; else the error text (kit tap rule as the composer's phys())."""
        import schema as S
        import gen_phys as GP
        import taps as TP
        if self.P is None:
            self.P = S.Plan(S.load(str(self.plan_path)), Path(self.plan_path))
        keep = self.P.types[self.tn]
        self.P.types[self.tn] = copy.deepcopy(t)
        try:
            if hasattr(TP, "_clear_density_cache"):
                TP._clear_density_cache()
            W, H = t["outline_um"]
            for port, x, y in GP.core_tap_pins(self.P, self.tn):
                if not (-EPS <= x <= W + EPS and -EPS <= y <= H + EPS):
                    return "core tap %s outside" % port
            if (t.get("clock") or {}).get("tap_mode") == "grid+explicit":
                TP.grid_explicit_taps(self.P, self.tn)
            return None
        except Exception as e:  # noqa: BLE001
            return "%s: %s" % (type(e).__name__, e)
        finally:
            self.P.types[self.tn] = keep

    def ok(self, t, taps=True):
        if self.new(t):
            return False
        if taps and self.tap0 is None:
            return self.taps(t) is None
        return True
