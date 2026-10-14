#!/usr/bin/env python3
"""In-order engine serialisation of the S81 stage programs, and the SU order that removes most of it (rom-layer-tput,
2026-10-13).

The committed stage programs (results/rtl/s81_ctrl_20261008/programs, tools/s81_ctrl/stage_programs.py) list every
engine's jobs in the golden ASAP start order of the token-path composition, which schedules every operator at
max(end of its predecessors): an engine of unlimited concurrency.  The die's SU slab master runs ONE job at a time, in
program order (ot_s81_su_hctl: e_cmd_ready = !run).  A critical SU job therefore queues behind an off-critical one that
the ASAP order happened to start first (attn.kv_rope_qdq before attn.q_rope; the shared-expert jobs before ffn.swiglu):
cycles that are in no price node.

This tool replays every stage program at its PRICED integer durations with the SU port exclusive and in order
(every other port as the composition has it), and searches the SU port's order (insertion moves, objective: the
stage's critical end, then the sum of ends).  It changes no program; --out writes the per-stage record.

    python3 tools/s81_ctrl/inorder_sched.py [--programs results/rtl/s81_ctrl_20261008/programs] [--out record.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SU = 1


def simulate(ops, su_order):
    """ops: program ops (preds = indices); su_order: SU op indices in issue order.  Returns end[] or None (deadlock)."""
    n = len(ops)
    en = [None] * n
    st = [None] * n
    free = 0
    k = 0
    left = n
    while left:
        moved = False
        for i, o in enumerate(ops):
            if en[i] is not None or o["port"] == SU:
                continue
            if all(en[p] is not None for p in o["preds"]):
                st[i] = max([o["ext"]] + [en[p] for p in o["preds"]])
                en[i] = st[i] + o["dur"]
                left -= 1
                moved = True
        while k < len(su_order):
            i = su_order[k]
            o = ops[i]
            if any(en[p] is None for p in o["preds"]):
                break
            st[i] = max([free, o["ext"]] + [en[p] for p in o["preds"]])
            en[i] = st[i] + o["dur"]
            free = en[i]
            k += 1
            left -= 1
            moved = True
        if not moved:
            return None
    return en


def stage(p):
    ops = p["ops"]
    ids = [o["id"] for o in ops]
    crit_end = p["crit_end"]
    su = [i for i, o in enumerate(ops) if o["port"] == SU]
    # the stage's critical sink: its hand-off (hop port 7), else the last op (the head die)
    hops = [i for i, o in enumerate(ops) if o["port"] == 7]
    sink = hops[-1] if hops else max(range(len(ops)), key=lambda i: ops[i]["end"])

    def cost(order):
        en = simulate(ops, order)
        return None if en is None else (en[sink], sum(en))
    c0 = cost(su)
    best, order = c0, list(su)
    improved = True
    while improved:
        improved = False
        for j in range(len(order)):
            for i in range(len(order)):
                if i == j:
                    continue
                t = list(order)
                t.insert(i, t.pop(j))
                c = cost(t)
                if c is not None and c < best:
                    best, order, improved = c, t, True
    return dict(stage=p["stage"], layers=p.get("layers"), asap=ops[sink]["end"], crit_end=crit_end, inorder=c0[0],
                searched=best[0], su_jobs=len(su), moved=[ids[i] for k, i in enumerate(order) if su[k] != i],
                su_order=[ids[i] for i in order])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--programs", type=Path, default=ROOT / "results/rtl/s81_ctrl_20261008/programs")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    idx = json.loads((a.programs / "index.json").read_text())
    rows = [stage(json.loads((a.programs / f"{s['stage']}.json").read_text())) for s in idx["stages"]]
    tot = {k: sum(r[k] for r in rows) for k in ("asap", "inorder", "searched")}
    rec = dict(schema="opentallas.s81-ctrl.inorder-sched.v1", tool="tools/s81_ctrl/inorder_sched.py",
               programs=str(a.programs.relative_to(ROOT)) if a.programs.is_relative_to(ROOT) else str(a.programs),
               model="priced integer durations; SU port (1) exclusive and in order, every other port as the composition",
               token_cycles=tot,
               su_inorder_added_cycles=tot["inorder"] - tot["asap"],
               su_searched_added_cycles=tot["searched"] - tot["asap"],
               su_inorder_loss_pct=round(100 * (tot["inorder"] - tot["asap"]) / tot["inorder"], 3),
               su_searched_loss_pct=round(100 * (tot["searched"] - tot["asap"]) / tot["searched"], 3),
               stages=rows)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{len(rows)} stages: ASAP {tot['asap']} cycles, SU in order as committed {tot['inorder']} "
          f"(+{tot['inorder'] - tot['asap']}, {rec['su_inorder_loss_pct']} %), SU order searched {tot['searched']} "
          f"(+{tot['searched'] - tot['asap']}, {rec['su_searched_loss_pct']} %)")
    worst = sorted(rows, key=lambda r: r["inorder"] - r["asap"], reverse=True)[:5]
    for r in worst:
        print(f"  {r['stage']} {r.get('layers')}: ASAP {r['asap']} in-order {r['inorder']} searched {r['searched']}")


if __name__ == "__main__":
    main()
