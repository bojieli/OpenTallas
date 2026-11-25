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
  SHARED    view declares nothing, but its closure reads a define that RTL outside its closure also reads (a wrapper on
            the other side of the black box, another core, the other die: FABLE-CLOSURE-STRATEGY 11-17 lever 5, 45 such
            pipeline-class defines on S81) or that a declared view tracks: ERROR (unknown build set: the S81 ba0/ba1 case)
  UNDECLARED view declares nothing and reads only defines no other RTL reads: advisory finding, never an error
SYNTHESIS, bench mutant (*MUTANT*, *_MUT*), *_CHECK and *_TRACE switches are never compared.

    python3 -I view_define_check.py PLAN.json --asbuilt ASBUILT_RUN.json [--base SRC] [--json OUT]   (exit 1 on ERROR)
bind.py bind --strict runs gate(): blocking when the asbuilt manifest sets view_define_gate, else reported (would_fail).
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
    import rtl_scan
    for f in sorted(list(root.rglob("*.sv")) + list(root.rglob("*.v"))):
        if f.name.endswith("_bb.v") or f.name.endswith("_bb.sv"):
            continue
        try:
            bodies = rtl_scan.scan("view_define_check.bodies", f, _file_bodies)   # BIND-SPEED-1124 #2: one scan per file
        except OSError:
            continue
        for m, conds, words in bodies:
            if m in mod:
                continue
            key = "%s::%s" % (f, m)
            mod[m] = key
            info[key] = (conds, words)
    return mod, info


def _file_bodies(text):
    """[(module, macros its body + the file-level guards test, instance-like words)] of one file, in text order (rtl_index)"""
    text = COMMENT.sub(" ", text)
    top = set(COND.findall(BODY.sub(" ", text)))
    return [(b.group(1), set(COND.findall(b.group(2))) | top, set(WORD.findall(b.group(2)))) for b in BODY.finditer(text)]


IGNORE = re.compile(r"^(SYNTHESIS|VERILATOR|NEGK)$|MUTANT|_MUT($|_|\d)|_CHECK$|_TRACE$")


def closure(module, mod, info):
    seen, todo = set(), [module]
    while todo:
        m = todo.pop()
        if m in seen or m not in mod:
            continue
        seen.add(m)
        todo.extend(w for w in info[mod[m]][1] if w in mod and w not in seen)
    return seen


def readers(mod, info):
    """macro -> set of modules whose body tests it"""
    out = {}
    for m, key in mod.items():
        for x in info[key][0]:
            out.setdefault(x, set()).add(m)
    return out


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
    who = readers(mod, info)
    rows = []
    for (m, lib), tns in sorted(views.items()):
        decl, vj = view_defines(base, lib)
        cl = closure(m, mod, info)
        rd = sorted(x for x in reads(m, mod, info) if not IGNORE.search(x))
        shared = {x: sorted(who.get(x, set()) - cl)[:4] for x in rd if who.get(x, set()) - cl}
        rows.append(dict(module=m, lib=lib, view_json=vj, declared=sorted(decl) if decl is not None else None,
                         reads=rd, shared=shared, types=sorted(tns)[:5], in_rtl=m in mod))
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
            hit = sorted((rd & tracked) | set(r["shared"]))
            if hit:
                errors.append("VIEW_DEFINES %s (%s): declares no bind_defines but reads shared define(s) %s (die has %s; also "
                              "read by %s): record the set it was built with in its view.json" % (
                                  r["module"], r["lib"], ",".join(hit), ",".join(x for x in hit if x in die) or "none",
                                  "; ".join("%s: %s" % (x, ",".join(r["shared"][x])) for x in hit if x in r["shared"])[:300]))
                r["verdict"] = "UNDECLARED_SHARED"
            else:
                r["verdict"] = "UNDECLARED"
                if rd & die:
                    advisory.append("%s reads die define(s) %s, view declares none" % (r["module"], ",".join(sorted(rd & die))))
    return errors, advisory, rows


def gate(plan, ab, base):
    """bind --strict hook -> (errors, summary).  Blocking once the asbuilt manifest sets "view_define_gate": true (a die turns
    it on when its views record their sets: S81 D5c had 1 of 66 views declared); until then the bind report carries the
    full finding list as would_fail and the bind does not stop on it."""
    errors, advisory, rows = check(plan, ab.get("defines") or [], base)
    from collections import Counter
    on = bool(ab.get("view_define_gate"))
    summ = dict(gate="BLOCKING" if on else "REPORT", views=len(rows), verdicts=dict(Counter(r["verdict"] for r in rows)),
                errors=len(errors), would_fail=[] if on else errors[:200], advisory=len(advisory), advisory_sample=advisory[:10])
    return (errors if on else []), summ


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
