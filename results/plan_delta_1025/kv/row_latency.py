#!/usr/bin/env python3
"""Vendored from claude/kv-plan3f-1025 g3/row_latency_v39f.py (PLAN-DELTA/KV 10-25: FAMILY + kv3_hg_v1_r2; v39e/v39f fields = before/after).
KV-PLAN3F 10-25: the per-row latency the compiler schedules for the KV head-group rows (plan v3.9f), replacing the R8
per-row alignment pads of v3.9e (TYPE-REDUCE KV item 1, COORD-approved; consumer: KV-TOK static schedule).

Input: the v3.9e and v3.9f R8 landing tables (tools/die_plan/r8.py pads: members[].landed = the depth the compiler
schedules, in cycles from the source leaf's output register to the sink leaf's input, landing pad included) and the
v3.9f plan.  Output (schema opentallas.die_plan.row_latency.v1):
  changed[]   every member whose landed depth differs v3.9e -> v3.9f (the removed pads), with the old and new depth;
  rows{}      per hg row 0..7 and quadrant, the landed depth of the row-scheduled buses (astk ep chain xi / zi from the row
              above, ep cal_exp from kvs_attn, ep qi from the astk ctl, ectl cfg / epoch / kgo / layer from kvs_hroot) and
              the as-built offsets the old pads kept (xi - zi, cfg - epoch) next to the v3.9f ones;
  summary     pad change on the changed members (bits, flops; negative = more pads), die pad flops v3.9e -> v3.9f,
              max |delta|, rows touched, members outside the hg family (fwd_reach stations change those).
The compiler must schedule each (row, quadrant) bus at its v3.9f `landed` depth; nothing else in the die moved.

    row_latency_v39f.py OLD_LANDING.json NEW_LANDING.json PLAN_V39F.json --out row_latency.json
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

FAMILY = ("kv3_hg", "kv3_hg_v1", "kv3_hg_v1_r2", "kv3_hg_v3")   # PLAN-DELTA/KV: + merged row type kv3_hg_v1_r2
ROW_BUSES = [("xi", r"\.xi\["), ("zi", r"\.zi\["), ("cal_exp", r"\.cal_exp\["), ("qi", r"\.qi\["),
             ("cfg", r"^ectl_[A-Z]+_\d+\.cfg\["), ("epoch", r"^ectl_[A-Z]+_\d+\.epoch\["),
             ("kgo", r"^ectl_[A-Z]+_\d+\.kgo\["), ("layer", r"^ectl_[A-Z]+_\d+\.layer\[")]


def nbits(rs):
    return sum(b - a + 1 for a, b in rs)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    old = json.loads(Path(a.old).read_text())
    new = json.loads(Path(a.new).read_text())
    plan = json.loads(Path(a.plan).read_text())
    pt = {p["name"]: p["type"] for p in plan["partitions"]}
    O = {m["id"]: m for m in old["members"]}
    changed, flops, bits = [], 0, 0
    for m in new["members"]:
        o = O.get(m["id"])
        if o is None or o["landed"] == m["landed"]:
            continue
        nb = nbits(m["sink_bits"])
        changed.append(dict(sink_part=m["sink_part"], type=pt.get(m["sink_part"]), sink=f"{m['sink']}.{m['sink_port']}",
                            bits=m["sink_bits"], width=nb, source=m["source"], lane=m.get("lane"),
                            asbuilt=m["asbuilt"], bound=m["bound"], pad_v39e=o["pad"], pad_v39f=m["pad"],
                            landed_v39e=o["landed"], landed_v39f=m["landed"], delta=m["landed"] - o["landed"]))
        flops += nb * (o["pad"] - m["pad"])
        bits += nb if o["pad"] != m["pad"] else 0
    missing = sorted(set(O) - {m["id"] for m in new["members"]})
    rows = defaultdict(lambda: defaultdict(dict))
    for m in new["members"]:
        if pt.get(m["sink_part"]) not in FAMILY or not m["sink_part"].startswith("hg_"):
            continue
        _, q, r = m["sink_part"].split("_")
        mid = f"{m['sink']}.{m['sink_port']}["
        for key, rx in ROW_BUSES:
            if re.search(rx, mid) and (key not in ("xi", "zi") or "g_ep_" in m["sink"]):
                o = O.get(m["id"], {})
                rows[int(r)][q][key] = dict(landed=m["landed"], landed_v39e=o.get("landed"), asbuilt=m["asbuilt"],
                                            source=m["source"], width=nbits(m["sink_bits"]), lane=m.get("lane"))
    for r, qs in rows.items():
        for q, d in qs.items():
            for x, y in (("xi", "zi"), ("cfg", "epoch")):
                if x in d and y in d:
                    d[f"{x}_minus_{y}"] = dict(asbuilt=d[x]["asbuilt"] - d[y]["asbuilt"],
                                              v39e=(d[x]["landed_v39e"] - d[y]["landed_v39e"])
                                              if d[x]["landed_v39e"] is not None and d[y]["landed_v39e"] is not None
                                              else None,
                                              v39f=d[x]["landed"] - d[y]["landed"])
    out = dict(
        schema="opentallas.die_plan.row_latency.v1", die=plan["die"]["name"], plan="v3.9pd (PLAN-DELTA/KV; v39e = before = v3.9, v39f = after)",
        consumer="KV-TOK (Qwen KV static schedule): schedule every (row, quadrant) bus below at its v3.9f landed depth; "
                 "the per-row R8 alignment pads of v3.9e (hg_v1_r1..r5 / hg_v2 / hg_v3 types) are removed and these "
                 "depths replace them (TYPE-REDUCE KV item 1, COORD 10-25).",
        units="cycles (1.2 GHz die clock) from the source leaf output register to the sink leaf input, landing pad "
              "included (= r8 landing members[].landed)",
        sources=dict(old=str(a.old), new=str(a.new), plan=str(a.plan), old_digest=old.get("bus_groups_digest"),
                     new_digest=new.get("bus_groups_digest")),
        summary=dict(changed_members=len(changed), pad_changed_bits=bits, pad_flops_removed_on_changed=flops,
                     max_abs_delta=max((abs(c["delta"]) for c in changed), default=0),
                     rows_touched=sorted({int(c["sink_part"].split("_")[-1]) for c in changed
                                          if c["sink_part"].startswith("hg_")}),
                     non_family_changes=sum(1 for c in changed if c["type"] not in FAMILY),
                     members_missing_in_new=len(missing),
                     pad_flops_die=dict(v39e=old["summary"]["pad_flops"], v39f=new["summary"]["pad_flops"])),
        changed=sorted(changed, key=lambda c: (c["sink_part"], c["sink"])),
        rows={str(r): {q: rows[r][q] for q in sorted(rows[r])} for r in sorted(rows)})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    s = out["summary"]
    print(f"row_latency: {s['changed_members']} members changed (rows {s['rows_touched']}), pad flops die "
          f"{s['pad_flops_die']['v39e']} -> {s['pad_flops_die']['v39f']}, max |delta| {s['max_abs_delta']}, non-family changes {s['non_family_changes']}")


if __name__ == "__main__":
    main()
