#!/usr/bin/env python3
"""Line-wise numeric delta of a regenerated kit vs the old kit (same line count expected).
usage: kit_delta.py OLD_KIT NEW_KIT OUT.json"""
import json, re, sys, filecmp, os
from pathlib import Path
old, new, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
num = re.compile(r'-?\d+\.\d+|-?\d+')
res = {"files_identical": [], "files_changed": {}, "only_old": [], "only_new": []}
fo = {p.relative_to(old).as_posix() for p in old.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
fn = {p.relative_to(new).as_posix() for p in new.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
res["only_old"] = sorted(fo - fn); res["only_new"] = sorted(fn - fo)
for f in sorted(fo & fn):
    a, b = old / f, new / f
    if filecmp.cmp(a, b, shallow=False):
        res["files_identical"].append(f); continue
    la, lb = a.read_text(errors='replace').splitlines(), b.read_text(errors='replace').splitlines()
    r = {"lines_old": len(la), "lines_new": len(lb), "changed_lines": 0, "max_abs_num_delta": 0.0, "nonnumeric_change_lines": 0, "deltas": {}}
    if len(la) == len(lb):
        for x, y in zip(la, lb):
            if x == y: continue
            r["changed_lines"] += 1
            if num.sub('#', x) != num.sub('#', y):
                r["nonnumeric_change_lines"] += 1; continue
            for u, v in zip(num.findall(x), num.findall(y)):
                if u != v:
                    d = round(abs(float(v) - float(u)), 6)
                    r["max_abs_num_delta"] = max(r["max_abs_num_delta"], d)
                    r["deltas"][str(d)] = r["deltas"].get(str(d), 0) + 1
    else:
        r["note"] = "line count differs"
    res["files_changed"][f] = r
res["n_identical"] = len(res["files_identical"])
json.dump(res, open(out, 'w'), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "files_identical"}, indent=1))
