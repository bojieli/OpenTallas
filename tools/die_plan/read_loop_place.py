#!/usr/bin/env python3
"""FABLE-FIX-S81-BANKLEAF 11-18: close sequencer <-> cfg ROM read loops that are over the reach by CORE PLACEMENT (0 cycles).

A read loop (ot_s81_cfg7_seq a / ce<k> -> ROM addr_in / ce_in, ROM rd_out -> seq q<k>) has a fixed latency inside the sequencer,
so relay_depth.py never gives it a row; a loop whose flight (pin centroid to pin centroid) is over the reach is listed there as
`unfixed`.  This tool moves the ROM of each such loop (a ROM touches only its sequencer and the clock, so nothing else moves and
no other link changes; no core is reshaped or rotated) to the nearest legal site where all three links are <= LIMIT - MARGIN:
  site grid GRID_UM (the plan's macro grid), search radius RADIUS_UM, inside the outline by EDGE_UM, clear of every other hard
  core by CLEAR_UM (the gap the ROM banks already use), nearest first (Manhattan move, then the smaller |dx|: a move along the
  bank column keeps the channels between the ROMs of a row).
usage: read_loop_place.py PLAN.json REPORT.json [REPORT.json ...] [--out-plan OUT.json] [--moves MOVES.json] [--plan-dir DIR]
       REPORTs = relay_depth.py --report files (their `unfixed` read-loop entries select the ROMs).  No site = exit 2, no write."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LIMIT = 405.0
MARGIN = 10.0
GRID_UM = 4.32
RADIUS_UM = 160.0
EDGE_UM = 8.64
CLEAR_UM = 5.0             # the gap the ROM banks already use (5.16 um beside, 6.17 um above / below)
SEQ = re.compile(r"^ot_s81_cfg7_seq")
ROM = re.compile(r"^ot_rom_")


def _centroid(tab, port):
    v = list(tab[port].values())
    return sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)


def _flight(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def loop_lengths(seq_hc, rom_hc, k, plan_dir):
    """flight of the three links of ROM k of this sequencer: (a -> addr_in, ce<k> -> ce_in, rd_out -> q<k>)"""
    import relay_depth as RD
    s, r = RD._pin_table(seq_hc, plan_dir), RD._pin_table(rom_hc, plan_dir)
    return (_flight(_centroid(s, "a"), _centroid(r, "addr_in")), _flight(_centroid(s, f"ce{k}"), _centroid(r, "ce_in")),
            _flight(_centroid(r, "rd_out"), _centroid(s, f"q{k}")))


def _box(hc):
    dx, dy = hc.get("track_offset_um", [0.0, 0.0])
    x, y = hc["origin_um"][0] + dx, hc["origin_um"][1] + dy
    return x, y, x + hc["outline_um"][0], y + hc["outline_um"][1]


def _legal(t, hc, others):
    x0, y0, x1, y1 = _box(hc)
    w, h = t["outline_um"]
    if x0 < EDGE_UM or y0 < EDGE_UM or x1 > w - EDGE_UM or y1 > h - EDGE_UM:
        return False
    for o in others:
        a0, b0, a1, b1 = o
        if x0 < a1 + CLEAR_UM and a0 < x1 + CLEAR_UM and y0 < b1 + CLEAR_UM and b0 < y1 + CLEAR_UM:
            return False
    return True


def place(t, seq_inst, rom_inst, plan_dir, limit=LIMIT):
    """-> move dict (new origin) or None when no site within RADIUS_UM closes the loop"""
    hcs = {h["inst"]: h for h in t["hard_cores"]}
    seq, rom = hcs[seq_inst], hcs[rom_inst]
    k = int(rom_inst.rsplit("_", 1)[1])
    others = [_box(h) for i, h in hcs.items() if i != rom_inst and "origin_um" in h and "outline_um" in h]
    ox, oy = rom["origin_um"]
    before = loop_lengths(seq, rom, k, plan_dir)
    n = int(RADIUS_UM // GRID_UM)
    cands = sorted(((abs(i) + abs(j), abs(i), i, j) for i in range(-n, n + 1) for j in range(-n, n + 1)
                    if (abs(i) + abs(j)) * GRID_UM <= RADIUS_UM))
    for _d, _aj, i, j in cands:
        trial = dict(rom, origin_um=[round(ox + i * GRID_UM, 3), round(oy + j * GRID_UM, 3)])
        if not _legal(t, trial, others):
            continue
        after = loop_lengths(seq, trial, k, plan_dir)
        if max(after) <= limit - MARGIN:
            return dict(seq=seq_inst, rom=rom_inst, origin_um=[ox, oy], new_origin_um=trial["origin_um"],
                        move_um=[round(i * GRID_UM, 3), round(j * GRID_UM, 3)],
                        before_um=[round(x, 1) for x in before], after_um=[round(x, 1) for x in after])
    return None


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("reports", nargs="+")
    ap.add_argument("--out-plan")
    ap.add_argument("--moves")
    ap.add_argument("--plan-dir")
    a = ap.parse_args(argv[1:])
    plan = json.loads(Path(a.plan).read_text())
    plan_dir = Path(a.plan_dir or Path(a.plan).resolve().parent)
    pt = plan["partition_types"]
    todo = {}
    for f in a.reports:
        for rep in json.loads(Path(f).read_text()):
            for u in rep.get("unfixed") or []:
                if "read loop" not in u.get("reason", ""):
                    continue
                hcs = {h["inst"]: h for h in pt[rep["type"]]["hard_cores"]}
                ends = (u["core"], u["partner"].rpartition(".")[0])
                rom = next(e for e in ends if ROM.search(hcs[e]["module"]))
                seq = next(e for e in ends if SEQ.search(hcs[e]["module"]))
                todo.setdefault(rep["type"], set()).add((seq, rom))
    moves, bad, cache = [], [], {}
    for tn in sorted(todo):
        t = pt[tn]
        for seq, rom in sorted(todo[tn]):
            geo = json.dumps([[h["inst"], h.get("origin_um"), h.get("outline_um"), h.get("orient")] for h in t["hard_cores"]]) + seq + rom
            m = cache.get(geo)
            if geo not in cache:
                m = cache[geo] = place(t, seq, rom, plan_dir)
            if m is None:
                bad.append(f"{tn}: {rom} (no legal site within {RADIUS_UM} um)")
                continue
            next(h for h in t["hard_cores"] if h["inst"] == rom)["origin_um"] = list(m["new_origin_um"])
            moves.append(dict(m, type=tn))
    for m in moves:
        print(f"{m['type']}: {m['rom']} {m['origin_um']} -> {m['new_origin_um']} (move {m['move_um']}); "
              f"a/ce/rd flight {m['before_um']} -> {m['after_um']}")
    if bad:
        print("READ_LOOP_PLACE FAIL:\n  " + "\n  ".join(bad))
        return 2
    if a.moves:
        Path(a.moves).write_text(json.dumps(moves, indent=1))
    if a.out_plan:
        Path(a.out_plan).write_text(json.dumps(plan, indent=1))
    print(f"READ_LOOP_PLACE {len(moves)} ROM move(s) in {len(todo)} type(s), 0 cycles")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
