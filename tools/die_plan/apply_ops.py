#!/usr/bin/env python3
"""apply_ops.py PLAN_IN OPS.json PLAN_OUT [TYPE_RE_SKIP]

Apply plan_ops (JSON-pointer) ops to a plan.
  replace : {"op":"replace","path":P,"old":V0,"value":V}  applied when the current value == V0 (old check); already == V counts applied;
            otherwise stale.  An op without "op" is a replace (the original behaviour).
  add     : {"op":"add","path":P,"value":V}  RFC 6902 add: into a list at index (or "-" = append), into a dict as key.
            A missing container on the path is created (list when the next token is an integer or "-", else dict), so
            /partition_types/T/internal_stations/0 works on a type that has no internal_stations key (STN-ROWS 11-25: the
            old script raised KeyError there).  Re-applying an add whose value already sits at that index counts applied.
  remove  : {"op":"remove","path":P}  absent key / index is a no-op (counted applied).
Exit 0; prints one OPS line.  Pointer tokens unescape ~1 -> / and ~0 -> ~.
"""
import json
import re
import sys


def tok(p):
    return [t.replace("~1", "/").replace("~0", "~") for t in p.strip("/").split("/")]


def is_idx(t):
    return t == "-" or t.isdigit()


def walk(cur, parts, create):
    """container of the last token; missing containers are created when create"""
    for i, p in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        if isinstance(cur, list):
            j = int(p)
            if j >= len(cur):
                if not create:
                    return None
                raise IndexError(f"list index {j} beyond {len(cur)} at {p}")
            cur = cur[j]
        else:
            if p not in cur or cur[p] is None:
                if not create:
                    return None
                cur[p] = [] if is_idx(nxt) else {}
            cur = cur[p]
    return cur


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def apply(P, ops, skip=None):
    ap = sk = st = 0
    stale = []
    for o in ops:
        parts = tok(o["path"])
        if skip and len(parts) > 1 and re.search(skip, parts[1]):
            sk += 1
            continue
        kind = o.get("op", "replace")
        if kind == "add":
            cur = walk(P, parts, True)
            k = parts[-1]
            if isinstance(cur, list):
                j = len(cur) if k == "-" else int(k)
                if j < len(cur) and same(cur[j], o["value"]):
                    ap += 1
                elif j > len(cur):
                    st += 1
                    stale.append(o["path"])
                else:
                    cur.insert(j, o["value"])
                    ap += 1
            else:
                cur[k] = o["value"]
                ap += 1
        elif kind == "remove":
            cur = walk(P, parts, False)
            k = parts[-1]
            if cur is not None:
                if isinstance(cur, list) and k.isdigit() and int(k) < len(cur):
                    del cur[int(k)]
                elif isinstance(cur, dict):
                    cur.pop(k, None)
            ap += 1
        else:
            cur = walk(P, parts, False)
            k = parts[-1]
            if cur is None:
                st += 1
                stale.append(o["path"])
                continue
            k = int(k) if isinstance(cur, list) else k
            have = cur[k] if (isinstance(cur, list) and k < len(cur)) or (isinstance(cur, dict) and k in cur) else None
            if same(have, o.get("old")):
                cur[k] = o["value"]
                ap += 1
            elif same(have, o["value"]):
                ap += 1
            else:
                st += 1
                stale.append(o["path"])
    return ap, sk, st, stale


def main(argv):
    P = json.load(open(argv[1]))
    R = json.load(open(argv[2]))
    skip = argv[4] if len(argv) > 4 else None
    ap, sk, st, stale = apply(P, R["ops"], skip)
    json.dump(P, open(argv[3], "w"), indent=1)
    open(argv[3], "a").write("\n")
    print(f"OPS {argv[2]}: applied {ap}, skipped(type) {sk}, stale(old!=cur) {st} {stale[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
