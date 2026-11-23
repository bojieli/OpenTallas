#!/usr/bin/env python3
"""KV-LEAF-BANKS (OPUS-KV-DIE-R2 11-22): leaf-anchored vport station chains and exact bit-group banks, inside CORE_AREA.

Main home of the D28 "R5" generator (OPUS-FIX-KV-PV-R5 split28/reanchor_pure_leaf.py + reanchor_mixed_leaf.py), which
wrote the D28 kv3_pv_v3 / v3e exact bit-group banks.  Two defects of that generator stopped both reps at place:
  (1) banks were allocated inside the outline minus 1.08 um, not inside the placement rows: 749 bit sites lay outside
      CORE_AREA (kit_fit.kit_core_area, 4.32 um inset) and place refused them "exact internal bank site is not on
      row/site" (OPUS-FIX-KV-PV-R7 21:59, fixed in the plan by the D29 BANKCORE row);
  (2) the bank cell was 1.188 um, but every bank holds the async-reset epoch flop DFFASRHQNx1 (1.404 um) (PV-R7 19:19,
      fixed by the D29 PVCELL row).
Here every site is allocated on the type's real rows: the allocator bounds and grid origin are kit_core_area, station
centres keep a cell clear of it, the cell is 1.404 x 0.27, and before the plan is written every exact site of every
changed type is checked with adv_bank_offarea.type_hits; any site outside CORE_AREA refuses the run (exit 2).

usage:
  kv_leaf_bank_sites.py pure  PLAN_IN RTL_DIR PLAN_OUT REPORT_OUT [--types T,..]
  kv_leaf_bank_sites.py mixed PLAN_IN PURE_REPORT RTL_DIR PLAN_OUT REPORT_OUT
RTL_DIR holds <type>_part.sv (the bound partition RTL).  Depth and cycles never change.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "die_trial"))
from kit_fit import kit_core_area  # noqa: E402
from adv_bank_offarea import type_hits  # noqa: E402
from legal_sites import RowAllocator  # noqa: E402

CELL = (1.404, 0.27)          # DFFASRHQNx1, the widest flop of a bank (epoch flop); PV-R7 19:19
CELL_W, ROW_H = CELL
PITCH = 2.376                 # column pitch of the D28 banks (>= CELL_W)
SNAP = 8.64                   # street search step
STATION0 = re.compile(r"\s*ot_dp_st #\(\.W\((\d+)\)\) u_ist_(\w+)_0 \(.*?\.d\((.*?)\), \.ea")
SLICE = re.compile(r"w_(vport_[EW])_\w+\[(\d+)(?::(\d+))?\]")
CHUNK = re.compile(r"(\w+)\[(\d+)(?::(\d+))?\]")
STAGE = re.compile(r"\.d\((.*?)\), \.ea")
ROT = {"R90", "R270", "MXR90", "MYR90"}
DEFAULT_TYPES = ("kv3_pv_v3", "kv3_pv_v3e")


def distance(a, b):
    return sum(abs(c - d) for c, d in zip(a, b))


def centre_area(item):
    """Station-centre window: CORE_AREA shrunk by half a cell, so a bank centred there stays on the rows."""
    x0, y0, x1, y1 = kit_core_area(item)
    return x0 + CELL_W / 2, y0 + ROW_H / 2, x1 - CELL_W / 2, y1 - ROW_H / 2


def core_boxes(item, halo=0.0):
    boxes = []
    for c in item.get("hard_cores", []):
        dx, dy = c.get("track_offset_um", [0.0, 0.0])
        (x, y), (w, h) = c["origin_um"], c["outline_um"]
        if c.get("orient") in ROT:
            w, h = h, w
        boxes.append((x + dx - halo, y + dy - halo, x + dx + w + halo, y + dy + h + halo))
    clock = item.get("clock", {})
    boxes.extend(tuple(b) for b in clock.get("keepouts_um", []))
    boxes.extend(tuple(b["rect_um"]) for b in clock.get("landing_contract", {}).get("bands", {}).values()
                 if len(b.get("rect_um", [])) == 4)
    return boxes


def fits(p, area, boxes, pad=1.08):
    x, y = p
    a, b, c, d = area
    return (a <= x <= c and b <= y <= d
            and all(not (u - pad <= x <= v + pad and q - pad <= y <= r + pad) for u, q, v, r in boxes))


def sites_between(start, end, length, area, boxes):
    """`length` station centres from start to end on a macro-free street, every one inside `area`."""
    candidates = [[start, (start[0], end[1]), end], [start, (end[0], start[1]), end]]
    for axis in (0, 1):
        for i in range(1, int(area[axis + 2] / SNAP)):
            a, b = list(start), list(end)
            a[axis] = b[axis] = SNAP * i
            candidates.append([start, tuple(a), tuple(b), end])
    best = None
    for path in candidates:
        total = sum(distance(a, b) for a, b in zip(path, path[1:]))
        if total > 270 * length:
            continue
        samples = []
        for a, b in zip(path, path[1:]):
            steps = max(1, math.ceil(distance(a, b) / 2.16))
            samples.extend(tuple(a[i] + (b[i] - a[i]) * k / steps for i in (0, 1)) for k in range(steps))
        samples.append(tuple(end))
        prev, cursor, chosen = start, 0, []
        for j in range(length):
            index = round((len(samples) - 1) * j / length)
            options = [i for i in range(max(cursor, index - 40), min(len(samples) - 1, index + 41))
                       if fits(samples[i], area, boxes) and samples[i] not in chosen
                       and distance(prev, samples[i]) <= (100 if j == 0 else 300)]
            if not options:
                break
            cursor = min(options, key=lambda i: abs(i - index)) + 1
            prev = samples[cursor - 1]
            chosen.append(prev)
        if len(chosen) == length and distance(chosen[-1], end) <= 300:
            score = (distance(start, chosen[0]), max(distance(a, b) for a, b in zip(chosen, chosen[1:] + [end])), total)
            if best is None or score < best[0]:
                best = score, chosen
    return None if best is None else [[round(x, 4), round(y, 4)] for x, y in best[1]]


def anchors_of(rows):
    anchors = {}
    for row in rows:
        m = re.search(r"leaf (u_\w+)", row.get("capture", ""))
        if m:
            anchors.setdefault(m.group(1), row["to_um"])
    return anchors


def face_rows(rows):
    return {r["capture"].split()[2]: r for r in rows if r.get("capture", "").startswith("face bus ")}


def check_on_rows(plan, names):
    """Refuse when any exact site of a changed type lies outside CORE_AREA (the PV-R7 21:59 class)."""
    bad = []
    for n in names:
        area, hits = type_hits(plan["partition_types"][n])
        bad.extend((n, area, h) for h in hits)
    if bad:
        for n, area, h in bad[:10]:
            print(f"REFUSED {n} {h[0]} ({h[1]:g},{h[2]:g}) {h[3]:g} um outside CORE_AREA {area}", file=sys.stderr)
        raise SystemExit(f"REFUSED: {len(bad)} exact site(s) outside CORE_AREA; nothing written")


def cmd_pure(plan_file, rtl_dir, output, report_file, types):
    plan = json.loads(Path(plan_file).read_text())
    report = {}
    for name in types:
        item = plan["partition_types"][name]
        area, boxes = centre_area(item), core_boxes(item)
        rows = item["internal_stations"]
        anchors, by_bus = anchors_of(rows), face_rows(rows)
        res = report[name] = {"moved": [], "mixed": [], "unsolved": []}
        for line in (Path(rtl_dir) / f"{name}_part.sv").read_text().splitlines():
            m = STATION0.match(line)
            if not m:
                continue
            width, bus, expr = m.groups()
            members = SLICE.findall(expr)
            leaves = {"u_" + r[0] for r in members} & anchors.keys()
            if not leaves or bus not in by_bus:
                continue
            row = by_bus[bus]
            depth = len(row["regs_um"])
            if not depth:
                continue
            leaf = sorted(leaves)[0]
            start = anchors[leaf]
            old_hop = distance(start, row["regs_um"][0])
            if old_hop <= 300:
                continue
            leaf_width = sum(abs(int(hi) - int(lo)) + 1 if lo else 1 for _, hi, lo in members)
            rec = dict(bus=bus, width=int(width), leaf=leaf, leaf_bits=leaf_width, old_hop=round(old_hop, 2), depth=depth)
            if len(leaves) != 1 or leaf_width != int(width):
                res["mixed"].append(rec)
                continue
            pts = sites_between(tuple(start), tuple(row["to_um"]), depth, area, boxes)
            if pts is None:
                res["unsolved"].append(rec)
                continue
            rec["new_hop"] = round(distance(start, pts[0]), 2)
            rec["max_hop"] = round(max(distance(x, y) for x, y in zip([start] + pts, pts + [row["to_um"]])), 2)
            row.update(from_um=start, regs_um=pts, launch=f"leaf {leaf}")
            row["note"] = row.get("note", "") + " | KV-LEAF-BANKS pure vport first stage seated at the launch leaf; cycles unchanged"
            res["moved"].append(rec)
    check_on_rows(plan, types)
    Path(output).write_text(json.dumps(plan, separators=(",", ":")) + "\n")
    Path(report_file).write_text(json.dumps(report, indent=2) + "\n")
    print({k: {g: len(v) for g, v in t.items()} for k, t in report.items()})


def membership(expr, leaf):
    bits = []
    for word in reversed(expr.strip("{}").split(",")):
        m = CHUNK.fullmatch(word.strip())
        if not m:
            raise ValueError(f"unsupported source slice: {word!r}")
        signal, high, low = m.groups()
        width = abs(int(high) - int(low)) + 1 if low is not None else 1
        bits.extend([signal.startswith("w_" + leaf.removeprefix("u_") + "_")] * width)
    return bits


def make_allocator(item):
    """Row allocator on the type's placement rows: bounds AND grid origin = CORE_AREA (row/site aligned)."""
    x0, y0, x1, y1 = kit_core_area(item)
    return RowAllocator((x0, y0, x1, y1), core_boxes(item, halo=2.16), CELL, PITCH, ROW_H, origin=(x0, y0))


