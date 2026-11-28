#!/usr/bin/env python3
"""plan_merge3.py BASE OUT ROW_PLAN[:NAME]@ANC ... [--whole-lists]

QC-CB-C1L (11-24): three-way compose of die plan rows onto one base event plan.  Each ROW_PLAN is a full plan that a
lane derived from its fork ancestor ANC (BASE itself, or an older plan); its delta against ANC (every leaf it adds,
changes or removes) is applied onto the running result in argument order.  Two rows that set the same leaf to different values are a CONFLICT (exit 2): the compose
stops and the later row is rebuilt on the earlier result instead of picking a value by hand.  A row that replaces a
whole subtree another row edited inside (or the reverse) is CONFLICT(sub).  Identical values from two rows merge.

Lists: a list of dicts whose elements carry a unique id (name / conn / inst / id, the keys compose_drop_guard uses) and
whose id sequence is the same in BASE and the row is diffed element by element, so two rows that edit different
hard_cores[] (or different fields of one core) merge; the same field of the same element is a CONFLICT.  A list whose
members are added, removed or reordered, and every other list, is one leaf.  --whole-lists restores the older
behaviour (every list is one leaf; the C1l/C1m composes used it).

Fork ancestor (C-MERGE3-BASE-HIDES-FORK-CONFLICT, HEAD-EAST-R4 11-27, blocking): every row names the plan it was
forked from, `ROW_PLAN[:NAME]@ANC` (ANC = a plan path, or the literal `base` when the row was derived from BASE
itself).  The row's delta is taken against ANC, not BASE.  When ANC is not BASE, a delta leaf whose BASE value moved
since ANC (BASE changed it too) and differs from the row's value is CONFLICT(fork) (exit 2): diffing such a row
against BASE alone made it look like a row-only edit and the row won silently (the 4 hd_lep0N strap_ca_k_* sites_um
of the W11-forked EAST row composed onto W12f).  A row leaf under a path BASE replaced, removed or retyped since ANC
(or a row subtree BASE edited inside) is CONFLICT(fork) too.  BASE-only changes since ANC are kept.  Fork conflicts
of all rows are listed at once.  Refused (exit 3): a row without @ANC (a lineage-base mismatch cannot be seen from
the plans), an unreadable ROW/ANC, a forked row with 0 leaves (wrong ancestor), a duplicate row NAME or the name
BASE.  The report records each row's ANC sha12.  Paths must not contain '@' or ':' (use ./base for a file named base).

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
        m = [e for e in d if isinstance(e, dict) and e.get(k[0]) == k[1]]
        if len(m) > 1:
            raise Conflict(f"CONFLICT(dup-id) {k[0]}={k[1]} matches {len(m)} elements")
        if not m:
            raise StopIteration(k)
        return m[0]
    return d[k]


def setp(d, path, v):
    for k in path[:-1]:
        try:
            d = _step(d, k)
        except (KeyError, IndexError, TypeError, StopIteration):
            if v is MISSING:                 # removing a key whose parent is already gone: no-op
                return
            raise
    if isinstance(path[-1], tuple):          # an element itself never is a leaf (diff recurses into it)
        raise ValueError(f"keyed element path {path}")
    if v is MISSING:
        d.pop(path[-1], None)
    else:
        d[path[-1]] = v


def getp(d, path):
    """value at path, MISSING when any step is absent"""
    for k in path:
        try:
            d = _step(d, k)
        except (KeyError, IndexError, TypeError, StopIteration):
            return MISSING
    return d


def fmt(path):
    return "/".join(f"{x[0]}={x[1]}" if isinstance(x, tuple) else str(x) for x in path)


BASE_ANC = "base"


def _under(p, q):
    """q is a proper prefix of p"""
    return len(q) < len(p) and p[:len(q)] == q


def merge(base, rows, keyed=True):
    """rows = [(name, plan, anc)], anc = fork-ancestor plan or BASE_ANC -> (result, report); raises Conflict"""
    res = json.loads(json.dumps(base))
    owner, pref, rep, deltas, fk = {}, {}, {}, [], []
    for row in rows:
        if len(row) != 3:
            raise ValueError(f"row {row[0]!r}: pass (name, plan, anc); anc = fork ancestor or BASE_ANC")
        name, plan, anc = row
        forked = anc != BASE_ANC
        anc = anc if forked else base
        d = []
        diff(anc, plan, (), d, keyed)
        deltas.append((name, d))
        rep[name] = {"n": len(d), "top": {}, "fork": forked}
        if forked:                               # pre-pass: every fork conflict of every row, listed at once
            db = []
            diff(anc, base, (), db, keyed)
            dbp = [q for q, _ in db]
            for p, v in d:
                bv = getp(base, p)
                if (bv != getp(anc, p) and bv != v) or any(_under(p, q) or _under(q, p) for q in dbp):
                    fk.append(f"CONFLICT(fork) {fmt(p)} rows BASE {name}")
    if fk:
        raise Conflict("\n".join(fk))
    for name, d in deltas:
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
    ap.add_argument("rows", nargs="+", help="ROW_PLAN[:NAME]@ANC (ANC = fork-ancestor plan path, or base)")
    ap.add_argument("--whole-lists", action="store_true", help="every list is one leaf (pre-keyed behaviour)")
    a = ap.parse_args(argv)
    base = json.load(open(a.base))
    rows, ancsha = [], {}
    sha = lambda f: hashlib.sha256(open(f, "rb").read()).hexdigest()[:12]
    for arg in a.rows:
        spec, at, anc = arg.rpartition("@")
        if not at or not anc or not spec:
            print(f"REFUSE row {arg}: name its fork ancestor as ROW_PLAN[:NAME]@ANC (ANC = plan path or base)")
            return 3
        f, _, name = spec.partition(":")
        name = name or f
        if name == "BASE" or name in ancsha:
            print(f"REFUSE row {arg}: row name {name!r} is reserved or used twice")
            return 3
        try:
            rows.append((name, json.load(open(f)), BASE_ANC if anc == "base" else json.load(open(anc))))
            ancsha[name] = "base" if anc == "base" else sha(anc)
        except (OSError, ValueError) as e:
            print(f"REFUSE row {arg}: {e}")
            return 3
    try:
        res, rep = merge(base, rows, keyed=not a.whole_lists)
    except Conflict as e:
        print(e)
        return 2
    for name, r in rep.items():
        r["anc"] = ancsha[name]
        if r["fork"] and r["n"] == 0:
            print(f"REFUSE row {name}: 0 leaves against its fork ancestor {ancsha[name]} (wrong ancestor?)")
            return 3
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
