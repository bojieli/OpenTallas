#!/usr/bin/env python3
"""QC st_a btab SRAM column row (FAM-QC-HCST-R2, COORD FABLE-PD-QC-1230 V3 item 2).
Moves the 4 btab SRAMs (g_btb[*]) of each st_a type ~259 um north into one x=449.28 column (window 149..370 um, FABLE-PD-QC 1.9),
then re-sites every exact station site / register that lands inside a hard core + halo (RowAllocator, nearest legal, same cell).
usage: btab_column.py PLAN OUT REPORT [--shift N]"""
import argparse, json, math, sys
sys.path.insert(0, "/srv/opentallas-scratch2/claude/FAM-QC-HCST-R3/launch/tools/die_plan"); sys.path.insert(0, "/srv/opentallas-scratch2/claude/FAM-QC-HCST-R3/launch")
import schema as S
from tools.die_trial.legal_sites import RowAllocator

CELL = (1.404, .27); M = 4.32; HALO = 4.32; LAT = 8.64; PITCH = 51.84; WIN = (149.0, 370.0); COLX = 449.28

def snap(v): return round(round(v / LAT) * LAT, 3)

def plan_moves(t, shift):
    srams = sorted([c for c in t["hard_cores"] if "g_btb" in c["inst"]], key=lambda c: (c["origin_um"][1], c["origin_um"][0]))
    new = []; prev = -1e9
    for c in srams:
        y = max(snap(c["origin_um"][1] + shift), prev + PITCH); prev = y; new.append(y)
    # keep shifts inside the window; slide the whole column down if the last pushed too far
    for c, y in zip(srams, new):
        d = y - c["origin_um"][1]
        if not (WIN[0] <= d <= WIN[1]): raise SystemExit(f"shift {d:.1f} outside window for {c['inst']}")
    return list(zip(srams, new))

def boxes_of(t): return list(S.placed_macro_boxes(t, halo=HALO).values())

def hit(x, y, w, h, boxes): return any(x < c and x + w > a and y < d and y + h > b for a, b, c, d in boxes)

def run(raw, shift, only):
    rep = []
    for tn, t in raw["partition_types"].items():
        if only and tn not in only: continue
        if not any("g_btb" in c["inst"] for c in t.get("hard_cores", [])): continue
        moves = plan_moves(t, shift)
        row = dict(type=tn, shifts=[], resited={}, max_disp_um=0.0, regs_hop_worst=[])
        for c, y in moves:
            row["shifts"].append([c["inst"].split(".")[-2], c["origin_um"][:], [COLX, y], round(y - c["origin_um"][1], 2)])
            c["origin_um"] = [COLX, y]
        boxes = boxes_of(t); w, h = map(float, t["outline_um"])
        al = RowAllocator((M, M, w - M, h - M), blocked=boxes, cell_size=CELL, column_pitch=2.16, row_pitch=.27, origin=(M, M))
        # occupy every existing site that is legal; collect the illegal ones
        groups = []   # (container, key, index path) ; items are ll footprints
        def scan(lst_getter, setter, name, ll=True):
            pass
        bad = []; seen = []
        def reg(stage, owner, key, si=None):
            for i, p in enumerate(stage):
                x, y = (p[0], p[1]) if ll else None
        # footprints
        cw, ch = CELL
        def fp_ok(p): return not hit(p[0], p[1], cw, ch, boxes)
        stage_lists = []
        for s in t.get("ft_slots", []):
            if s.get("bit_sites_um"):
                for st in s["bit_sites_um"]: stage_lists.append((f"ft:{s['name']}", st))
        for s in t.get("internal_stations", []):
            for st in (s.get("bit_sites_um") or []): stage_lists.append((f"int:{s['conn']}", st))
            if s.get("face_bit_sites_um"): stage_lists.append((f"intface:{s['conn']}", s["face_bit_sites_um"]))
        for name, st in stage_lists:
            for p in st:
                if fp_ok(p): al.reserve_rectangle((p[0], p[1], p[0] + cw, p[1] + ch))
        for name, st in stage_lists:
            for i, p in enumerate(st):
                if fp_ok(p): continue
                ctr = (p[0] + cw / 2, p[1] + ch / 2)
                sites, _ = al.allocate(ctr, 1, max_radius_um=120.0)
                q = [round(float(sites[0][0] - cw / 2), 3), round(float(sites[0][1] - ch / 2), 3)]
                disp = abs(q[0] - p[0]) + abs(q[1] - p[1])
                row["max_disp_um"] = max(row["max_disp_um"], disp)
                r = row["resited"].setdefault(name, [0, 0.0]); r[0] += 1; r[1] = max(r[1], round(disp, 1))
                st[i] = q
        def regs_fix(owner, label, a=None, b=None):
            regs = owner.get("regs_um") or []
            pts = ([owner.get("from_um")] if owner.get("from_um") else []) + regs + ([owner.get("to_um")] if owner.get("to_um") else [])
            before = max([abs(p[0]-q[0]) + abs(p[1]-q[1]) for p, q in zip(pts, pts[1:])] or [0])
            for i, r in enumerate(regs):
                if hit(r[0] - cw / 2, r[1] - ch / 2, cw, ch, boxes):
                    sites, _ = al.allocate(tuple(r), 1, max_radius_um=120.0)
                    regs[i] = [round(float(sites[0][0]), 3), round(float(sites[0][1]), 3)]
                    row["resited"].setdefault(label + ":regs", [0, 0.0])[0] += 1
            pts = ([owner.get("from_um")] if owner.get("from_um") else []) + regs + ([owner.get("to_um")] if owner.get("to_um") else [])
            after = max([abs(p[0]-q[0]) + abs(p[1]-q[1]) for p, q in zip(pts, pts[1:])] or [0])
            if abs(after - before) > 1e-6: row["regs_hop_worst"].append([label, round(before, 1), round(after, 1)])
        for s in t.get("internal_stations", []): regs_fix(s, "int:" + s["conn"])
        for s in t.get("ft_slots", []): regs_fix(s, "ft:" + s["name"])
        # exact collision audit
        row["residual_site_hits"] = sum(1 for _, st in stage_lists for p in st if not fp_ok(p))
        rep.append(row)
    return rep

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--shift", type=float, default=259.2); ap.add_argument("--types")
    a = ap.parse_args()
    raw = json.load(open(a.plan))
    rep = run(raw, a.shift, set(a.types.split(",")) if a.types else None)
    json.dump(raw, open(a.out, "w"), indent=1); open(a.out, "a").write("\n")
    json.dump(rep, open(a.report, "w"), indent=1)
    for r in rep: print(r["type"], "max_disp", round(r["max_disp_um"], 1), "resited", r["resited"], "residual", r["residual_site_hits"], "hops", r["regs_hop_worst"])
