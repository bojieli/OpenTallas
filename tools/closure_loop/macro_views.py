#!/usr/bin/env python3
"""Resolve verdict.macros entries to src-relative macro view directories (DIR/NAME.lef, DIR/NAME_<corner>.lib).

MACRO-VIEW (el1011-ds-misc 2026-10-11): every consumer of verdict.macros (hold_eco.sh / vtswap_eco.sh -> OT_MACROS
"/src/<m>", path_summary.py --macro, corner_sta --macro, the post-ECO abstract re-export --macro-view) reads
<m>/<basename m>.lef relative to the job's source snapshot.  A spec that named the SRAM by its bare master
("ot_sram_1r1w_128x256_m1_r2c2") made every hold ECO die at once with ORD-0001 ".../ot_sram_.../...lef does not
exist" (el1011-pqc-aq12t-*, el1011-engc-pb*-*, qkd_ectl_f): hold fixing silently never ran.  An entry is accepted as
  physical/.../NAME            (canonical; kept as is, also when the tree does not hold it: installed views)
  /src/..., {SRC}/..., trailing '/', or a path to NAME.lef   (normalised)
  NAME (bare master)           -> the unique DIR/NAME/NAME.lef in the tree (physical/asap7_memory_macros preferred)
A bare name that cannot be resolved, or is ambiguous, raises MacroViewError: the caller fails loudly instead of running a
hold ECO without the macro's LEF/lib.

CLI (remote side, cwd-independent):  macro_views.py --root SRC m1 m2 ...  -> resolved dirs on stdout (space separated),
one 'MACRO-VIEW: a -> b' line per rewrite on stderr; exit 2 (message on stderr) when an entry cannot be resolved.
"""
import argparse
import os
import re
import sys
from pathlib import PurePosixPath

PREFERRED = ("physical/asap7_memory_macros/",)


class MacroViewError(ValueError):
    pass


def normalise(entry):
    m = re.sub(r"^(/src/|\{SRC\}/|\{SRCDIR\}/|\./)", "", str(entry).strip()).rstrip("/")
    if m.endswith(".lef"):
        m = str(PurePosixPath(m).parent)
    return m


def resolve(entries, lef_paths):
    """entries: verdict.macros; lef_paths: iterable of src-relative paths of the tree's *.lef files.
    -> (resolved list, [(entry, resolved), ...] rewrites).  Raises MacroViewError."""
    lefs = set(p for p in lef_paths if p.endswith(".lef"))
    by_name = {}
    for p in lefs:
        pp = PurePosixPath(p)
        if pp.parent.name == pp.stem:                       # DIR/NAME/NAME.lef: a macro view directory
            by_name.setdefault(pp.stem, []).append(str(pp.parent))
    out, rewrites = [], []
    for e in entries or []:
        m = normalise(e)
        name = PurePosixPath(m).name
        if not name:
            raise MacroViewError(f"verdict.macros entry {e!r} is empty")
        if "/" in m or f"{m}/{name}.lef" in lefs:
            r = m     # a path is the author's choice (views may be installed after the archive): normalised, kept
        else:
            cands = sorted(set(by_name.get(name, [])))
            pref = [c for c in cands if c.startswith(PREFERRED)]
            if len(cands) == 1 or len(pref) == 1:
                r = (pref or cands)[0]
            elif not cands:
                raise MacroViewError(f"verdict.macros entry {e!r}: no {name}/{name}.lef in the source tree "
                                     f"(give the src-relative view dir, e.g. physical/asap7_memory_macros/{name})")
            else:
                raise MacroViewError(f"verdict.macros entry {e!r} is ambiguous: {', '.join(cands)}")
        if r != e:
            rewrites.append((e, r))
        out.append(r)
    return out, rewrites


def tree_lefs(root):
    root = os.path.abspath(root)
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if not x.startswith(".") and x not in ("node_modules", "__pycache__")]
        for f in files:
            if f.endswith(".lef"):
                yield os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="source snapshot root (the ECO's /src)")
    ap.add_argument("macros", nargs="*")
    a = ap.parse_args(argv)
    if not a.macros:
        return 0
    direct = [f"{normalise(m)}/{os.path.basename(normalise(m))}.lef" for m in a.macros]
    need_walk = any("/" not in normalise(m) and not os.path.isfile(os.path.join(a.root, f)) for m, f in zip(a.macros, direct))
    lefs = list(tree_lefs(a.root)) if need_walk else direct
    try:
        out, rw = resolve(a.macros, lefs)
    except MacroViewError as ex:
        print(f"MACRO-VIEW ERROR: {ex}", file=sys.stderr)
        return 2
    for e, r in rw:
        print(f"MACRO-VIEW: {e} -> {r}", file=sys.stderr)
    print(" ".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
