#!/usr/bin/env python3
"""compose_drop_guard.py PREV.json NEW.json [--history OLDER.json ...] [--row NAME=BASE.json:ROW.json ...]
                       [--drop-list FILE] [--max-list N] [--json OUT.json]

COMPOSE-GUARD-1124 (QC-COMPOSE-GUARD, COORD 11-24): refuse a composed die plan that silently loses what the previous
event's plan (or an adopted private row) carried.  QC C1k lost the QC-OPEN-STA r10 st_a row (3c17478ed804, built on C1g,
never composed into C1h..C1k) and landing_relay_start_copy on two st_a types; four route kits then failed SETUP_TRIAGE.

Findings (each is one plan path, dotted; list elements that are dicts with a unique name/conn/inst/id are keyed by it):
  DROP    PREV has the path and NEW lacks it (or NEW holds null there).  Reported at the highest missing level, so a lost
          partition type is one line, not thousands.
  REVERT  (needs --history) NEW's value equals the value an OLDER plan held, and PREV had changed it: a compose that
          started from a stale base undoes a later row.
  ROW-LOST / ROW-DROP  (needs --row NAME=BASE:ROW) a private row adopted for this event: every path where ROW differs
          from BASE must hold ROW's value in NEW, or some third value (a later row replaced it).  NEW == BASE value is
          ROW-LOST, a missing path ROW-DROP.
Drop list FILE: one fnmatch pattern per line over the dotted path, optional ' # reason'; a matching finding is reported
as INTENDED and does not fail.  '#' lines and blank lines are ignored.  A pattern may be prefixed with the finding kind
('REVERT partition_types.x.clock.*'); without a kind it matches every kind.
rc 0 = nothing silent; rc 1 = silent drops/reverts/row losses (listed); rc 2 = usage / unreadable input.
Compose scripts call it after writing NEW and before PRE/bind, for example:
  python3 -I tools/die_plan/compose_drop_guard.py C1j.json C1k.json --history C1g.json C1h.json C1i.json \
      --row r10=C1g.json:plan_c1g_sta10.json --drop-list rows/c1k_drops.txt
plan_gate_pre runs the DROP/REVERT part against --baseline-plan as the COMPOSEDROP class (WARN; OT_COMPOSE_DROP=fail
makes it a FAIL)."""
import argparse
import fnmatch
import hashlib
import json
import sys
from collections import Counter, OrderedDict

ID_KEYS = ("name", "conn", "inst", "id")


