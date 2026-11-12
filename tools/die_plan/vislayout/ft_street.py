#!/usr/bin/env python3
"""VISLAYOUT3-KVHEAD ft_street.py: positions-only re-site of ft-slot stations off hard-core columns into a street.

    ft_street.py PLAN_IN PLAN_OUT LEDGER.json TYPE MOVE [MOVE ...] [--bins IN.json OUT.json] [--bins-path P]

MOVE = slot:station:dx:dy  (station = index into bit_sites_um; regs_um[station+1] moves with it).
Every bit site of the station is translated by (dx, dy) (dx snapped to the 0.216-um column lattice, dy to the
0.27-um row), then any bit cell that hits an obstacle (hard core + 1.08 keep-off, die island, keepout, landing band,
collector relay / reset / strap site cell, any other ft bit cell) slides along its own column (row steps) to the
nearest free row.  Station counts, slot widths, faces, pins, cores, outline, cycles: unchanged (asserted).
--bins: the type's clock sink_bins file; every bin inside a moved station's old bbox (+ half a bin) moves by the
same (dx, dy) (sink inventory follows the flops); the plan's clock.sink_bins_file is pointed at --bins-path."""
import argparse, copy, gzip, json, math, sys

CELL = (1.404, 0.27)
KEEP = 1.08


def load(p):
    return json.load(gzip.open(p) if p.endswith(".gz") else open(p))


