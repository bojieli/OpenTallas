"""HBM-BIND-10: fine-grained die_plan.json delta base -> new, and apply with per-item base checks (fail closed, lists it).
  python3 plan_delta.py make  BASE.json NEW.json DELTA.json.gz
  python3 plan_delta.py apply BASE.json DELTA.json.gz OUT.json
Recursive: dicts by key, lists of objects with a unique id/name by that id (order kept from NEW), other values whole.
An op records the sha of the base item it replaces; apply reports every op whose base item differs (a conflict
with a concurrent event) and still applies it, so the conflicts can be read and resolved by hand."""
import json, gzip, hashlib, sys
DEL = "__DEL__"
def h(x): return hashlib.sha256(json.dumps(x, sort_keys=True).encode()).hexdigest()[:16]
def idk(lst):
    for k in ("id", "name", "inst", "conn"):
        if lst and all(isinstance(e, dict) and k in e for e in lst) and len({e[k] for e in lst}) == len(lst): return k
    return None
def diff(x, y, path, ops, depth):
    if x == y: return
    if depth < 5 and isinstance(x, dict) and isinstance(y, dict):
        for s in list(x) + [s for s in y if s not in x]:
            if s not in y: ops.append(["set", path + [s], h(x[s]), DEL])
            elif s not in x: ops.append(["set", path + [s], None, y[s]])
            else: diff(x[s], y[s], path + [s], ops, depth + 1)
        return
    if depth < 5 and isinstance(x, list) and isinstance(y, list) and idk(x) and idk(x) == idk(y):
        ik = idk(x); xa = {e[ik]: e for e in x}; ya = {e[ik]: e for e in y}
        for s in list(xa) + [s for s in ya if s not in xa]:
            p = path + [{"@" + ik: s}]
            if s not in ya: ops.append(["set", p, h(xa[s]), DEL])
            elif s not in xa: ops.append(["set", p, None, ya[s]])
            else: diff(xa[s], ya[s], p, ops, depth + 1)
        if [e[ik] for e in x] != [e[ik] for e in y]:
            ops.append(["order", path, ik, [e[ik] for e in y]])
        return
    ops.append(["set", path, h(x), y])
def resolve(root, path, create=False):
    """returns (container, key) for the last path element; key is a dict key or ('@', ik, id)."""
    cur = root
    for p in path[:-1]:
        if isinstance(p, dict):
            (ik, s), = p.items(); ik = ik[1:]
            m = [e for e in cur if e.get(ik) == s]
            if not m: return None, None
            cur = m[0]
        else:
            if p not in cur:
                if not create: return None, None
                cur[p] = {}
            cur = cur[p]
    return cur, path[-1]
def get(c, k):
    if isinstance(k, dict):
        (ik, s), = k.items(); m = [e for e in c if e.get(ik[1:]) == s]; return (True, m[0]) if m else (False, None)
    return (k in c, c.get(k))
def put(c, k, v):
    if isinstance(k, dict):
        (ik, s), = k.items(); ik = ik[1:]; idx = [i for i, e in enumerate(c) if e.get(ik) == s]
        if v == DEL:
            for i in reversed(idx): c.pop(i)
        elif idx: c[idx[0]] = v
        else: c.append(v)
    else:
        if v == DEL: c.pop(k, None)
        else: c[k] = v
def apply(a, d):
    bad = []
    for op in d["ops"]:
        if op[0] != "set": continue
        _, path, hb, v = op
        c, k = resolve(a, path, create=True)
        if c is None: bad.append(["missing parent", path]); continue
        ok, cur = get(c, k)
        if (h(cur) if ok else None) != hb: bad.append(["base differs", path])
        put(c, k, v)
    for op in d["ops"]:
        if op[0] != "order": continue
        _, path, ik, order = op
        c = a
        for p in path:
            if isinstance(p, dict):
                (pk, s), = p.items(); c = [e for e in c if e.get(pk[1:]) == s][0]
            else: c = c[p]
        pos = {s: i for i, s in enumerate(order)}
        c.sort(key=lambda e: pos.get(e[ik], len(pos)))
    return a, bad
if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "make":
        a = json.load(open(sys.argv[2])); b = json.load(open(sys.argv[3])); ops = []
        diff(a, b, [], ops, 0); d = {"base_sha": h(a), "new_sha": h(b), "ops": ops}
        json.dump(d, gzip.open(sys.argv[4], "wt")); print("ops", len(ops), "base", d["base_sha"], "new", d["new_sha"])
        a2, bad = apply(json.load(open(sys.argv[2])), d); print("self-apply", h(a2) == d["new_sha"], "conflicts", len(bad))
    elif cmd == "apply":
        a = json.load(open(sys.argv[2])); d = json.load(gzip.open(sys.argv[3], "rt"))
        print("base sha", h(a), "delta base", d["base_sha"])
        a2, bad = apply(a, d)
        print("conflicts", len(bad))
        for b in bad: print("  CONFLICT", b[0], json.dumps(b[1]))
        json.dump(a2, open(sys.argv[4], "w"), indent=1); print("result sha", h(a2), "delta new", d["new_sha"])
