#!/usr/bin/env python3
"""Prefix every module DEFINED in one preprocessed source tree (definitions + all word-boundary uses).

usage: rename.py IN.sv OUT.sv PREFIX [--keep NAME ...]
IN.sv is the `verilator -E -P` output of one closure (macros resolved), so the rename only has to handle identifiers.
Only names defined by `module NAME` in IN.sv are renamed; everything else (signals, ports, strings that are not
identical to a module name) is untouched.  Prints the renamed module list to stderr.
"""
import re
import sys


def main():
    a = sys.argv[1:]
    if len(a) < 3:
        sys.exit(__doc__)
    src, dst, pre = a[:3]
    keep = set(a[a.index("--keep") + 1:]) if "--keep" in a else set()
    txt = open(src).read()
    mods = sorted(set(re.findall(r"^\s*module\s+(?:automatic\s+|static\s+)?([A-Za-z_]\w*)", txt, re.M)) - keep)
    if not mods:
        sys.exit("rename.py: no module definitions in " + src)
    rx = re.compile(r"(?<![\w$`.])(" + "|".join(map(re.escape, sorted(mods, key=len, reverse=True))) + r")(?![\w$])")
    out = rx.sub(lambda m: pre + m.group(1), txt)
    open(dst, "w").write(out)
    sys.stderr.write(f"rename.py: {len(mods)} modules prefixed {pre}: {' '.join(mods)}\n")


if __name__ == "__main__":
    main()
