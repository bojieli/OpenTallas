"""3-way rebase of a plan event: apply (new - base) onto other. Report conflicts."""
import json, sys

KEYS = ("name", "inst", "instance", "id", "type")


def keyof(lst):
    if not lst or not all(isinstance(x, dict) for x in lst):
        return None
    for k in KEYS:
        vals = [x.get(k) for x in lst]
        if all(v is not None for v in vals) and len(set(map(str, vals))) == len(vals):
            return k
    return None


def diff(b, n, path, out):
    if isinstance(b, dict) and isinstance(n, dict):
        for k in set(b) | set(n):
            if k not in n:
                out.append((path + [("d", k)], "DEL", None))
            elif k not in b:
                out.append((path + [("d", k)], "SET", n[k]))
            elif b[k] != n[k]:
                diff(b[k], n[k], path + [("d", k)], out)
        return
    if isinstance(b, list) and isinstance(n, list):
        kb, kn = keyof(b), keyof(n)
        if kb and kb == kn:
            bm = {str(x[kb]): x for x in b}
            nm = {str(x[kb]): x for x in n}
            for k in set(bm) | set(nm):
                if k not in nm:
                    out.append((path + [("l", kb, k)], "DEL", None))
                elif k not in bm:
                    out.append((path + [("l", kb, k)], "SET", nm[k]))
                elif bm[k] != nm[k]:
                    diff(bm[k], nm[k], path + [("l", kb, k)], out)
            return
    out.append((path, "SET", n))


def get(o, path):
    for p in path:
        if p[0] == "d":
            if not isinstance(o, dict) or p[1] not in o:
                return KeyError
            o = o[p[1]]
        else:
            if not isinstance(o, list):
                return KeyError
            m = [x for x in o if isinstance(x, dict) and str(x.get(p[1])) == p[2]]
            if len(m) != 1:
                return KeyError
            o = m[0]
    return o


def put(o, path, op, val):
    for p in path[:-1]:
        o = o[p[1]] if p[0] == "d" else [x for x in o if str(x.get(p[1])) == p[2]][0]
    p = path[-1]
    if p[0] == "d":
        if op == "DEL":
            o.pop(p[1], None)
        else:
            o[p[1]] = val
    else:
        idx = [i for i, x in enumerate(o) if str(x.get(p[1])) == p[2]]
        if op == "DEL":
            for i in reversed(idx):
                o.pop(i)
        elif idx:
            o[idx[0]] = val
        else:
            o.append(val)


def fmt(path):
    return "/".join(str(p[1]) if p[0] == "d" else f"[{p[1]}={p[2]}]" for p in path)


base, new, other, outp = sys.argv[1:5]
B, N, O = (json.load(open(f)) for f in (base, new, other))
ch = []
diff(B, N, [], ch)
conf = 0
for path, op, val in ch:
    ov, bv = get(O, path), get(B, path)
    if ov is not KeyError and bv is not KeyError and ov != bv and ov != val:
        conf += 1
        print("CONFLICT", fmt(path))
    elif ov is KeyError and bv is not KeyError:
        conf += 1
        print("CONFLICT-MISSING", fmt(path))
    else:
        put(O, path, op, val)
        print(op, fmt(path))
print("changes", len(ch), "conflicts", conf)
json.dump(O, open(outp, "w"), indent=1)
