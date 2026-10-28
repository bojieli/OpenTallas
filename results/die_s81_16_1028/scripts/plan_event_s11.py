#!/usr/bin/env python3
"""DIE-S81-16 S81 plan event plan_s11 = plan_s10 + COORD 13:5x ASK 3 items (die-local plan input, no shared-tool edit).
 (a) bf_col plan clk pin on its N edge rect = the CORES-EARLY-1 550a4b5e10 pin table (merged input file; the plan json
     only references it).  Tap xy are NOT moved: the plan_s10 core taps sit at the CORELAT boundary point, not at the
     pin-table clk pin (reported as tap_to_pin_um)
 (b) rom_elem_q binds the _gb master (ot_v41_rom_elem_q_qxpq_w10_gb: only unused xs_sv[1:0] removed, same clk pin)
 (c) early taps of rom_elem_q / bf_col re-derived: no CORES-EARLY-2 signed views yet -> --rom-tt/--bf-tt (TT ps,
     FF = TT x the plan_s10 FF/TT ratio of that tap), labelled UNCHECKED in budget_owner
 (d) delta_signed_view_pins_1028.py is run on the OUTPUT afterwards (separate command, see README)
usage (worktree root): plan_event_s11.py PLAN_IN PLAN_OUT --rom-tt 285 --bf-tt 285"""
import argparse, collections, hashlib, json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("out")
ap.add_argument("--rom-tt", type=float, required=True); ap.add_argument("--bf-tt", type=float, required=True)
a = ap.parse_args()
raw = Path(a.plan).read_bytes(); P = json.loads(raw)
S81 = Path("physical/die_plan/s81")
GB = dict(module="ot_v41_rom_elem_q_qxpq_w10_gb", lef="physical/die_plan/s81/cores/elem_boundary/ot_v41_rom_elem_q_qxpq_w10_gb.lef",
          pins_file="inputs/core_pins/ot_v41_rom_elem_q_qxpq_w10_gb.json")
stat = collections.Counter()


def clock_xy(c):
    pins = json.load(open(S81 / c["pins_file"]))["pins"]
    ck = [p for p in pins if p["name"] in ("clk", "ck", "clock")]
    assert len(ck) == 1, (c["inst"], [p["name"] for p in ck])
    p = ck[0]; x, y = c["origin_um"]; w, h = c["outline_um"]; px, py = p["x"], p["y"]; o = c.get("orient", "R0")
    if o in ("MY", "R180"): px = w - px
    if o in ("MX", "R180"): py = h - py
    dx, dy = c.get("track_offset_um", [0.0, 0.0])
    return p["name"], [round(x + dx + px, 3), round(y + dy + py, 3)]


moves = []
for tn, t in P["partition_types"].items():
    taps = (t.get("clock") or {}).get("taps", [])
    for c in t.get("hard_cores", []):
        m = c.get("module")
        if m not in ("ot_v41_rom_elem_q_qxpq_w10", "ot_v41_bf_col"):
            continue
        if m == "ot_v41_rom_elem_q_qxpq_w10":
            c.update(GB); c.pop("lib", None)       # (b) no _gb lib yet: the die STA uses the declared tap insertion
            c["note"] = (c.get("note", "") + " | DIE-S81-16 plan_s11: _gb master (unused xs_sv[1:0] removed)").lstrip(" |")
            stat["rom_gb_bind"] += 1
            tt = a.rom_tt
        else:
            tt = a.bf_tt
        pin, xy = clock_xy(c)
        for tp in taps:
            if tp.get("kind") == "core" and (tp["name"] == c["inst"] + "." + pin or tp["name"].startswith(c["inst"] + ".")):
                moves.append(abs(tp["xy"][0] - xy[0]) + abs(tp["xy"][1] - xy[1]))
                r = tp["insertion_ff_ps"] / tp["insertion_ps"]
                tp["insertion_ps"], tp["insertion_ff_ps"] = tt, round(tt * r, 1)
                tp["budget_owner"] = (f"DIE-S81-16 plan_s11 UNCHECKED: CORES-EARLY-1 rebuilt-insertion estimate {tt} TT "
                                      f"(range 250-320, no signed view yet; FF = TT x plan_s10 ratio {r:.3f}); was {tp['budget_owner'][:120]}")
                stat["tap_insertion_" + m] += 1
out = json.dumps(P, indent=1) + "\n"
Path(a.out).write_text(out)
print("PLAN_EVENT_S11", a.out, "in", hashlib.sha256(raw).hexdigest()[:12], "out", hashlib.sha256(out.encode()).hexdigest()[:12],
      dict(stat), "tap_to_pin_um max", round(max(moves), 4) if moves else 0)
