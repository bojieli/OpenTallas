#!/usr/bin/env python3
"""plan_patch.py: carry a plan stage computed on another base onto the composed plan, fail-closed on conflicts.

    plan_patch.py diff BASE.json OUT.json PATCH.json          # recursive dict diff (lists / scalars atomic)
    plan_patch.py apply CUR.json PATCH.json NEW.json [--receipt R.json]

A patch op = {path: [k1, k2, ...], base: <value at BASE or MISSING>, new: <value at OUT or DELETED>}.
apply: at every path CUR must still hold `base` (or already hold `new`: idempotent); otherwise CONFLICT (exit 2,
nothing written).  Receipt: ops applied / already / conflicts, types touched, in/out sha256."""
import hashlib
import json
import sys

MISSING = {"__plan_patch__": "missing"}


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def diff(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b), key=str):
            out += diff(a.get(k, MISSING), b.get(k, MISSING), path + (k,))
        return out
    return [] if a == b else [dict(path=list(path), base=a, new=b)]


def _get(d, path):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return MISSING
        d = d[k]
    return d


def _set(d, path, v):
    for k in path[:-1]:
        d = d.setdefault(k, {})
    if v == MISSING:
        d.pop(path[-1], None)
    else:
        d[path[-1]] = v


def apply(cur, ops):
    done, already, conf = 0, 0, []
    for op in ops:
        have = _get(cur, op["path"])
        if have == op["new"]:
            already += 1
        elif have == op["base"]:
            done += 1
        else:
            conf.append(op["path"])
    if conf:
        return None, dict(conflicts=len(conf), conflict_paths=conf[:50])
    for op in ops:
        _set(cur, op["path"], op["new"])
    types = sorted({op["path"][1] for op in ops if op["path"][:1] == ["partition_types"] and len(op["path"]) > 1})
    top = sorted({op["path"][0] for op in ops if op["path"][:1] != ["partition_types"]})
    return cur, dict(ops=len(ops), applied=done, already=already, conflicts=0, types=types, top_level=top)


def main(a):
    if a[0] == "diff":
        ra, rb = open(a[1], "rb").read(), open(a[2], "rb").read()
        ops = diff(json.loads(ra), json.loads(rb))
        json.dump(dict(base_sha256=_sha(ra), out_sha256=_sha(rb), ops=ops), open(a[3], "w"))
        print("diff ops", len(ops), "base", _sha(ra)[:12], "out", _sha(rb)[:12])
        return 0
    if a[0] == "apply":
        rc = open(a[1], "rb").read()
        P = json.load(open(a[2]))
        new, rep = apply(json.loads(rc), P["ops"])
        rep.update(in_sha256=_sha(rc), patch_base=P["base_sha256"], patch_out=P["out_sha256"])
        if new is None:
            print("CONFLICT", json.dumps(rep)[:2000])
            if "--receipt" in a:
                json.dump(rep, open(a[a.index("--receipt") + 1], "w"), indent=1)
            return 2
        b = json.dumps(new, indent=1).encode()
        open(a[3], "wb").write(b)
        rep["out_sha256"] = _sha(b)
        if "--receipt" in a:
            json.dump(rep, open(a[a.index("--receipt") + 1], "w"), indent=1)
        print("applied", json.dumps({k: v for k, v in rep.items() if k != "types"}), "types", len(rep["types"]))
        return 0
    raise SystemExit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
