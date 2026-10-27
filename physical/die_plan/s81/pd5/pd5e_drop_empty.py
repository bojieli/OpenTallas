#!/usr/bin/env python3
"""S81-UNBLOCK-2 10-27: PD5d -> PD5e: remove EMPTY partitions from the PD5 composed plan.

An empty partition = no plan port starts or ends on it, its type has no contents and no hard cores, and the reset
wavefront gives it no children (it would only receive rst and drive nothing).  The PD5 phy-fit left exactly one:
s_4N_x06 (slice_station__t48_phy1026_s_4N_x06, 1442.88 x 1226.88 um, contents []), which the strict bind refuses
(EMPTY_PARTITION + "wavefront reset carriers lack bound partitions").  It is a dead slot, not a station: dropping it
changes no lane, no latency and no other type (its wavefront parent loses one rst_o leaf output).
  python3 pd5e_drop_empty.py IN_PLAN OUT_PLAN
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools" / "die_plan"))


def main(src, dst):
    import schema
    import reset_tree as RT
    raw = json.load(open(src))
    used = {q[e]["part"] for q in raw["ports"] for e in ("src", "dst")}
    W = RT.wf_plan(schema.Plan(json.load(open(src)), src))
    parents = {v.get("parent") for v in W["parts"].values()}
    drop = []
    for x in raw["partitions"]:
        t = raw["partition_types"][x["type"]]
        if x["name"] in used or t.get("contents") or t.get("hard_cores") or x["name"] in parents:
            continue
        drop.append(x["name"])
    types = {x["type"] for x in raw["partitions"] if x["name"] in drop}
    raw["partitions"] = [x for x in raw["partitions"] if x["name"] not in drop]
    left = {x["type"] for x in raw["partitions"]}
    gone = sorted(t for t in types if t not in left)
    for t in gone:
        del raw["partition_types"][t]
        raw["reset"].get("in_sites", {}).pop(t, None)
    raw["note"] = raw.get("note", "") + f" | PD5e (S81-UNBLOCK-2 10-27): empty partitions removed {drop} (types {gone})."
    Path(dst).write_text(json.dumps(raw, indent=1) + "\n")
    print(json.dumps(dict(dropped=drop, types=gone, out=dst, sha256=hashlib.sha256(Path(dst).read_bytes()).hexdigest())))


if __name__ == "__main__":
    main(*sys.argv[1:3])
