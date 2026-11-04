#!/usr/bin/env python3
"""DH58-RF2 (11-03): plan-time estimate of the reset LEAF hop (CTS check OT_RESET_TREE LEAF, limit 405 um) for every
generated (non-hard) type of a die plan, before any build.

The CTS check (tools/die_plan/reset_taps.tcl, rt_postplace) measures, for every placed flop whose reset pin hangs on a
terminal net rst_n_t<i>, the Manhattan distance to the NEAREST same-polarity terminal launch flop; > reach = FAIL.
Those control sinks are (a) ft-slot station epoch flops (u_ft_<slot>_s<j>/eq), which global placement strings along the
in-window -> out-window line, and (b) face / pin registers at the bus and slot windows.  The estimate uses:

  terminals  the reset tree's terminal relays (reset_tree.for_type: relays whose q is rst_n_t<i>, i < reset consumer
             count), at their plan positions (clock-tap and reset.local_taps_um terminals);
  stations   slot s with k stations: station j at fraction (j + 1) / (k + 1) of the straight line between the in- and
             out-window centres on their faces (l48rf hd_ctl_n w3d placed s0..s4 at 0.20 / 0.37 / 0.55 / 0.72 / 0.89);
  faces      both ends and the centre of every bus / slot window on its face;
  interior   INFO only: worst free point of the outline on an 8.64-um grid (any flop anywhere).

usage: head_reset_hop_estimate.py PLAN.json [--reach 405] [--types a,b] [--out EST.json] [--tools TOOLS_ROOT]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("plan", type=Path)
ap.add_argument("--reach", type=float, default=405.0)
ap.add_argument("--types")
ap.add_argument("--out", type=Path)
ap.add_argument("--tools", default=os.environ.get("RF_TOOL_ROOT") or str(Path(__file__).resolve().parents[2]))
ap.add_argument("--grid", type=float, default=8.64)
a = ap.parse_args()
sys.path.insert(0, str(Path(a.tools) / "tools" / "die_plan"))
import schema as S        # noqa: E402
import reset_tree as RT   # noqa: E402

P = S.Plan(json.loads(a.plan.read_text()), a.plan.resolve())


def face_pt(face, v, W, H):
    return {"W": (0.0, v), "E": (W, v), "S": (v, 0.0), "N": (v, H)}[face]


def man(p, q):
    return abs(p[0] - q[0]) + abs(p[1] - q[1])


rows, fails = {}, []
for tn in sorted(a.types.split(",") if a.types else P.types):
    t = P.types[tn]
    if t.get("hard"):
        continue
    try:
        T = RT.for_type(P, tn)
    except Exception as e:                       # noqa: BLE001 - report, never hide
        rows[tn] = dict(error=f"{type(e).__name__}: {e}")
        fails.append(tn)
        continue
    W, H = t["outline_um"]
    ncons = RT.consumer_count(T)
    term = []
    for r in T["relays"]:
        m = re.fullmatch(r"rst_n_t(\d+)", r.get("q", ""))
        if m and int(m.group(1)) < ncons:
            term.append((int(m.group(1)), tuple(r["xy"])))
    if not term:
        rows[tn] = dict(error="no terminal relays")
        fails.append(tn)
        continue
    sinks = []
    for s in t.get("ft_slots", []):
        a0 = face_pt(s["in_face"], sum(s["in_window_um"]) / 2, W, H)
        b0 = face_pt(s["out_face"], sum(s["out_window_um"]) / 2, W, H)
        k = int(s.get("stations", 1))
        for j in range(k):
            f = (j + 1) / (k + 1)
            sinks.append((f"ft:{s['name']}.s{j}", (a0[0] + f * (b0[0] - a0[0]), a0[1] + f * (b0[1] - a0[1]))))
        for nm, fc, win in (("in", s["in_face"], s["in_window_um"]), ("out", s["out_face"], s["out_window_um"])):
            for v in (win[0], (win[0] + win[1]) / 2, win[1]):
                sinks.append((f"face:{s['name']}_{nm}", face_pt(fc, v, W, H)))
    for b in t.get("buses", []):
        if b.get("face") and b.get("window_um"):
            for v in (b["window_um"][0], sum(b["window_um"]) / 2, b["window_um"][1]):
                sinks.append((f"face:{b['name']}", face_pt(b["face"], v, W, H)))
    worst = None
    for nm, p in sinks:
        d, i = min((man(p, q), i) for i, q in term)
        if worst is None or d > worst[0]:
            worst = (round(d, 2), nm, [round(p[0], 2), round(p[1], 2)], i)
    boxes = RT.blockages(t)
    inter = 0.0
    y = 0.0
    while y <= H:
        x = 0.0
        while x <= W:
            if not any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes):
                inter = max(inter, min(man((x, y), q) for _, q in term))
            x += a.grid
        y += a.grid
    st = [d for d in [min(man(p, q) for _, q in term) for nm, p in sinks if nm.startswith("ft:")]]
    rows[tn] = dict(outline_um=[W, H], terminals=len(term), local_taps=len((t.get("reset") or {}).get("local_taps_um") or []),
                    worst_sink_um=worst[0] if worst else None, worst_sink=worst[1] if worst else None,
                    worst_sink_xy=worst[2] if worst else None, nearest_terminal=worst[3] if worst else None,
                    worst_station_um=round(max(st), 2) if st else None, interior_worst_um_info=round(inter, 2),
                    verdict=("FAIL" if worst and worst[0] > a.reach else "PASS"))
    if worst and worst[0] > a.reach:
        fails.append(tn)
res = dict(schema="opentallas.head_reset_hop_estimate.v1", plan=str(a.plan), reach_um=a.reach, types=rows,
           over_reach=sorted(fails),
           method="terminal relays (reset_tree.for_type) vs ft stations on the in->out window line + face windows; "
                  "interior grid INFO")
txt = json.dumps(res, indent=1)
if a.out:
    a.out.write_text(txt + "\n")
for tn, r in rows.items():
    print(f"{tn:22s} {r.get('verdict', 'ERROR'):5s} sink {r.get('worst_sink_um')} ({r.get('worst_sink')}) station "
          f"{r.get('worst_station_um')} interior {r.get('interior_worst_um_info')} terms {r.get('terminals')} "
          f"local {r.get('local_taps')} {r.get('error', '')}")
print("OVER_REACH", res["over_reach"])
