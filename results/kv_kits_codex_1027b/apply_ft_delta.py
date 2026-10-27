#!/usr/bin/env python3
"""Apply the prescribed reach405 FT delta to a KV plan, preserving all unrelated keys.
This is a pending plan event input. R8 tables and compiler/model ledger must travel with it.
"""
import argparse, copy, json
from pathlib import Path


def apply(raw, delta):
    raw = copy.deepcopy(raw)
    expected = {(r["type"], r["slot"]): r for r in delta["slot_changes"]}
    changes = []
    for tn, part in delta["type_slices"].items():
        typ = raw["partition_types"][tn]
        if typ["outline_um"] != part["outline_um"]:
            raise ValueError(f"{tn}: outline changed; re-site against current geometry")
        old = {s["name"]: s for s in typ["ft_slots"]}
        new = {s["name"]: s for s in part["ft_slots"]}
        if old.keys() != new.keys():
            raise ValueError(f"{tn}: FT slot inventory changed")
        for sn, sl in old.items():
            ns = new[sn]
            for key in ("width", "in_face", "out_face"):
                if sl[key] != ns[key]:
                    raise ValueError(f"{tn}/{sn}: {key} changed")
            row = expected.get((tn, sn))
            want = row["old_stations"] if row else ns["stations"]
            current = sl["stations"]
            if current != want:
                raise ValueError(f"{tn}/{sn}: stations changed {current} != {want}")
            if row:
                if ns["stations"] != row["new_stations"] or row["new_stations"] - want != 1:
                    raise ValueError(f"{tn}/{sn}: delta must be exactly +1")
                changes.append((tn, sn))
        typ["ft_slots"] = copy.deepcopy(part["ft_slots"])
    if set(changes) != set(expected):
        raise ValueError("slot changes incomplete")
    return raw


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan"); ap.add_argument("delta"); ap.add_argument("out")
    a = ap.parse_args()
    Path(a.out).write_text(json.dumps(apply(json.loads(Path(a.plan).read_text()), json.loads(Path(a.delta).read_text())), indent=0)+"\n")
