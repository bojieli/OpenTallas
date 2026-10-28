"""Name-based structural equivalence: original vs partitioned netlist.

The partitioner only regroups leaf cells, it never changes them, so the two
netlists must have the same leaf cells (same names, same types) and the
same connectivity once hierarchy is flattened.  This compares, for every
net, the set of (leaf, pin, bit) and chip-port bits it touches, plus
constant tie-offs.  It is a stronger check than LEC for this purpose (it
also catches swapped-but-equivalent pins) and needs no solver.
"""
from __future__ import annotations

import re

from .netlist import flatten


def _canon(nl, strip_re=None):
    def nm(name):
        return strip_re.sub("", name, count=1) if strip_re else name

    types = {nm(lf.name): lf.type for lf in nl.leaves}
    nets = {}
    consts = set()
    for lf in nl.leaves:
        for port, bits in lf.conns.items():
            for i, b in enumerate(bits):
                key = (nm(lf.name), port, i)
                if isinstance(b, int):
                    nets.setdefault(b, set()).add(key)
                else:
                    consts.add((key, b))
    for pn, p in nl.ports.items():
        for i, b in enumerate(p["bits"]):
            if isinstance(b, int):
                nets.setdefault(b, set()).add(("<port>", pn, i))
            else:
                consts.add((("<port>", pn, i), b))
    return types, {frozenset(s) for s in nets.values() if len(s) > 1}, consts


def partition_insts(part_json, top):
    """Instances in the partitioned top whose type is a module of the netlist (the partitions)."""
    mods = part_json["modules"]
    t = mods.get(top) or next(m for m in mods.values() if m.get("attributes", {}).get("top"))
    return sorted(n for n, c in t["cells"].items() if c["type"] in mods)


def compare(orig_json, part_json, top, libcells=None, strip=None):
    if strip is None:
        insts = partition_insts(part_json, top)
        strip = r"^(?:%s)\." % "|".join(re.escape(i) for i in insts) if insts else r"^$^"
    a = flatten(orig_json, top, libcells)
    b = flatten(part_json, top, libcells)
    ta, na, ca = _canon(a)
    tb, nb, cb = _canon(b, re.compile(strip))
    res = {
        "leaves_orig": len(ta), "leaves_part": len(tb),
        "missing_leaves": sorted(set(ta) - set(tb))[:20],
        "extra_leaves": sorted(set(tb) - set(ta))[:20],
        "type_mismatch": sorted(n for n in set(ta) & set(tb) if ta[n] != tb[n])[:20],
        "nets_orig": len(na), "nets_part": len(nb),
        "nets_only_orig": len(na - nb), "nets_only_part": len(nb - na),
        "const_mismatch": len(ca ^ cb),
    }
    res["equivalent"] = (not res["missing_leaves"] and not res["extra_leaves"] and
                         not res["type_mismatch"] and res["nets_only_orig"] == 0 and
                         res["nets_only_part"] == 0 and res["const_mismatch"] == 0)
    if not res["equivalent"]:
        res["example_only_orig"] = [sorted(s)[:6] for s in list(na - nb)[:3]]
        res["example_only_part"] = [sorted(s)[:6] for s in list(nb - na)[:3]]
    return res
