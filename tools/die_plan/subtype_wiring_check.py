#!/usr/bin/env python3
"""Wiring proof of a one-to-one sub-type rebind (BIND-SUBTYPE 11-11), independent of bind_subtype.py.

    subtype_wiring_check.py OLD_TYPE.sv NEW_TYPE.sv RULE.json [--out RECEIPT.json]   exit 0 PASS, 1 FAIL

OLD = a bound partition type from the bind without subtype_bind, NEW = the same type from the bind with it (same plan,
same base manifest).  The check reads both files as text: every line outside instance statements must be identical,
every instance must exist in both with the same module and the same port expressions, except instances of the rule's
native module, which must become instances of the rule's top with port expression new[top port] == old[native port]
under the rule's rename / share maps (every top port connected, no other port).  With the sub-cores blackboxed this is
the structural equivalence of the two partitions: the only change is the declared leaf -> composition substitution.
"""
import argparse
import json
import re
import sys
from pathlib import Path

_INST = re.compile(r"(?ms)^([ \t]*)(\w+)([ \t]*#\(.*?\))?[ \t]+(\\\S+|\w+)[ \t]*\((.*?)\);[ \t]*$")
_KW = {"module", "input", "output", "inout", "wire", "reg", "logic", "assign", "parameter", "localparam", "always",
       "initial", "genvar", "function", "task", "if", "else", "for", "case", "begin", "end"}


def conns(body):
    out, pos = {}, 0
    while True:
        m = re.compile(r"\.(\w+)\s*\(").search(body, pos)
        if not m:
            return out
        d, j = 1, m.end()
        while j < len(body) and d:
            d += {"(": 1, ")": -1}.get(body[j], 0)
            j += 1
        out[m.group(1)] = re.sub(r"\s+", "", body[m.end():j - 1])
        pos = j


def split(text):
    """(non-instance text with instances replaced by a marker, {inst: (module, params, conns)})."""
    insts, rest, pos = {}, [], 0
    for m in _INST.finditer(text):
        if m.group(2) in _KW:
            continue
        rest.append(text[pos:m.start()])
        rest.append(f"<INST {m.group(4)}>")
        pos = m.end()
        if m.group(4) in insts:
            raise ValueError(f"duplicate instance {m.group(4)}")
        insts[m.group(4)] = (m.group(2), re.sub(r"\s+", "", m.group(3) or ""), conns(m.group(5)))
    rest.append(text[pos:])
    return "".join(rest), insts


_ID = re.compile(r"^(\\\S+|\w+)(\[[^\]]*\])?$")


def net_renames(o, n, rule):
    """{NEW net: OLD net} read off the substituted instances only: a renamed port whose NEW and OLD expressions are the
    same bit range of two differently named nets (the binder names a leaf output net after the leaf port, e.g.
    w_<inst>_sfu_coll vs w_<inst>_lane_coll).  ({}, errors) on a conflicting pair."""
    rename, share, nmap, errs = rule.get("rename", {}), rule.get("share", {}), {}, []
    for name in sorted(set(o) & set(n)):
        (om, _op, oc), (nm, _np, nc) = o[name], n[name]
        if om != rule["native"] or nm != rule["top"]:
            continue
        for tp, e in nc.items():
            src = share.get(tp) or rename.get(tp, tp)
            a, b = _ID.match(e), _ID.match(oc.get(src, ""))
            if a and b and a.group(2) == b.group(2) and a.group(1) != b.group(1):
                if nmap.setdefault(a.group(1), b.group(1)) != b.group(1):
                    errs.append(f"net {a.group(1)} maps to {nmap[a.group(1)]} and {b.group(1)}")
    return nmap, errs


def apply_renames(text, nmap):
    """NEW text with whole identifiers renamed; errors when an OLD name is already a different NEW identifier."""
    idents = set(re.findall(r"\b\w+\b", text))
    errs = [f"rename collision: {k} -> {v} but {v} is already a NEW identifier" for k, v in nmap.items() if v in idents]
    if nmap and not errs:
        rx = re.compile(r"\b(" + "|".join(sorted(map(re.escape, nmap), key=len, reverse=True)) + r")\b")
        text = rx.sub(lambda m: nmap[m.group(1)], text)
    return text, errs


def check(old_text, new_text, rule):
    """Comments are dropped on both sides (the binder annotates lanes with sink port names); every NEW net that a
    renamed port names differently is renamed back (net_renames, bijective, collision-checked); then exact."""
    errs, n_sub = [], 0
    old_text = re.sub(r"//[^\n]*", "", old_text)
    new_text = re.sub(r"//[^\n]*", "", new_text)
    nmap, e1 = net_renames(split(old_text)[1], split(new_text)[1], rule)
    new_text, e2 = apply_renames(new_text, nmap)
    errs += e1 + e2
    check.renamed_nets = len(nmap)
    o_rest, o = split(old_text)
    n_rest, n = split(new_text)
    if o_rest != n_rest:
        a, b = o_rest.splitlines(), n_rest.splitlines()
        k = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        errs.append(f"non-instance text differs at line {k + 1}")
    if set(o) != set(n):
        errs.append(f"instance sets differ: only old {sorted(set(o) - set(n))[:5]}, only new {sorted(set(n) - set(o))[:5]}")
    rename, share = rule.get("rename", {}), rule.get("share", {})
    for name in sorted(set(o) & set(n)):
        (om, op, oc), (nm, np_, nc) = o[name], n[name]
        if om == rule["native"]:
            n_sub += 1
            if nm != rule["top"] or np_:
                errs.append(f"{name}: {om} -> {nm}{np_}, expected {rule['top']} without parameters")
                continue
            want = {}
            for tp in nc:
                src = share.get(tp) or rename.get(tp, tp)
                if src not in oc:
                    errs.append(f"{name}.{tp}: native port {src} not connected in OLD")
                    continue
                want[tp] = oc[src]
            covered = {share.get(tp) or rename.get(tp, tp) for tp in nc}
            if covered != set(oc):
                errs.append(f"{name}: native ports not carried {sorted(set(oc) - covered)[:5]}")
            for tp, e in want.items():
                if nc[tp] != e:
                    errs.append(f"{name}.{tp}: NEW {nc[tp][:60]} != OLD {e[:60]}")
        elif (om, op, oc) != (nm, np_, nc):
            errs.append(f"{name}: instance changed ({om} -> {nm})")
    return errs, n_sub


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("rule")
    ap.add_argument("--out")
    a = ap.parse_args()
    rule = json.loads(Path(a.rule).read_text())
    errs, n_sub = check(Path(a.old).read_text(), Path(a.new).read_text(), rule)
    ok = not errs and n_sub > 0
    rec = dict(schema="opentallas.die_plan.subtype_wiring.v1", old=a.old, new=a.new, native=rule["native"],
               top=rule["top"], substituted=n_sub, renamed_nets=getattr(check, "renamed_nets", 0),
               verdict="PASS" if ok else "FAIL", errors=errs[:50])
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print(rec["verdict"], n_sub, "renamed_nets", rec["renamed_nets"], errs[:5])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
