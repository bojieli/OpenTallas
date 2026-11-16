#!/usr/bin/env python3
"""S81-LEAF-PLAN 11-15 (COORD r88, E2): merge several lanes' partition_types row files into ONE leaf delta on a base
plan by a 3-way merge per field.

Each row file is {type: full partition_types row} written against BASE (or against its own --base-of plan).  For
every type the change of each row file is the set of leaf paths where row != its base; a leaf is a scalar, an [x, y]
point, a list whose length changed, or a dict key added / removed.  Changes are applied in the order given; a path
already changed by an earlier file to a DIFFERENT value is a conflict (kept at the earlier value, listed), the same
value is a no-op.  Types and paths no file touches stay byte-equal to BASE.

    rows_merge.py BASE OUT LEDGER ROWS[@ROWBASE] [ROWS[@ROWBASE] ...]
Exit 0 with no conflicts, 3 with conflicts (OUT still written).
"""
import json
import sys
from pathlib import Path

MISSING = object()


def is_point(v):
    return isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)


def changes(base, new, path=()):
    """[(path, old, new)] leaf changes from base to new."""
    if base == new:
        return []
    if isinstance(base, dict) and isinstance(new, dict):
        out = []
        for k in list(base) + [k for k in new if k not in base]:
            out += changes(base.get(k, MISSING), new.get(k, MISSING), path + (k,))
        return out
    if isinstance(base, list) and isinstance(new, list) and len(base) == len(new) and not is_point(base):
        out = []
        for i, (a, b) in enumerate(zip(base, new)):
            out += changes(a, b, path + (i,))
        return out
    return [(path, base, new)]


def get(o, path):
    for k in path:
        if isinstance(o, dict):
            if k not in o:
                return MISSING
            o = o[k]
        elif isinstance(o, list) and isinstance(k, int) and k < len(o):
            o = o[k]
        else:
            return MISSING
    return o


def put(o, path, v):
    for k in path[:-1]:
        o = o[k]
    if v is MISSING:
        del o[path[-1]]
    else:
        o[path[-1]] = v


def main(argv=None):
    a = argv if argv is not None else sys.argv[1:]
    if len(a) < 4:
        print(__doc__); return 2
    base_p, out_p, led_p, rows = a[0], a[1], a[2], a[3:]
    base = json.loads(Path(base_p).read_text())
    plan = json.loads(json.dumps(base))
    T = plan["partition_types"]
    owner = {}                       # (type, path) -> (file, value)
    led = dict(files=[], conflicts=[], types={})
    for spec in rows:
        f, _, rb = spec.partition("@")
        R = json.loads(Path(f).read_text())
        RB = json.loads(Path(rb).read_text())["partition_types"] if rb else base["partition_types"]
        n_ch = n_ok = 0
        for tn, row in R.items():
            if tn not in RB or tn not in T:
                led["conflicts"].append(dict(file=f, type=tn, path=[], why="type not in base / plan")); continue
            for path, old, new in changes(RB[tn], row):
                n_ch += 1
                cur = get(T[tn], path)
                key = (tn, path)
                if cur == new:
                    n_ok += 1; continue
                if key in owner and owner[key][1] != new:
                    led["conflicts"].append(dict(file=f, type=tn, path=list(path), kept_from=owner[key][0],
                                                 kept=owner[key][1], dropped=None if new is MISSING else new)); continue
                if cur != old and key not in owner:
                    led["conflicts"].append(dict(file=f, type=tn, path=list(path), why="base drift", base=old,
                                                 current=None if cur is MISSING else cur)); continue
                try:
                    put(T[tn], path, new)
                except (KeyError, IndexError, TypeError):
                    # parent missing (a list another file resized): take the row's whole parent value
                    led["conflicts"].append(dict(file=f, type=tn, path=list(path), why="parent changed shape")); continue
                owner[key] = (f, new); n_ok += 1
                led["types"].setdefault(tn, set()).add(f)
        led["files"].append(dict(file=f, base=rb or base_p, types=len(R), changes=n_ch, applied=n_ok))
    led["types"] = {k: sorted(v) for k, v in led["types"].items()}
    led["multi_owner_types"] = {k: v for k, v in led["types"].items() if len(v) > 1}
    Path(out_p).write_text(json.dumps(plan) + "\n")
    Path(led_p).write_text(json.dumps(led, indent=1, default=str) + "\n")
    print("ROWS_MERGE files %d, types %d (multi-owner %d), conflicts %d" % (
        len(rows), len(led["types"]), len(led["multi_owner_types"]), len(led["conflicts"])))
    return 3 if led["conflicts"] else 0


if __name__ == "__main__":
    sys.exit(main())
