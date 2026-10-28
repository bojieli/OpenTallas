"""roll up a flat yosys `stat` (per-module local cells + submodule instance counts) into total std cells per
module class under TOP.  usage: hier_sum.py STAT_FLAT.txt TOP"""
import re
import sys
from collections import defaultdict
from functools import lru_cache

txt = open(sys.argv[1]).read()
top = sys.argv[2]
mods = {}
for blk in re.split(r"(?m)^=== ", txt)[1:]:
    name, body = blk.split(" ===", 1)
    local, subs, mode = 0, {}, None
    for ln in body.splitlines():
        m = re.match(r"^\s+(\d+)\s+cells$", ln)
        if m:
            mode = "cells"
            continue
        m = re.match(r"^\s+(\d+)\s+submodules$", ln)
        if m:
            mode = "subs"
            continue
        m = re.match(r"^\s+(\d+)\s{3}(\S+)$", ln)
        if m and mode == "cells":
            if not m.group(2).endswith("_R"):
                continue        # instance of a module: counted under submodules / blackbox
            local += int(m.group(1))
        elif m and mode == "subs":
            subs[m.group(2)] = int(m.group(1))
        elif re.match(r"^\s+\d+\s+\S", ln) and not re.match(r"^\s+\d+\s{3}", ln):
            mode = None
    mods[name] = (local, subs)


def cls(n):
    return n.split("\\")[-1] if n.startswith("$paramod$") else (n.split("\\")[1] if n.startswith("$paramod\\") else n)


@lru_cache(None)
def total(n):
    if n not in mods:
        return 0
    loc, subs = mods[n]
    return loc + sum(c * total(s) for s, c in subs.items())


by = defaultdict(int)


def walk(n, mult, owner):
    loc, subs = mods.get(n, (0, {}))
    by[owner] += mult * loc
    for s, c in subs.items():
        walk(s, mult * c, owner if owner != "<glue>" or s.endswith("_bound") else cls(s))


walk(top, 1, "<glue>")
for t, (loc, subs) in mods.items():
    pass
T = total(top)
print(f"{top}: total std cells {T}")
for k, v in sorted(by.items(), key=lambda kv: -kv[1])[:12]:
    print(f"  {k:32s} {v:8d} ({100 * v / T:.1f}%)")
