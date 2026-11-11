#!/usr/bin/env python3
"""BIND-SUBTYPE-2 11-11 (HBM hub K-way split, DIE-HBM-100 / HBM-HUB-ARCH-2): as-built manifest for a plan that splits a
hub partition into K partitions by connectivity.

    hbm_hub_split_asbuilt.py BASE_AB OUT_AB OUT_MAP SPLIT.json [SPLIT.json ...]

The binder places every as-built cell by asbuilt map.parts (inline map + map_file): {as-built path: partition or
[partition, local name]}, a key covering its descendants.  A split is therefore a pure map change: every key of the
parent partition moves to the group partition that SPLIT names, the local name unchanged.  SPLIT
(opentallas.hbm.hub_split_map.v1): {"parent_partition", "parent_type", "groups": {k: {"partition", "type",
"map_keys": [...]}}}.

Fails closed: a parent key in no group or in two, a group key that is not a parent key, a map rule (regex) that
resolves to the parent, a group partition that already exists in the map.  Rows naming the parent type in a "types"
list (declared_ties) also name every group type.  Other manifest fields that mention the parent partition or type
are listed (not changed) in OUT_AB.note_hub_split_review.  OUT_MAP is a complete map_file (parts + rules); OUT_AB
points to it and drops its inline map entries for the moved keys.
"""
import argparse
import copy
import json
from pathlib import Path


class SplitError(Exception):
    pass


def part_of(v):
    return v[0] if isinstance(v, list) else v


def split_parts(parts, rules, split):
    P = split["parent_partition"]
    owned = {k for k, v in parts.items() if part_of(v) == P}
    if any(part_of(v) == P or v == P for _, v in rules):
        raise SplitError(f"{P}: a map rule resolves to the parent partition; list its paths as keys first")
    have = {part_of(v) for v in parts.values()}
    seen, moved = {}, {}
    for gk, g in sorted(split["groups"].items()):
        if g["partition"] in have:
            raise SplitError(f"group partition {g['partition']} already in the map")
        for key in g["map_keys"]:
            if key in seen:
                raise SplitError(f"{key}: in group {seen[key]} and {gk}")
            if key not in owned:
                raise SplitError(f"{key}: not a {P} map key")
            seen[key] = gk
            v = parts[key]
            moved[key] = [g["partition"], v[1]] if isinstance(v, list) and len(v) > 1 else g["partition"]
    missing = sorted(owned - set(seen))
    if missing:
        raise SplitError(f"{P}: {len(missing)} keys in no group, e.g. {missing[:5]}")
    return moved


def build(ab, splits):
    out = copy.deepcopy(ab)
    mp = dict(ab.get("map", {}))
    mf = json.loads(Path(ab["map_file"]).read_text()) if ab.get("map_file") else {}
    parts = {**mf.get("parts", {}), **mp.get("parts", {})}
    rules = list(mp.get("rules", [])) + list(mf.get("rules", []))
    stats, review = [], []
    for s in splits:
        moved = split_parts(parts, rules, s)
        parts.update(moved)
        gtypes = [g["type"] for _, g in sorted(s["groups"].items())]
        n_ties = 0
        for row in out.get("declared_ties", []):
            if s["parent_type"] in row.get("types", []):
                row["types"] = row["types"] + [t for t in gtypes if t not in row["types"]]
                n_ties += 1
        for k, v in out.items():
            if k in ("declared_ties", "map", "map_file"):
                continue
            t = json.dumps(v)
            if s["parent_partition"] in t or f'"{s["parent_type"]}"' in t:
                review.append(f"{k} names {s['parent_partition']}/{s['parent_type']}")
        stats.append(dict(parent=s["parent_partition"], keys=len(moved), groups={g["partition"]: len(g["map_keys"])
                     for _, g in sorted(s["groups"].items())}, declared_ties_rows=n_ties))
    out_map = dict(parts=parts, rules=[list(r) for r in mf.get("rules", [])])
    if "map" in out:
        out["map"] = dict(mp, parts={k: v for k, v in mp.get("parts", {}).items()
                                     if part_of(v) == part_of(parts[k])})
    out["note_hub_split"] = stats
    out["note_hub_split_review"] = sorted(set(review))
    return out, out_map


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base")
    ap.add_argument("out_ab")
    ap.add_argument("out_map")
    ap.add_argument("splits", nargs="+")
    a = ap.parse_args()
    ab = json.loads(Path(a.base).read_text())
    splits = [json.loads(Path(f).read_text()) for f in a.splits]
    try:
        out, out_map = build(ab, splits)
    except SplitError as e:
        raise SystemExit(f"HUB_SPLIT_FAIL {e}")
    Path(a.out_map).write_text(json.dumps(out_map, indent=0) + "\n")
    out["map_file"] = str(Path(a.out_map).resolve())
    Path(a.out_ab).write_text(json.dumps(out, indent=1) + "\n")
    print("HUB_SPLIT_OK", json.dumps(out["note_hub_split"]), "review:", out["note_hub_split_review"])


if __name__ == "__main__":
    main()
