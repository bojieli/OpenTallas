#!/usr/bin/env python3
"""DIE-QC-97 HC-CLAND 11-11: re-runnable derivation of the hc1/hc2 landing-ring form from the CURRENT plan geometry.

Use it after any core / band move (e.g. VIS-TRIAGE-QC's clean-slate placement round).  It reads the plan as it is now
and never hard-codes a rect.  Running it twice gives the same output: the second run is byte-identical.

1. Ring-flop strip rows: budgets.cland_strip_rows_types[base] = ROWS for each base in BASES (sle_hc1 slw_hc1 sle_hc2
   slw_hc2).  gen_phys._cland_strip_rows then exports OT_CLAND_STRIP_ROWS=3 for every type of those bases.  A base
   already set to ROWS is left alone; a base set to another value -> SystemExit (merge by hand).
2. b_hw_i face home, for each type of those bases.  A b_hw_i band "off home" has its face-crossing demand above its
   strip cap, or more than half its bits outside the band's span along the face.  Such a band is re-sited with the same
   size on its own face:
   - Candidates are the face-parallel offsets on the 2.16-um grid, from the 17.28-um margin.  They are ranked by
     crossing demand, then inset from the face, then distance from the window-centred offset.
   - The first candidate is taken that is clear of every planning obstacle (cland_band_fit.obstacles: macros/cores +
     clearance, keepouts, die islands, reserved clock sites, ft station sites, PHY supply, START/status groups) and
     within the 402.84-um pin reach.
   - Other ring bands may be in the way, if each one can be re-sited.  Each displaced band keeps its size and its own
     face, and takes the legal rect with the least Manhattan shift from its old rect (2.16-um grid).  Legal means:
     clear of the obstacles, 2.16 um from every other band, in reach, and within its own strip crossing cap.
   - Collector reset-relay sites are not obstacles unless budgets.cland_avoid_reset_types names the type (the compose
     rule; the old bands overlap them too).
   - Each moved band gets rect_um, max_pin_to_band_hop_um, resized_from_um (its old rect) and a resize note.  Every
     other field, band and type stays byte-identical.
   - No legal home -> SystemExit (no partial plan).
On the 11-11 lineage (aace4c2668fc / 886a8ffae774) this reproduces HC1-STRIP exactly.  Four hc1 types get
b_hw_i [108.528,17.28,380.496,62.64] -> [17.28,17.28,289.248,62.64] and rs_n1 [17.28,17.28,69.12,106.368] ->
[17.28,64.8,69.12,153.888].  All hc2 b_hw_i bands are already home.
    derive_hc_cland_1111.py PLAN.json OUT.json [--rows 3] [--bases sle_hc1,slw_hc1,sle_hc2,slw_hc2]
       -> prints {keys, moved, sha256_in, sha256_out}; OUT keeps PLAN's JSON style (compact / indent=1)
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))

ROWS = 3
BASES = ("sle_hc1", "slw_hc1", "sle_hc2", "slw_hc2")
BUS = "b_hw_i"
G = 2.16
MARGIN = 17.28
REACH = 405 - 2.16
MAX_INSET_STEPS = 20
MAX_SHIFT_STEPS = 120
OFF_WINDOW = 0.5
NOTE = "DIE-QC-97 HC-CLAND 11-11: derived face home (b_hw_i over its own pins; displaced bands least-shift, same face)"


def _ov(a, o, pad=0.0):
    return (min(a[2], o[2] + pad) > max(a[0], o[0] - pad) + 1e-6 and
            min(a[3], o[3] + pad) > max(a[1], o[1] - pad) + 1e-6)


def _r(v):
    return round(v, 6)


class TypeCtx:
    def __init__(self, raw, plan_obj, tn):
        import clock_landing_plan as C
        import cland_band_fit as F
        self.C, self.F = C, F
        self.raw, self.P, self.tn = raw, plan_obj, tn
        self.t = raw["partition_types"][tn]
        self.lc = self.t["clock"]["landing_contract"]
        self.w, self.h = self.t["outline_um"]
        tree = self.lc.get("collector_tree")
        avoid = C._reset_sites_for_type(raw, tn, tree, self.lc.get("base_type"))
        self.skip = set() if avoid else {tuple(r) for r in C.reset_site_rects(tree)}

    def movable(self, k):
        b = self.lc["bands"][k]
        return (k != BUS and not k.startswith("monitor_") and b.get("rect_um") and not b.get("hard_core")
                and not any(x in b for x in ("rects_um", "ff_rect_um", "freg_rect_um", "native_role_banks"))
                and self.C._has_type_geom(self.t, k))

    def fixed_obstacles(self, bands):
        """planning obstacles except ring bands and (compose rule) reset-relay sites"""
        lc = copy.deepcopy(self.lc)
        lc["bands"] = {}
        return [o for o in self.F.obstacles(self.t, self.tn, self.P, None, lc, None) if tuple(o) not in self.skip]

    def legal(self, bus, rect, fixed, others):
        if rect[0] < MARGIN - 1e-6 or rect[1] < MARGIN - 1e-6 or rect[2] > self.w - MARGIN + 1e-6 or \
                rect[3] > self.h - MARGIN + 1e-6:
            return None
        px, py = self.C._bus_xy(self.t, bus)
        hop = max(abs(x - px) + abs(y - py) for x in (rect[0], rect[2]) for y in (rect[1], rect[3]))
        if hop > REACH + 1e-6:
            return None
        dm, cap = self.C.face_crossing(self.t, bus, rect, int(self.lc["bands"][bus]["width"]))
        if dm > cap + 1e-6:
            return None
        if any(_ov(rect, o) for o in fixed) or any(_ov(rect, o, G - 1e-3) for o in others):
            return None
        return _r(hop)

    def off_home(self):
        b = self.lc["bands"].get(BUS)
        if not b or not b.get("rect_um") or not self.C._has_type_geom(self.t, BUS):
            return False
        dm, cap = self.C.face_crossing(self.t, BUS, b["rect_um"], int(b["width"]))
        return dm > cap + 1e-6 or dm > OFF_WINDOW * int(b["width"])

    def home_candidates(self):
        b = self.lc["bands"][BUS]
        r = b["rect_um"]
        geo = self.C._bus_geom(self.t, BUS)
        f, (lo, hi) = geo["face"], geo["window_um"]
        along = self.h if f in "EW" else self.w
        L = (r[3] - r[1]) if f in "EW" else (r[2] - r[0])
        D = (r[2] - r[0]) if f in "EW" else (r[3] - r[1])
        ideal = min(max(MARGIN, (lo + hi - L) / 2), along - MARGIN - L)
        out = []
        n = int((along - 2 * MARGIN - L) / G + 1e-6)
        for k in range(n + 1):
            s = MARGIN + k * G
            for j in range(MAX_INSET_STEPS + 1):
                i = MARGIN + j * G
                rect = ([i, s, i + D, s + L] if f == "W" else [self.w - i - D, s, self.w - i, s + L] if f == "E" else
                        [s, i, s + L, i + D] if f == "S" else [s, self.h - i - D, s + L, self.h - i])
                rect = [_r(v) for v in rect]
                dm, _ = self.C.face_crossing(self.t, BUS, rect, int(b["width"]))
                out.append((round(dm, 3), j, abs(s - ideal), rect))
        out.sort(key=lambda c: c[:3])
        return [c[3] for c in out]

    def resite(self, k, fixed, others):
        r = self.lc["bands"][k]["rect_um"]
        best = None
        for dx in range(-MAX_SHIFT_STEPS, MAX_SHIFT_STEPS + 1):
            for dy in range(-MAX_SHIFT_STEPS, MAX_SHIFT_STEPS + 1):
                cost = abs(dx) + abs(dy)
                if best is not None and cost >= best[0]:
                    continue
                rect = [_r(r[0] + dx * G), _r(r[1] + dy * G), _r(r[2] + dx * G), _r(r[3] + dy * G)]
                hop = self.legal(k, rect, fixed, others)
                if hop is not None and (best is None or (cost, rect) < best[:2]):
                    best = (cost, rect, hop)
        return best

    def derive(self):
        bands = self.lc["bands"]
        fixed = self.fixed_obstacles(bands)
        for rect in self.home_candidates():
            in_way = sorted(k for k, o in bands.items() if k != BUS and o.get("rect_um") and _ov(rect, o["rect_um"], G - 1e-3))
            if any(not self.movable(k) for k in in_way):
                continue
            stay = [o["rect_um"] for k, o in bands.items() if k != BUS and k not in in_way and o.get("rect_um")]
            stay += [rr for k, o in bands.items() if k != BUS and o.get("rects_um") for rr in o["rects_um"]]
            hop = self.legal(BUS, rect, fixed, stay)
            if hop is None:
                continue
            new = {BUS: (rect, hop)}
            placed = stay + [rect]
            ok = True
            for k in sorted(in_way, key=lambda k: (-int(bands[k].get("width") or 0), k)):
                got = self.resite(k, fixed, placed)
                if got is None:
                    ok = False
                    break
                new[k] = (got[1], got[2])
                placed.append(got[1])
            if ok:
                return new
        raise SystemExit(f"HC-CLAND: {self.tn}: no legal face home for {BUS} {bands[BUS]['rect_um']}")


def apply(raw, rows=ROWS, bases=BASES):
    types = sorted(t for t in raw.get("partition_types", {}) if t.split("__")[0] in bases)
    if not types:
        raise SystemExit(f"HC-CLAND: plan has no type of {bases}")
    bud = raw.setdefault("budgets", {})
    per = bud.get("cland_strip_rows_types")
    per = {} if per is None else per
    clash = {k: per[k] for k in list(bases) + types if k in per and per[k] != rows}
    if clash:
        raise SystemExit(f"HC-CLAND: cland_strip_rows_types already sets {clash} (merge by hand)")
    import schema as S
    plan_obj = S.Plan(raw) if (raw.get("die") or {}).get("pg", {}).get("domains") and raw.get("partitions") else None
    moved = {}
    for tn in types:
        if not (raw["partition_types"][tn].get("clock") or {}).get("landing_contract"):
            continue
        ctx = TypeCtx(raw, plan_obj, tn)
        if not ctx.off_home():
            continue
        new = ctx.derive()
        for k, (rect, hop) in sorted(new.items()):
            b = ctx.lc["bands"][k]
            moved.setdefault(tn, {})[k] = dict(old=list(b["rect_um"]), new=rect, hop_um=hop)
            b["resized_from_um"] = list(b["rect_um"])
            b["rect_um"] = rect
            b["max_pin_to_band_hop_um"] = hop
            b["resize"] = NOTE
    for b in bases:
        per[b] = rows
    bud["cland_strip_rows_types"] = per
    return raw, moved


def _dump(src, obj):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p, indent=1) + "\n"):
        if f(json.loads(src)).encode() == src:
            return f(obj).encode()
    return (json.dumps(obj, separators=(",", ":")) + "\n").encode()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--rows", type=int, default=ROWS)
    p.add_argument("--bases", default=",".join(BASES))
    a = p.parse_args()
    src = Path(a.input).read_bytes()
    bases = tuple(x for x in a.bases.split(",") if x)
    raw, moved = apply(json.loads(src), a.rows, bases)
    out = _dump(src, raw)
    Path(a.output).write_bytes(out)
    print(json.dumps({"keys": {b: a.rows for b in bases}, "moved": moved,
                      "sha256_in": hashlib.sha256(src).hexdigest(), "sha256_out": hashlib.sha256(out).hexdigest()}))


if __name__ == "__main__":
    main()
