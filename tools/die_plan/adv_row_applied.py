"""adv_row_applied.py -- PRECHECK ADV-ROW-APPLIED (COORD 11-24, FABLE-RC-ALL f77e2c6f; report only).

A row accepted 'by reference' (IN-BASE / ROW-REBASED / REASONED) whose ops were never applied to any plan (S81 KVLEAF-T2-HARD-1: 0 of 5 ops in c8).
Checks BY OP CONTENT, never by label: for each ops file given (kw rows=[paths] / env OT_ADV_ROWS=colon-separated), every op {op: replace|add|add_or_replace|remove,
path (JSON pointer or dotted), value, old} must have its value at its path in THIS plan.  FULL / PARTIAL / NONE per row; ops still at their old value are counted.
Ops file format: {"ops": [...]} or a bare op list; {"derived": true} without "base" = diffed against an inferred base -> INFERRED-BASE, never NONE; rows with no ops file: kw noops=[names] -> NOOPS.  Without rows= it prints NOT-RUN with how to give them (the composing lane lists its rows' ops files).
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import os
import sys
from pathlib import Path

CHECK = "ADV-ROW-APPLIED"


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def canon(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"))


def get(doc, path):
    cur = doc
    for tok in [t for t in path.strip("/").split("/") if t != ""]:
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            try:
                cur = cur[int(tok)]
            except (ValueError, IndexError):
                return KeyError
        elif isinstance(cur, dict) and tok in cur:
            cur = cur[tok]
        else:
            return KeyError
    return cur


def ops_of(d):
    if isinstance(d, dict) and isinstance(d.get("ops"), list):
        return d["ops"]
    if isinstance(d, list) and d and isinstance(d[0], dict) and "path" in d[0]:
        return d
    return None


def applied(ops, plan):
    """-> (n judged, applied, still at old value, path missing)"""
    n = a = old = miss = 0
    for o in ops:
        if not isinstance(o, dict) or o.get("path") is None:
            continue
        op = o.get("op") or "replace"
        op = "replace" if op == "add_or_replace" else op
        p = o["path"]
        if "/" not in p:
            p = "/" + p.replace(".", "/")
        if op == "remove":
            n += 1
            a += get(plan, p) is KeyError
            continue
        if op not in ("replace", "add", "set") or "value" not in o:
            continue
        n += 1
        cur = get(plan, p)
        if cur is KeyError:
            miss += 1
        elif canon(cur) == canon(o["value"]):
            a += 1
        elif "old" in o and canon(cur) == canon(o["old"]):
            old += 1
    return n, a, old, miss


def status(n, a, inferred=False):
    """FULL / PARTIAL / NONE; NOOPS = nothing checkable.  Ops derived by diffing against a guessed base (file key derived/base_inferred true, or no 'base'
    label on a derived file) can only prove presence: a non-FULL result is INFERRED-BASE, never NONE or PARTIAL (ask the owner for the stated base)."""
    if n == 0:
        return "NOOPS"
    if a == n:
        return "FULL"
    if inferred:
        return "INFERRED-BASE"
    return "NONE" if a == 0 else "PARTIAL"


def is_inferred(d):
    """ops file dict from a whole-plan diff without the row's stated base"""
    return isinstance(d, dict) and bool(d.get("derived") or d.get("base_inferred")) and not d.get("base")


def _findings(raw, plan_path, tree=None, **kw):
    rows = kw.get("rows") or [x for x in os.environ.get("OT_ADV_ROWS", "").split(":") if x]
    noops = list(kw.get("noops") or [x for x in os.environ.get("OT_ADV_NOOPS", "").split(":") if x])
    if not rows and not noops:
        return [_w("NOT-RUN: no rows given (kw rows=[ops files] / OT_ADV_ROWS=a.json:b.json; rows accepted without an ops file: kw noops=[names] / OT_ADV_NOOPS): "
                   "list the ops file of every row this compose claims")]
    out, cnt = [], {"FULL": 0, "PARTIAL": 0, "NONE": 0, "INFERRED-BASE": 0, "NOOPS": 0}
    for nm in noops:
        cnt["NOOPS"] += 1
        out.append(_w(f"{nm}: NOOPS row accepted with no ops file: nothing to check, the owner must supply its ops"))
    for p in rows:
        d = json.loads(Path(p).read_text())
        ops = ops_of(d)
        if ops is None:
            out.append(_w(f"{Path(p).name}: not an ops file (no ops list)"))
            continue
        n, a, old, miss = applied(ops, raw)
        inf = is_inferred(d)
        s = status(n, a, inf)
        cnt[s] += 1
        if s != "FULL":
            tail = {"NONE": "; the row is NOT applied: compose it or drop it with a reason",
                    "INFERRED-BASE": "; ops derived against an inferred base: not a NONE, ask the row owner for the stated base"}.get(s, "")
            out.append(_w(f"{Path(p).name}: {s} {a}/{n} ops present in this plan ({old} still at the old value, {miss} path(s) missing){tail}"))
    out.append(_w("summary", f"{len(rows) + len(noops)} row(s): {cnt['FULL']} FULL, {cnt['PARTIAL']} PARTIAL, {cnt['NONE']} NONE, "
                  f"{cnt['INFERRED-BASE']} INFERRED-BASE, {cnt['NOOPS']} NOOPS"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], None, rows=sys.argv[2:]):
        print(ln)