def walk(o, path=()):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, path + (k,))
    elif isinstance(o, list):
        if len(o) in (2, 4) and all(isinstance(v, (int, float)) for v in o):
            yield path, o
        else:
            for i, v in enumerate(o):
                yield from walk(v, path + (i,))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in"); ap.add_argument("plan_out"); ap.add_argument("ledger"); ap.add_argument("type")
    ap.add_argument("moves", nargs="+")
    ap.add_argument("--bins", nargs=2)
    ap.add_argument("--bins-path")
    a = ap.parse_args()
    P = load(a.plan_in); P0 = copy.deepcopy(P)
    t = P["partition_types"][a.type]
    W, H = t["outline_um"]
    rects = []   # (x0,y0,x1,y1,label)
    for c in t.get("hard_cores", []):
        x, y = c["origin_um"]; w, h = c.get("size_um") or c.get("outline_um")
        if str(c.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        rects.append((x - KEEP, y - KEEP, x + w + KEEP, y + h + KEEP, "core:" + c["inst"]))
    pts = []
    for path, v in walk(t.get("clock", {}), ("clock",)):
        s = ".".join(map(str, path))
        if len(v) == 4 and ("island" in s or "keepout" in s or "rect" in s or "band" in s):
            rects.append((v[0] - 0.3, v[1] - 0.3, v[2] + 0.3, v[3] + 0.3, s))
        elif len(v) == 2 and s.endswith("xy") or (len(v) == 2 and "site" in s):
            pts.append((v[0], v[1], s))
    for key in ("reset", "count_straps", "reset_spine_pins"):
        for path, v in walk(t.get(key, {}), (key,)):
            if len(v) == 2:
                pts.append((v[0], v[1], ".".join(map(str, path))))
    for (x, y, s) in pts:
        rects.append((x - 0.75, y - 0.3, x + CELL[0] + 0.75, y + CELL[1] + 0.3, s))
    slots = {f["name"]: f for f in t["ft_slots"]}
    moves = []
    for m in a.moves:
        s, j, dx, dy = m.split(":")
        dx = round(round(float(dx) / 0.216) * 0.216, 4); dy = round(round(float(dy) / 0.27) * 0.27, 4)
        moves.append((s, int(j), dx, dy))
    moving = {(s, j) for s, j, _, _ in moves}
    # occupancy of every OTHER ft bit cell (row-keyed for speed)
    occ = {}

    def key(x, y):
        return round(y / 0.27)

    def add(x, y):
        occ.setdefault(key(x, y), []).append(x)

    for f in t["ft_slots"]:
        for j, st in enumerate(f.get("bit_sites_um") or []):
            if (f["name"], j) in moving:
                continue
            for b in st:
                if isinstance(b, list) and len(b) == 2:
                    add(*b)

    def free(x, y):
        if x < 0.5 or y < 0.5 or x + CELL[0] > W - 0.5 or y + CELL[1] > H - 0.5:
            return False
        for (x0, y0, x1, y1, _) in rects:
            if x < x1 and x + CELL[0] > x0 and y < y1 and y + CELL[1] > y0:
                return False
        for ox in occ.get(key(x, y), ()):
            if abs(ox - x) < CELL[0]:
                return False
        return True

    led = {"type": a.type, "moves": [], "obstacle_rects": len(rects)}
    bins_shift = []
    for s, j, dx, dy in moves:
        f = slots[s]; st = f["bit_sites_um"][j]
        xs = [b[0] for b in st if isinstance(b, list)]; ys = [b[1] for b in st if isinstance(b, list)]
        old_bbox = [min(xs), min(ys), max(xs) + CELL[0], max(ys) + CELL[1]]
        new = []; slid = 0; maxslide = 0.0
        for b in st:
            if not (isinstance(b, list) and len(b) == 2):
                new.append(b); continue
            x, y = round(b[0] + dx, 4), round(b[1] + dy, 4)
            if not free(x, y):
                for n in range(1, 2000):
                    hit = None
                    for yy in (y + n * 0.27, y - n * 0.27):
                        if free(x, round(yy, 4)):
                            hit = round(yy, 4); break
                    if hit is not None:
                        maxslide = max(maxslide, abs(hit - y)); y = hit; slid += 1; break
                else:
                    sys.exit(f"FAIL {s}[{j}] bit at ({x},{y}) found no free row")
            add(x, y); new.append([x, y])
        f["bit_sites_um"][j] = new
        r = f["regs_um"][j + 1]
        f["regs_um"][j + 1] = [round(r[0] + dx, 4), round(r[1] + dy, 4)]
        nx = [b[0] for b in new if isinstance(b, list)]; ny = [b[1] for b in new if isinstance(b, list)]
        led["moves"].append(dict(slot=s, station=j, dx=dx, dy=dy, bits=len(nx), slid=slid, max_slide_um=round(maxslide, 3),
                                 old_bbox=[round(v, 3) for v in old_bbox],
                                 new_bbox=[round(min(nx), 3), round(min(ny), 3), round(max(nx) + CELL[0], 3), round(max(ny) + CELL[1], 3)],
                                 old_reg=r, new_reg=f["regs_um"][j + 1]))
        bins_shift.append((old_bbox, dx, dy))
    # invariants: only these slots' bit_sites_um / regs_um (and clock.sink_bins_file) changed
    t0 = P0["partition_types"][a.type]
    for k in t:
        if k in ("ft_slots", "clock"):
            continue
        assert t[k] == t0[k], k
    for f, f0 in zip(t["ft_slots"], t0["ft_slots"]):
        for k in f:
            if k not in ("bit_sites_um", "regs_um"):
                assert f[k] == f0[k], (f["name"], k)
        assert len(f["bit_sites_um"]) == len(f0["bit_sites_um"]) and len(f["regs_um"]) == len(f0["regs_um"])
        assert all(len(x) == len(y) for x, y in zip(f["bit_sites_um"], f0["bit_sites_um"]))
    for k in P:
        if k != "partition_types":
            assert P[k] == P0[k], k
    for tn in P["partition_types"]:
        if tn != a.type:
            assert P["partition_types"][tn] is P0["partition_types"][tn] or P["partition_types"][tn] == P0["partition_types"][tn]
    if a.bins:
        B = json.load(open(a.bins[0])); half = B.get("bin_um", 10.8) / 2; moved = 0; nmoved = 0
        out = []
        for bx, by, n in B["bins"]:
            for (bb, dx, dy) in bins_shift:
                if bb[0] - half <= bx <= bb[2] + half and bb[1] - half <= by <= bb[3] + half:
                    bx, by = round(bx + dx, 4), round(by + dy, 4); moved += 1; nmoved += n; break
            out.append([bx, by, n])
        B["bins"] = out; B["source"] = B.get("source", "") + " | VISLAYOUT3-KVHEAD ft_street: %d bins (%d sinks) moved with ft stations" % (moved, nmoved)
        json.dump(B, open(a.bins[1], "w"))
        led["bins_moved"] = moved; led["bin_sinks_moved"] = nmoved
        if a.bins_path:
            t["clock"]["sink_bins_file"] = a.bins_path
    for k in t["clock"]:
        if k != "sink_bins_file":
            assert t["clock"][k] == t0["clock"][k], k
    json.dump(P, open(a.plan_out, "w"), indent=1)
    json.dump(led, open(a.ledger, "w"), indent=1)
    print(json.dumps(led["moves"], indent=0)[:3000]); print("bins", led.get("bins_moved"), led.get("bin_sinks_moved"))


main()
