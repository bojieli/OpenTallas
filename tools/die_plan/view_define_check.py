#!/usr/bin/env python3
"""VIEW-DEFINES (COORD r535, S81 D5c 11-17): every hard-core view must be bound under the define set it was built with.

The die bind elaborates one die-wide preprocessor define set (asbuilt manifest `defines`) but blackboxes the hard cores, so a
core whose RTL reads a die define it was NOT synthesised with (or misses one it was) is never seen by the bind: S81 D5c bound
the signed dsdv_gunit_l1f_bf (M1REG C1REG SVREG FWPIPE) under a die set with FWPIPE only, and the signed ba0/ba1 views
(built without FWPIPE) under FWPIPE, so their bias lagged bf by one cycle; only the kit gen_lint found the first half.

A view declares its synthesis defines in `<view dir>/*.view.json` "bind_defines" (the dir of the plan hard_cores[].lib).
For each distinct hard-core module of the plan:
  reads(module)  = every macro tested by `ifdef / `ifndef / `elsif inside the module's body (plus file-level guards) and the
                   bodies of every module it instantiates, transitively (index of <base>/rtl; *_bb stubs never define)
  DECLARED  view lists bind_defines V: ERROR for each m in reads with (m in V) != (m in die defines)
  TRACKED   view declares nothing, but it reads a macro that some declared view of the plan also reads and lists, or that
            a declared view lists and the die defines: ERROR (same define family, unknown build set: the S81 ba0/ba1 case)
  UNDECLARED view declares nothing and reads only untracked macros: advisory finding (count + sample), never an error

    python3 -I view_define_check.py PLAN.json --asbuilt ASBUILT_RUN.json [--base SRC] [--json OUT]   (exit 1 on ERROR)
bind.py bind --strict runs gate() and adds its errors to the bind errors.
"""
import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

MODULE = re.compile(r"^\s*module\s+(\w+)", re.M)
COND = re.compile(r"`(?:ifdef|ifndef|elsif)\s+(\w+)")
WORD = re.compile(r"\b([A-Za-z_]\w*)\s*(?:#\s*\(|\w+\s*\()")
COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


BODY = re.compile(r"^\s*module\s+(\w+)(.*?)^\s*endmodule\b", re.M | re.S)


def rtl_index(base):
    """-> (module -> key, key -> (macros, words)) over <base>/rtl (*.sv, *.v; *_bb stubs skipped).  One key per module
    body (file + module): a module reads the conditions inside its own body plus the file-level ones outside every body
    (a guard around whole module definitions)."""
    mod, info = {}, {}
    root = Path(base) / "rtl"
    for f in sorted(list(root.rglob("*.sv")) + list(root.rglob("*.v"))):
        if f.name.endswith("_bb.v") or f.name.endswith("_bb.sv"):
            continue
        try:
            text = COMMENT.sub(" ", f.read_text(errors="replace"))
        except OSError:
            continue
        outside = BODY.sub(" ", text)
        top = set(COND.findall(outside))
        for b in BODY.finditer(text):
            m = b.group(1)
            if m in mod:
                continue
            key = "%s::%s" % (f, m)
            mod[m] = key
            info[key] = (set(COND.findall(b.group(2))) | top, set(WORD.findall(b.group(2))))
    return mod, info


def reads(module, mod, info):
    """macros the module's RTL tests, transitively over the modules it instantiates"""
    seen, todo, out = set(), [module], set()
    while todo:
        m = todo.pop()
        if m in seen or m not in mod:
            continue
        seen.add(m)
        macros, words = info[mod[m]]
        out |= macros
        todo.extend(w for w in words if w in mod and w not in seen)
    return out


def view_defines(base, lib):
    """the view's declared synthesis defines (list) or None when no *.view.json beside the lib declares bind_defines"""
    if not lib:
        return None, None
    d = Path(lib) if os.path.isabs(lib) else Path(base) / lib
    for vj in sorted(glob.glob(str(d.parent / "*.view.json"))):
        try:
            v = json.loads(Path(vj).read_text())
        except (OSError, ValueError):
            continue
        if isinstance(v.get("bind_defines"), list):
            return set(v["bind_defines"]), vj
    return None, None


def check(plan, die_defines, base, index=None):
    """-> (errors, advisory, rows)"""
    die = {(d[2:] if d.startswith("-D") else d).split("=", 1)[0] for d in die_defines}
    views = {}
    for tn, t in sorted((plan.get("partition_types") or {}).items()):
        for hc in t.get("hard_cores") or []:
            m = hc.get("module") or hc.get("physical_master")
            if not m:
                continue
            key = (m, hc.get("lib") or "")
            views.setdefault(key, set()).add(tn)
    mod, info = index or rtl_index(base)
    rows = []
    for (m, lib), tns in sorted(views.items()):
        decl, vj = view_defines(base, lib)
        rows.append(dict(module=m, lib=lib, view_json=vj, declared=sorted(decl) if decl is not None else None,
                         reads=sorted(reads(m, mod, info)), types=sorted(tns)[:5], in_rtl=m in mod))
    tracked = set()
    for r in rows:
        if r["declared"] is not None:
            tracked |= set(r["reads"]) & (set(r["declared"]) | die)
    errors, advisory = [], []
    for r in rows:
        rd = set(r["reads"])
        if r["declared"] is not None:
            v = set(r["declared"])
            bad = sorted(x for x in rd & (v | die) if (x in v) != (x in die))
            for x in bad:
                side = "built WITH %s, die set lacks it" % x if x in v else "built WITHOUT %s, die set has it" % x
                errors.append("VIEW_DEFINES %s (%s): %s (%s reads it)" % (r["module"], r["lib"], side, r["module"]))
            r["verdict"] = "MISMATCH" if bad else "MATCH"
        else:
            hit = sorted(rd & tracked)
            if hit:
                errors.append("VIEW_DEFINES %s (%s): declares no bind_defines but reads tracked define(s) %s (die has %s): "
                              "record the set it was built with in its view.json" % (
                                  r["module"], r["lib"], ",".join(hit), ",".join(x for x in hit if x in die) or "none"))
                r["verdict"] = "UNDECLARED_TRACKED"
            else:
                r["verdict"] = "UNDECLARED"
                if rd & die:
                    advisory.append("%s reads die define(s) %s, view declares none" % (r["module"], ",".join(sorted(rd & die))))
    return errors, advisory, rows


def gate(plan, ab, base):
    """bind --strict hook -> (errors, summary)"""
    errors, advisory, rows = check(plan, ab.get("defines") or [], base)
    from collections import Counter
    summ = dict(views=len(rows), verdicts=dict(Counter(r["verdict"] for r in rows)), errors=len(errors),
                advisory=len(advisory), advisory_sample=advisory[:10])
    return errors, summ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--asbuilt", required=True)
    ap.add_argument("--base", default=".")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    ab = json.loads(Path(a.asbuilt).read_text())
    errors, advisory, rows = check(plan, ab.get("defines") or [], a.base)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(schema="opentallas.view_define_check.v1", errors=errors,
                                                advisory=advisory, views=rows), indent=1) + "\n")
    for e in errors:
        print(e)
    print("VIEW_DEFINES %s views %d errors %d advisory %d" % ("FAIL" if errors else "PASS", len(rows), len(errors), len(advisory)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
