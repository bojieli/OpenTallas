#!/usr/bin/env python3
"""plan_merge3.py BASE OUT ROW_PLAN[:NAME] ... [--whole-lists]

QC-CB-C1L (11-24): three-way compose of die plan rows onto one base event plan.  Each ROW_PLAN is a full plan that a
lane derived from BASE; its delta against BASE (every leaf it adds, changes or removes) is applied onto the running
result in argument order.  Two rows that set the same leaf to different values are a CONFLICT (exit 2): the compose
stops and the later row is rebuilt on the earlier result instead of picking a value by hand.  A row that replaces a
whole subtree another row edited inside (or the reverse) is CONFLICT(sub).  Identical values from two rows merge.

Lists: a list of dicts whose elements carry a unique id (name / conn / inst / id, the keys compose_drop_guard uses) and
whose id sequence is the same in BASE and the row is diffed element by element, so two rows that edit different
hard_cores[] (or different fields of one core) merge; the same field of the same element is a CONFLICT.  A list whose
members are added, removed or reordered, and every other list, is one leaf.  --whole-lists restores the older
behaviour (every list is one leaf; the C1l/C1m composes used it).

Writes OUT (compact JSON, keys in base order then new keys in row order, so the sha is reproducible) and
OUT.report.json (per row: number of leaves, count per top-3 path).  Prints `ROW <name> leaves <n>` per row and
`OUT <path> <sha12>`.  Run compose_drop_guard.py on OUT afterwards."""
import argparse
import hashlib
import json
import sys

ID_KEYS = ("name", "conn", "inst", "id")
MISSING = object()


class Conflict(Exception):
    pass


def idkey(lst):
    """the id key unique on every element of a list of dicts, else None"""
    if not lst or not all(isinstance(e, dict) for e in lst):
        return None
    for k in ID_KEYS:
        v = [e.get(k) for e in lst]
        if all(isinstance(x, str) for x in v) and len(set(v)) == len(v):
            return k
    return None


def diff(b, n, path, out, keyed=True):
    """append (path, new_value) for every leaf where n differs from b; MISSING = removed"""
    if keyed and isinstance(b, list) and isinstance(n, list):
        k = idkey(b)
        if k and idkey(n) == k and [e[k] for e in b] == [e[k] for e in n]:
            for eb, en in zip(b, n):
                diff(eb, en, path + ((k, eb[k]),), out, keyed)
            return
    if isinstance(b, dict) and isinstance(n, dict):
        for k in list(b) + [k for k in n if k not in b]:
            bv, nv = b.get(k, MISSING), n.get(k, MISSING)
            nest = (bv is not MISSING and nv is not MISSING and type(bv) is type(nv)
                    and (isinstance(bv, dict) or (keyed and isinstance(bv, list))))
            if nest:
                diff(bv, nv, path + (k,), out, keyed)
            elif bv != nv:
                out.append((path + (k,), nv))
    elif b != n:
        out.append((path, n))


def _step(d, k):
    if isinstance(k, tuple):
        return next(e for e in d if isinstance(e, dict) and e.get(k[0]) == k[1])
    return d[k]


def setp(d, path, v):
    for k in path[:-1]:
        d = _step(d, k)
    if isinstance(path[-1], tuple):          # an element itself never is a leaf (diff recurses into it)
        raise ValueError(f"keyed element path {path}")
    if v is MISSING:
        d.pop(path[-1], None)
    else:
        d[path[-1]] = v


def fmt(path):
    return "/".join(f"{x[0]}={x[1]}" if isinstance(x, tuple) else str(x) for x in path)


def merge(base, rows, keyed=True):
    """rows = [(name, plan)] -> (result, report); raises Conflict"""
    res = json.loads(json.dumps(base))
    owner, pref, rep = {}, {}, {}
    for name, plan in rows:
        d = []
        diff(base, plan, (), d, keyed)
        rep[name] = {"n": len(d), "top": {}}
        for p, v in d:
            key = fmt(p[:3])
            rep[name]["top"][key] = rep[name]["top"].get(key, 0) + 1
            for q in [p[:i] for i in range(1, len(p) + 1)]:
                if q in owner and owner[q][0] != name:
                    if q == p and owner[q][1] == v:
                        continue
                    raise Conflict(f"CONFLICT {fmt(p)} rows {owner[q][0]} {name}")
            if p in pref and pref[p] != name and p not in owner:
                raise Conflict(f"CONFLICT(sub) {fmt(p)} rows {pref[p]} {name}")
            owner[p] = (name, v)
            for i in range(1, len(p)):
                pref.setdefault(p[:i], name)
            setp(res, p, v)
    return res, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("rows", nargs="+", help="ROW_PLAN[:NAME]")
    ap.add_argument("--whole-lists", action="store_true", help="every list is one leaf (pre-keyed behaviour)")
    a = ap.parse_args(argv)
    base = json.load(open(a.base))
    rows = []
    for arg in a.rows:
        f, _, name = arg.partition(":")
        rows.append((name or f, json.load(open(f))))
    try:
        res, rep = merge(base, rows, keyed=not a.whole_lists)
    except Conflict as e:
        print(e)
        return 2
    for name, r in rep.items():
        print("ROW", name, "leaves", r["n"])
    with open(a.out, "w") as fh:
        fh.write(json.dumps(res, separators=(",", ":")) + "\n")
    with open(a.out + ".report.json", "w") as fh:
        json.dump(rep, fh, indent=1)
    print("OUT", a.out, hashlib.sha256(open(a.out, "rb").read()).hexdigest()[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