def reserve_existing(alloc, item, changing):
    for x, y in item.get("relay_sites", {}).values():
        alloc.reserve_rectangle((x - 0.54, y - 0.135, x + 0.54, y + 0.135))
    for slot in item.get("ft_slots", []):
        fw, fh = slot.get("bit_site_cell_um", CELL)
        for bank in slot.get("bit_sites_um", []):
            for x, y in bank:
                alloc.reserve_rectangle((x, y, x + fw, y + fh))
    for row in item["internal_stations"]:
        if row["conn"].removeprefix("bus:") in changing:
            continue
        fw, fh = row.get("bit_site_cell_um", CELL)
        for bank in row.get("bit_sites_um", []):
            for x, y in bank:
                alloc.reserve_rectangle((x, y, x + fw, y + fh))


def cmd_mixed(plan_file, pure_report, rtl_dir, output, report_file):
    plan = json.loads(Path(plan_file).read_text())
    report = json.loads(Path(pure_report).read_text())
    changed = []
    for name, info in report.items():
        item = plan["partition_types"][name]
        area, boxes = centre_area(item), core_boxes(item, halo=2.16)
        alloc = make_allocator(item)
        changing = {r["bus"] for r in info["mixed"]}
        reserve_existing(alloc, item, changing)
        by_bus, anchors = face_rows(item["internal_stations"]), anchors_of(item["internal_stations"])
        rtl = (Path(rtl_dir) / f"{name}_part.sv").read_text().splitlines()
        for rec in info["mixed"]:
            bus, leaf, W, depth = (rec[k] for k in ("bus", "leaf", "width", "depth"))
            first, = [s for s in rtl if " u_ist_" + bus + "_0 " in s]
            leaf_bits = membership(STAGE.search(first).group(1), leaf)
            assert len(leaf_bits) == W and sum(leaf_bits) == rec["leaf_bits"], rec
            row = by_bus[bus]
            assert len(row["regs_um"]) == depth and "bit_sites_um" not in row and "bit_route" not in row
            start, end = anchors[leaf], row["to_um"]
            targets = sites_between(tuple(start), tuple(end), depth, area, boxes)
            if targets is None:
                rec.update(accepted=False, leaf_max_um=None, forwarded_max_um=None, why="no legal street")
                continue
            fwd = sites_between(tuple(row["from_um"]), tuple(end), depth, area, boxes) or row["regs_um"]
            banks = []
            for point, old in zip(targets, fwd):
                old = [min(max(old[0], area[0]), area[2]), min(max(old[1], area[1]), area[3])]
                local, _ = alloc.allocate(point, sum(leaf_bits), max_radius_um=72)
                forwarded, _ = alloc.allocate(old, W - sum(leaf_bits) + 1, max_radius_um=72)
                groups = {True: iter(local), False: iter(forwarded)}
                banks.append([[round(float(x) - CELL_W / 2, 6), round(float(y) - ROW_H / 2, 6)]
                              for x, y in (next(groups[m]) for m in [*leaf_bits, False])])
            leaf_worst = max(distance(a, b) for i, own in enumerate(leaf_bits) if own
                             for a, b in zip([start] + [s[i] for s in banks], [s[i] for s in banks] + [end]))
            fwd_worst = max(distance(a, b) for i, own in enumerate([*leaf_bits, False]) if not own
                            for a, b in zip([row["from_um"]] + [s[i] for s in banks], [s[i] for s in banks] + [end]))
            rec.update(leaf_max_um=round(leaf_worst, 2), forwarded_max_um=round(fwd_worst, 2))
            if leaf_worst > 300 or fwd_worst > 405:
                print("MIXED_LIMIT", name, bus, rec["leaf_max_um"], rec["forwarded_max_um"], flush=True)
                rec["accepted"] = False
                continue
            row.update(bit_sites_um=banks, bit_site_cell_um=list(CELL))
            row["note"] = row.get("note", "") + " | KV-LEAF-BANKS exact bit-group site banks for leaf versus forwarded source, on CORE_AREA rows; depth unchanged"
            rec["accepted"] = True
            changed.append(name)
    check_on_rows(plan, sorted(set(changed)))
    Path(output).write_text(json.dumps(plan, separators=(",", ":")) + "\n")
    Path(report_file).write_text(json.dumps(report, indent=2) + "\n")
    print({k: [(r["bus"], r.get("accepted"), r.get("leaf_max_um"), r.get("forwarded_max_um")) for r in v["mixed"]]
           for k, v in report.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pure")
    p.add_argument("plan"); p.add_argument("rtl_dir"); p.add_argument("out"); p.add_argument("report")
    p.add_argument("--types", default=",".join(DEFAULT_TYPES))
    m = sub.add_parser("mixed")
    m.add_argument("plan"); m.add_argument("pure_report"); m.add_argument("rtl_dir"); m.add_argument("out"); m.add_argument("report")
    a = ap.parse_args(argv)
    if a.cmd == "pure":
        cmd_pure(a.plan, a.rtl_dir, a.out, a.report, [t for t in a.types.split(",") if t])
    else:
        cmd_mixed(a.plan, a.pure_report, a.rtl_dir, a.out, a.report)


if __name__ == "__main__":
    main()
