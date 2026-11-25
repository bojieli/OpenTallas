#!/usr/bin/env python3
"""plan_patch: apply a row of RFC 6902 ops to a plan with old-value checks, fail-closed (HEAD-TOOLS-FACEGUARD 11-25).

    python3 -I tools/die_plan/plan_patch.py PLAN.json ROW.json [-o OUT.json]

ROW.json = {"row": id, "ops": [{"op": "test"|"replace"|"add"|"remove", "path": "/a/b", "value": v}, ...]}.
Every replace/remove must be preceded by a "test" of the same path with the old value (or carry "old": v, which is
checked the same way); a missing path, a differing old value or an unguarded replace/remove raises PatchError and
nothing is written.  "test" ops alone are a pure precondition row (a tool-side fix whose plan inputs must be as expected).
"""
import argparse
import copy
import json
import os
import sys


class PatchError(ValueError):
    pass


def _walk(doc, path):
    if path == "":
        return None, None, doc
    toks = [t.replace("~1", "/").replace("~0", "~") for t in path.split("/")[1:]]
    cur = doc
    for t in toks[:-1]:
        cur = _child(cur, t, path)
    return cur, toks[-1], _child(cur, toks[-1], path, missing_ok=True)


_MISSING = object()


def _child(cur, tok, path, missing_ok=False):
    if isinstance(cur, dict):
        if tok in cur:
            return cur[tok]
    elif isinstance(cur, list) and tok.isdigit() and int(tok) < len(cur):
        return cur[int(tok)]
    if missing_ok:
        return _MISSING
    raise PatchError(f"path {path}: {tok!r} not found")


def apply_row(plan, row):
    doc = copy.deepcopy(plan)
    tested = {}
    for i, op in enumerate(row["ops"]):
        kind, path = op["op"], op["path"]
        parent, key, cur = _walk(doc, path)
        if kind == "test":
            if cur is _MISSING or cur != op["value"]:
                raise PatchError(f"op {i} test {path}: have {None if cur is _MISSING else cur!r}, want {op['value']!r}")
            tested[path] = True
            continue
        if kind in ("replace", "remove"):
            if "old" in op:
                if cur is _MISSING or cur != op["old"]:
                    raise PatchError(f"op {i} {kind} {path}: old value differs")
            elif not tested.get(path):
                raise PatchError(f"op {i} {kind} {path}: no old-value check (test op or old)")
            if cur is _MISSING:
                raise PatchError(f"op {i} {kind} {path}: missing")
        elif kind == "add":
            if "old" in op or tested.get(path):
                pass
            elif cur is not _MISSING:
                raise PatchError(f"op {i} add {path}: exists (use replace with an old-value check)")
        else:
            raise PatchError(f"op {i}: unknown op {kind!r}")
        if kind == "remove":
            del parent[int(key) if isinstance(parent, list) else key]
        elif isinstance(parent, list) and kind == "add" and cur is _MISSING:
            parent.insert(int(key), op["value"]) if key.isdigit() else parent.append(op["value"])
        elif isinstance(parent, list):
            parent[int(key)] = op["value"]
        else:
            parent[key] = op["value"]
        tested.pop(path, None)
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("row")
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    plan, row = json.load(open(a.plan)), json.load(open(a.row))
    try:
        out = apply_row(plan, row)
    except PatchError as ex:
        print(f"PLAN-PATCH FAIL {row.get('row')}: {ex}")
        return 1
    if a.out:
        json.dump(out, open(a.out + ".tmp", "w"), indent=1)
        os.replace(a.out + ".tmp", a.out)
    print(f"PLAN-PATCH PASS {row.get('row')}: {len(row['ops'])} ops, changed={out != plan}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
