#!/usr/bin/env python3
"""tap_window_floor.py: floor of the per-port kit hold window (HEAD-95 11-12, COORD 07:5x ACCEPTED, all dies).

    tap_window_floor.py PLAN OUT [--kitwin KITWIN.json] [--floor 10] [--margin 10] [--types T1,T2]

CLASS: clock.tap_window.per_port_ps (KW-FIX-4-SDC, die_sta_related --kit-window-out) is the window W_p that the kit SDC
puts on each kit clock port ([-W_p, 0] source latency).  HEAD DIE-HEAD-68 l48ue wrote the RAW measured need (ceil 1 ps)
with no margin, so a port that measured 0 got W_p = 0, and any later clock (die balance) that moves that port by
0.75 ps is a kit-contract violation on a 0-ps window: a missing margin, not a design limit.

RULE (COORD 11-12 07:5x):  W_p = min(per_type_ps[type], max(W_p, need_p + margin, floor))
  need_p = the port's need from KITWIN (die_sta_related --kit-window-out, per_port_ps) when given, else 0;
  the cap per_type_ps[type] (else the die cap T/4 = 208 ps) is never exceeded;
  a window is never lowered (a signed kit closed against a larger window stays valid).
Every change is printed; each changed type's kit SDC changes, so that type needs a re-sign.
"""
import argparse
import json
import sys

DIE_CAP_PS = 208.0     # T/4 at 833 ps (gen_phys: window_ps <= T/4)


def floor_windows(plan, kitwin=None, floor=10.0, margin=10.0, types=None):
    """in place on plan (raw JSON dict) -> [(type, port, old, new)]"""
    tw = (plan.get("clock") or {}).get("tap_window")
    if not tw:
        return []
    pt = tw.get("per_type_ps") or {}
    need = (kitwin or {}).get("per_port_ps") or {}
    changes = []
    for tn, ports in sorted((tw.get("per_port_ps") or {}).items()):
        if types and tn not in types:
            continue
        cap = float(pt.get(tn, DIE_CAP_PS))
        for p in sorted(ports):
            w = float(ports[p])
            n = float((need.get(tn) or {}).get(p, 0.0))
            nw = min(cap, max(w, n + margin, floor))
            if nw > w:
                ports[p] = nw
                changes.append((tn, p, w, nw))
    if changes:
        tw["per_port_note"] = (tw.get("per_port_note", "") + " | TAPWIN-FLOOR (HEAD-95 11-12, COORD 07:5x): per_port "
                               f"W = min(per_type, max(W, need + {margin:g}, {floor:g})); {len(changes)} ports raised").strip(" |")
    return changes


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--kitwin", help="die_sta_related --kit-window-out JSON (per-port needs on the clock of record)")
    ap.add_argument("--floor", type=float, default=10.0)
    ap.add_argument("--margin", type=float, default=10.0)
    ap.add_argument("--types", help="comma list (default: every type in per_port_ps)")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    kw = json.load(open(a.kitwin)) if a.kitwin else None
    ch = floor_windows(plan, kw, a.floor, a.margin, set(a.types.split(",")) if a.types else None)
    with open(a.out, "w") as f:
        json.dump(plan, f, indent=1)
        f.write("\n")
    for c in ch:
        print("W %s.%s %g -> %g" % c)
    print("changed", len(ch), "types", sorted({c[0] for c in ch}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
