#!/usr/bin/env python3
"""KV-MP1-R3: D-KV-MP1 items (1)-(3) as a deterministic POST-PASS on the KV die_plan.json (candidate revision, not the
plan of record).  The generator path (physical/die_plan/qwen_kvsys/build_plan.py) was not changed (too slow to change
inside this lane); the post-pass is reproducible: same input plan -> same output.

    python3 -I kv_mp1_postpass.py TOOLDIR PLAN_IN PLAN_OUT REPORT.json

TOOLDIR = tools/die_plan of the master-plan branch (schema.py, master_plan.py, infra_sites.py).

(1) WINDOWS: every port touching a KV ft slot gets window width >= bits x f(layer) (f = 0.1067 M4/M5, 0.1422 M6/M7,
    0.1532 M8/M9; max over the port's layers), centred on its (snapped) centre, kept inside the face; the ft slot
    declares in_window_um / out_window_um (type frame) from its first instance (replica disagreement reported).
(2)+(3) SNAP: every straight run of a lane (consecutive ports on N/S faces = vertical run, E/W = horizontal) shares one
    route coordinate; it is moved (minimum displacement) so the band [c - w/2, c + w/2] lies inside a FULL-SPAN glue
    strip (no hard core across the partition in the route direction) with 4.32-um margin in EVERY straight-slot
    partition of the run (hub row ft ports leave the partition-face corners for the glue-column lattice of the rows
    above/below because the run intersection includes their column).  The ft slot bit_sites_um shift with it.
    Runs whose band fits no common strip are listed (split candidates: > 668 b -> 2 x 528, NOT applied here).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

tool, pin, pout, rep = sys.argv[1:5]
sys.path.insert(0, tool)
import schema as S  # noqa: E402
import master_plan as MP  # noqa: E402

F = {"M4": 0.1067, "M5": 0.1067, "M6": 0.1422, "M7": 0.1422, "M8": 0.1532, "M9": 0.1532}
MARGIN = 4.32
MIN_WIN = 8.64                   # >= 2 PG-lattice pitches so a moved window always keeps tracks off the M8/M9 PG stripes
raw = json.loads(Path(pin).read_text())
P = S.Plan(S.load(pin), Path(pin))
ports = {p["id"]: p for p in raw["ports"]}
OPPF = {"N": "S", "S": "N", "E": "W", "W": "E"}


def slot_of(end):
    part, bus = end["part"], end["bus"]
    if part not in P.parts or not (bus.endswith("_i") or bus.endswith("_o")):
        return None
    s = P.slot(part, bus[:-2])
    return (part, s, bus[-1]) if s is not None else None


def width_of(pr):
    return max(F.get(L, 0.1422) for L in pr["layers"]) * int(pr["width"])


strip_cache = {}


def strips(part, vert):
    """full-span free intervals (die frame) across the partition: x-intervals (vert) or y-intervals."""
    k = (part, vert)
    if k in strip_cache:
        return strip_cache[k]
    x0, y0, x1, y1 = P.rect(part)
    bl = [c for c in MP.part_blockers(P, part, {}) if c[4] != "island"]
    lo, hi = (x0, x1) if vert else (y0, y1)
    occ = sorted((c[0], c[2]) if vert else (c[1], c[3]) for c in bl)
    out, cur = [], lo
    for a, b in occ:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if hi > cur:
        out.append((cur, hi))
    strip_cache[k] = out
    return out


def allowed(part, vert, w):
    return [(a + w / 2 + MARGIN, b - w / 2 - MARGIN) for a, b in strips(part, vert) if b - a - 2 * MARGIN >= w]


def intersect(A, B):
    out = []
    for a0, a1 in A:
        for b0, b1 in B:
            lo, hi = max(a0, b0), min(a1, b1)
            if lo <= hi + 1e-9:
                out.append((lo, hi))
    return out


def nearest(ivs, c):
    best = None
    for lo, hi in ivs:
        v = min(max(c, lo), hi)
        if best is None or abs(v - c) < abs(best - c):
            best = v
    return best


def centre(pr):
    return (pr["window_um"][0] + pr["window_um"][1]) / 2.0


new_c = {}
runs_moved, runs_ok, runs_nofit, nofit = 0, 0, 0, []
disp = []
for lid, ln in P.lanes.items():
    ids = [q for q in ln["ports"] if q in ports]
    # straight runs: maximal chains of consecutive ports on parallel faces joined by straight slots
    run = []

    def flush(run):
        global runs_moved, runs_ok, runs_nofit
        if not run:
            return
        f = ports[run[0]]["face"]
        vert = f in "NS"
        w = max(width_of(ports[q]) for q in run)
        parts = []
        for q in run:
            for side in ("src", "dst"):
                so = slot_of(ports[q][side])
                if so and so[1]["in_face"] == OPPF[so[1]["out_face"]] and (so[1]["in_face"] in "NS") == vert:
                    parts.append(so[0])
        parts = sorted(set(parts))
        if not parts:
            return
        A = None
        for part in parts:
            al = allowed(part, vert, w)
            A = al if A is None else intersect(A, al)
        cs = [centre(ports[q]) for q in run]
        c0 = sum(cs) / len(cs)
        if not A:
            runs_nofit += 1
            nofit.append(dict(lane=lid, ports=run, bits=int(ports[run[0]]["width"]), band_um=round(w, 2),
                              parts=parts, coord=round(c0, 2), axis="x" if vert else "y"))
            return
        c = nearest(A, c0)
        if all(abs(x - c) < 1e-3 for x in cs):
            runs_ok += 1
        else:
            runs_moved += 1
            disp.append(abs(c - c0))
        for q in run:
            new_c[q] = c

    for q in ids:
        pr = ports[q]
        if run and (pr["face"] in "NS") != (ports[run[-1]]["face"] in "NS"):
            flush(run)
            run = []
        # a turning slot between run[-1] and q breaks the run
        if run:
            so = slot_of(pr["src"])
            if so and so[1]["in_face"] != OPPF[so[1]["out_face"]]:
                flush(run)
                run = []
        run.append(q)
    flush(run)

# (1) windows on every ft-slot port; apply snapped centres
n_win = 0
for q, pr in ports.items():
    touches = slot_of(pr["src"]) or slot_of(pr["dst"])
    if not touches:
        continue
    part = P.face_part(q)
    x0, y0, x1, y1 = P.rect(part)
    lo, hi = (x0, x1) if pr["face"] in "NS" else (y0, y1)
    w = max(width_of(pr), abs(pr["window_um"][1] - pr["window_um"][0]), MIN_WIN)
    c = new_c.get(q, centre(pr))
    w = min(w, hi - lo)
    c = min(max(c, lo + w / 2), hi - w / 2)
    pr["window_um"] = [round(c - w / 2, 4), round(c + w / 2, 4)]
    n_win += 1

# slot windows (type frame) + bit_sites shift, from the first instance of each type (sorted part names)
types = raw["partition_types"]
decl, disagree, shifted = {}, 0, 0
for q in sorted(ports):
    pr = ports[q]
    for side in ("src", "dst"):
        so = slot_of(pr[side])
        if not so:
            continue
        part, s, io = so
        tn = P.parts[part]["type"]
        key = (tn, s["name"], "in_window_um" if io == "i" else "out_window_um")
        a, b = pr["window_um"]
        f = pr["face"] if side == "src" or pr["src"]["part"] == S.DIE_PART else OPPF[pr["face"]]
        # die window -> type frame along the face
        if f in "NS":
            ta, tb = P.to_type(part, (a, 0))[0], P.to_type(part, (b, 0))[0]
        else:
            ta, tb = P.to_type(part, (0, a))[1], P.to_type(part, (0, b))[1]
        win = [round(min(ta, tb), 4), round(max(ta, tb), 4)]
        if key in decl:
            if abs(decl[key][0] - win[0]) > 1e-3 or abs(decl[key][1] - win[1]) > 1e-3:
                disagree += 1
            continue
        decl[key] = win
oldc = {}
for p in json.loads(Path(pin).read_text())["ports"]:
    oldc[p["id"]] = centre(p)
for tn, t in types.items():
    for s in t.get("ft_slots", []):
        for wk in ("in_window_um", "out_window_um"):
            if (tn, s["name"], wk) in decl:
                s[wk] = decl[(tn, s["name"], wk)]
# bit_sites shift: per (type, slot) the type-frame delta of the in-port centre of its first instance
delta = {}
for q in sorted(ports):
    pr = ports[q]
    so = slot_of(pr["dst"])
    if not so or q not in new_c:
        continue
    part, s, io = so
    tn = P.parts[part]["type"]
    if (tn, s["name"]) in delta:
        continue
    o, n = oldc[q], new_c[q]
    if pr["face"] in "NS":
        d = P.to_type(part, (n, 0))[0] - P.to_type(part, (o, 0))[0]
        delta[(tn, s["name"])] = (d, 0.0)
    else:
        d = P.to_type(part, (0, n))[1] - P.to_type(part, (0, o))[1]
        delta[(tn, s["name"])] = (0.0, d)
for tn, t in types.items():
    for s in t.get("ft_slots", []):
        dx, dy = delta.get((tn, s["name"]), (0.0, 0.0))
        if (abs(dx) > 1e-6 or abs(dy) > 1e-6) and s.get("bit_sites_um"):
            s["bit_sites_um"] = [[[round(x + dx, 4), round(y + dy, 4)] for x, y in st] for st in s["bit_sites_um"]]
            shifted += 1
raw["note"] = raw.get("note", "") + (" | KV-MP1-R3 CANDIDATE (not plan of record): D-KV-MP1 items 1-3 post-pass "
                                     "(ft windows >= bits x 0.1067/0.1422/0.1532, straight runs snapped into full-span "
                                     "glue strips, bit_sites shifted); split > 668 b NOT applied")
Path(pout).write_text(json.dumps(raw, indent=1))
d = sorted(disp)
Path(rep).write_text(json.dumps(dict(
    ports_windowed=n_win, runs_moved=runs_moved, runs_already_ok=runs_ok, runs_nofit=runs_nofit,
    disp_um=dict(n=len(d), p50=round(d[len(d) // 2], 2) if d else 0, max=round(d[-1], 2) if d else 0),
    slot_windows_declared=len(decl), replica_window_disagreements=disagree, slots_bit_sites_shifted=shifted,
    split_candidates_gt668=[x for x in nofit if x["bits"] > 668][:60],
    nofit_le668=[x for x in nofit if x["bits"] <= 668][:60],
    nofit_counts=dict(gt668=sum(1 for x in nofit if x["bits"] > 668), le668=sum(1 for x in nofit if x["bits"] <= 668))),
    indent=1))
print(open(rep).read()[:1500])