def _md5(x):
    return hashlib.md5(json.dumps(x, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]


def _list_key(v):
    """identity key for a list of dicts (every element has it, values unique hashable), else None"""
    if not v or not all(isinstance(e, dict) for e in v):
        return None
    for k in ID_KEYS:
        vals = [e.get(k) for e in v]
        if all(isinstance(x, (str, int)) for x in vals) and len(set(map(str, vals))) == len(vals):
            return k
    return None


def _children(v):
    """OrderedDict of child label -> value for a dict or an identity-keyed list, else None (a leaf)"""
    if isinstance(v, dict):
        return v
    if isinstance(v, list):
        k = _list_key(v)
        if k:
            return OrderedDict(("[%s=%s]" % (k, e[k]), e) for e in v)
    return None


def show(path):
    """dotted display form of a tuple path; identity-keyed list elements print as [key=value]"""
    out = ""
    for k in path:
        out = k if not out else (out + k if k.startswith("[") and k.endswith("]") and "=" in k else out + "." + k)
    return out


def flatten(v, path=(), out=None):
    """{tuple path: md5} of every leaf plus every container (so a container-level revert is visible too)"""
    if out is None:
        out = {}
    out[path] = _md5(v)
    ch = _children(v)
    if ch:
        for k, x in ch.items():
            flatten(x, path + (str(k),), out)
    return out


def drops(prev, new, path=(), out=None):
    """tuple paths PREV has and NEW lacks (or holds null), at the highest missing level"""
    if out is None:
        out = []
    cp, cn = _children(prev), _children(new)
    if cp is None or cn is None or type(prev) is not type(new):
        return out
    for k, x in cp.items():
        p = path + (str(k),)
        if k not in cn or (cn[k] is None and x is not None):
            out.append(p)
        else:
            drops(x, cn[k], p, out)
    return out


def _innermost(paths):
    """drop every path that is a proper prefix (container) of another path in the set"""
    anc = set()
    for p in paths:
        anc.update(p[:i] for i in range(len(p)))
    return [p for p in paths if p not in anc]


def reverts(prev_fl, new_fl, hist_fls):
    """paths where NEW == an older plan's value, != PREV's (PREV changed it, NEW undid it); innermost only"""
    hits = {}
    for p, nv in new_fl.items():
        pv = prev_fl.get(p)
        if not p or pv is None or pv == nv:
            continue
        for name, hf in hist_fls:
            if hf.get(p) == nv:
                hits[p] = name
                break
    return [(p, hits[p]) for p in _innermost(list(hits))]


def row_check(base, row, new):
    """[(kind, path)] for a private row: every path ROW set vs BASE must be carried (or replaced) in NEW"""
    bf, rf, nf = flatten(base), flatten(row), flatten(new)
    leaf = _innermost([p for p in rf if p and bf.get(p) != rf[p]])   # containers of changed leaves change too
    out = []
    for p in leaf:
        nv = nf.get(p)
        if nv == rf[p]:
            continue
        if nv is None:
            out.append(("ROW-DROP", p))
        elif nv == bf.get(p):
            out.append(("ROW-LOST", p))
    return out


def load_drop_list_lines(lines):
    """[(kind or None, fnmatch pattern)] from drop-list lines ('[KIND ]PATTERN [# reason]')"""
    pats = []
    for line in lines:
        s = line.split(" #", 1)[0].strip()
        if not s or s.startswith("#"):
            continue
        kind, _, pat = s.partition(" ")
        if kind in ("DROP", "REVERT", "ROW-LOST", "ROW-DROP") and pat.strip():
            pats.append((kind, pat.strip()))
        else:
            pats.append((None, s))
    return pats


def load_drop_list(fn):
    if not fn:
        return []
    with open(fn) as f:
        return load_drop_list_lines(f)


def intended(kind, path, pats):
    return any((k is None or k == kind or (k == "DROP" and kind == "ROW-DROP")) and fnmatch.fnmatchcase(path, p)
               for k, p in pats)


def group(path):
    parts = path.replace("[", ".[").split(".")
    return ".".join(parts[:3] if parts[0] == "partition_types" else parts[:2])


def guard(prev, new, history=(), rows=(), drop_pats=()):
    """[(kind, path, extra)] of every finding; history = [(name, plan)], rows = [(name, base, row)]"""
    found = [("DROP", show(p), "") for p in drops(prev, new)]
    if history:
        pf, nf = flatten(prev), flatten(new)
        found += [("REVERT", show(p), "to " + n) for p, n in reverts(pf, nf, [(n, flatten(h)) for n, h in history])]
    for name, base, row in rows:
        found += [(k, show(p), "row " + name) for k, p in row_check(base, row, new)]
    return [(k, p, x, intended(k, p, drop_pats)) for k, p, x in found]


def report(found, max_list=12):
    """(lines, silent findings): one line per (kind, plan path group, note) with a count and up to 3 example paths"""
    lines = []
    silent = [f for f in found if not f[3]]
    for label, sel in (("SILENT", silent), ("INTENDED", [f for f in found if f[3]])):
        c, ex = Counter(), {}
        for k, p, x, _ in sel:
            g = (k, group(p), x)
            c[g] += 1
            ex.setdefault(g, []).append(p) if len(ex.get(g, ())) < 3 else None
        for i, ((k, g, x), n) in enumerate(sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))):
            if i >= max_list:
                lines.append(f"{label} ... {len(c) - max_list} more groups (--max-list / --json)")
                break
            lines.append(f"{label} {k} {g} x{n}{(' (' + x + ')') if x else ''}: " + ", ".join(ex[(k, g, x)]))
    return lines, silent


def findings_for_pre(prev, new, drop_list=None, level="WARN", max_list=6):
    """plan_gate_pre COMPOSEDROP: DROP findings of NEW vs the baseline plan, one line per group"""
    found = guard(prev, new, drop_pats=load_drop_list(drop_list))
    lines, silent = report([f for f in found if not f[3]], max_list)
    if not silent:
        return []
    return [f"{level} COMPOSEDROP {len(silent)} plan paths the baseline carries are missing (compose_drop_guard.py; "
            f"--drop-list names intended drops)"] + [f"{level} COMPOSEDROP {ln[len('SILENT '):]}" for ln in lines[:max_list]]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prev")
    ap.add_argument("new")
    ap.add_argument("--history", nargs="*", default=[], help="older plans (oldest first) for REVERT detection")
    ap.add_argument("--row", action="append", default=[], help="NAME=BASE.json:ROW.json adopted private row")
    ap.add_argument("--drop-list", help="intended drops, fnmatch patterns over dotted paths")
    ap.add_argument("--max-list", type=int, default=12)
    ap.add_argument("--json", help="write every finding as JSON")
    a = ap.parse_args(argv)
    try:
        ld = lambda p: json.load(open(p))
        prev, new = ld(a.prev), ld(a.new)
        hist = [(p, ld(p)) for p in a.history]
        rows = []
        for r in a.row:
            name, _, br = r.partition("=")
            b, _, rw = br.partition(":")
            if not (name and b and rw):
                raise ValueError("--row wants NAME=BASE.json:ROW.json, got " + r)
            rows.append((name, ld(b), ld(rw)))
        pats = load_drop_list(a.drop_list)
    except (OSError, ValueError) as e:
        print(f"compose_drop_guard: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    found = guard(prev, new, hist, rows, pats)
    lines, silent = report(found, a.max_list)
    for ln in lines:
        print(ln)
    if a.json:
        json.dump([dict(kind=k, path=p, note=x, intended=i) for k, p, x, i in found], open(a.json, "w"), indent=0)
    n_int = len(found) - len(silent)
    if silent:
        print(f"REFUSED {len(silent)} silent losses ({n_int} intended): name them in --drop-list or restore them")
        return 1
    print(f"PASS 0 silent losses ({n_int} intended)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
