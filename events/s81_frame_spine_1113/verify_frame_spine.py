#!/usr/bin/env python3
"""verify_frame_spine.py BASE NEW --types-file F [--out R.json]

FRAME-SPINE-1113 delta audit: every difference between BASE and NEW, as JSON key paths.  Allowed: in the listed types
only hard_cores, internal_stations, clock.taps and clock.added_taps.  Anything else is printed as NOT-ALLOWED.
Also: per base item (type name up to '__pv'), all pv types carry identical hard_cores (inst, origin, orient)."""
import collections
import json
import sys

ALLOWED = (("hard_cores",), ("internal_stations",), ("clock", "taps"), ("clock", "added_taps"))


def diff(a, b, path, out):
    if type(a) is not type(b):
        out.append(path)
        return
    if isinstance(a, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b:
                out.append(path + (k,))
            else:
                diff(a[k], b[k], path + (k,), out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(path)
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diff(x, y, path + (i,), out)
    elif a != b:
        out.append(path)


def main():
    a = sys.argv[1:]
    B, N = json.load(open(a[0])), json.load(open(a[1]))
    T = set(open(a[a.index("--types-file") + 1]).read().split())
    bad, ok = [], collections.Counter()
    for k in set(B) | set(N):
        if k == "partition_types":
            continue
        if json.dumps(B.get(k), sort_keys=True) != json.dumps(N.get(k), sort_keys=True):
            bad.append(("<top>", k))
    pb, pn = B["partition_types"], N["partition_types"]
    changed = set()
    for tn in set(pb) | set(pn):
        if tn not in pb or tn not in pn:
            bad.append((tn, "<type added/removed>"))
            continue
        if json.dumps(pb[tn], sort_keys=True) == json.dumps(pn[tn], sort_keys=True):
            continue
        changed.add(tn)
        d = []
        diff(pb[tn], pn[tn], (), d)
        for p in d:
            key = next((al for al in ALLOWED if tuple(p[:len(al)]) == al), None)
            if tn in T and key:
                ok[".".join(key)] += 1
            else:
                bad.append((tn, ".".join(map(str, p))))
    pv = collections.defaultdict(list)
    for tn in sorted(changed):
        pv[tn.split("__pv")[0]].append(tn)
    same = {}
    for it, ts in sorted(pv.items()):
        sig = {json.dumps(sorted((c["inst"], c["origin_um"], c.get("orient")) for c in pn[t]["hard_cores"])) for t in ts}
        same[it] = dict(types=len(ts), identical_hard_cores=len(sig) == 1)
    rep = dict(changed_types=len(changed), changed_not_in_list=sorted(changed - T), allowed_diffs=dict(ok),
               not_allowed=[list(x) for x in bad[:500]], not_allowed_n=len(bad), pv_identical=same)
    print(json.dumps({k: v for k, v in rep.items() if k != "not_allowed"}, indent=1))
    for x in bad[:40]:
        print("NOT-ALLOWED", x)
    if "--out" in a:
        json.dump(rep, open(a[a.index("--out") + 1], "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
