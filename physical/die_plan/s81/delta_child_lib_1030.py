#!/usr/bin/env python3
"""DIE-S81-39 child-lib plan event (COORD 23:4x, 12.3 'signed or current real' views; data only under 12.20).

143 S81 types are WAIT-DEP in the kit wave: a hard_cores/contents child has a lef but no lib, and gen_phys
write_type_kit refuses 'macros have LEF but no timing liberty'.  For every such child module this script sets
hard_cores[].lib (TT liberty, the key gen_phys.type_macros reads) to a real view's TT lib, ONLY when the lib's port
bits equal the plan's own child pin table (pins_file, the plan of record) -- name set equal, no extra and no missing
bit.  A child whose candidate lib differs keeps no lib (its parents stay WAIT-DEP) and is reported.  Nothing else in
the plan changes (asserted: lef, pins, origins, outlines, clock, taps are untouched).

usage (repo root): delta_child_lib_1030.py PLAN_IN PLAN_OUT CANDIDATES.json REPORT.json
  CANDIDATES.json = {module: [repo-relative TT lib path, ...]} in preference order (first matching lib wins)."""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path.cwd()
PD = ROOT / "physical/die_plan/s81"
sys.path.insert(0, str(PD))
import compact_plan as CP  # noqa: E402

PG = {"VDD", "VSS", "VPWR", "VGND"}  # supply pins of the timing model are not signal ports
# SUPERSET=1: also accept a lib whose ports contain every plan pin bit plus extra ports (an older, wider interface of the
# same child; the extra ports stay unconnected).  Off by default: exact match only.
import os  # noqa: E402
SUPERSET = os.environ.get("SUPERSET") == "1"


def lib_bits(path):
    """Port bit names of a liberty cell: pin(x) -> x, bus(x) {bus_type: t} -> x[from..to]."""
    text = Path(path).read_text(errors="replace")
    types = {}
    for m in re.finditer(r'type\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{(.*?)\}', text, re.S):
        f = re.search(r"bit_from\s*:\s*(\d+)", m.group(2))
        t = re.search(r"bit_to\s*:\s*(\d+)", m.group(2))
        if f and t:
            types[m.group(1)] = (int(f.group(1)), int(t.group(1)))
    bits = set()
    for m in re.finditer(r'\bbus\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{\s*bus_type\s*:\s*"?([^";\s]+)"?', text):
        a, b = types[m.group(2)]
        for i in range(min(a, b), max(a, b) + 1):
            bits.add(f"{m.group(1)}[{i}]")
    # scalar pins: those outside bus groups; bus member pins are named x[i] and are already counted
    for m in re.finditer(r'\bpin\s*\(\s*"?([^")\s]+)"?\s*\)', text):
        bits.add(m.group(1).replace("\\", ""))
    return bits - PG


def plan_bits(h):
    pf = h.get("pins_file")
    if not pf:
        return None
    d = json.loads((PD / pf).read_text())
    return {p["name"] for p in d["pins"]}


def main():
    src, dst, cand_p, rp = sys.argv[1:5]
    text = Path(src).read_text()
    raw = json.loads(text)
    orig = copy.deepcopy(raw)
    cand = json.loads(Path(cand_p).read_text())
    need = {}
    for tn, t in raw["partition_types"].items():
        for kind in ("hard_cores", "contents"):
            for h in t.get(kind) or []:
                if h.get("lef") and not h.get("lib"):
                    need.setdefault(h["module"], []).append((tn, kind, h))
    rep = {}
    chosen = {}
    for m in sorted(need):
        r = rep[m] = dict(entries=len(need[m]), types=len({tn for tn, _, _ in need[m]}), tried=[])
        pb = {json.dumps(sorted(plan_bits(h) or [])) for _, _, h in need[m]}
        if len(pb) != 1 or pb == {"[]"}:
            r["verdict"] = "SKIP: plan pin tables differ between entries or are missing"
            continue
        want = set(json.loads(pb.pop()))
        for lib in cand.get(m, []):
            if not (ROOT / lib).is_file():
                r["tried"].append(dict(lib=lib, result="missing file"))
                continue
            got = lib_bits(ROOT / lib)
            extra, miss = sorted(got - want), sorted(want - got)
            ok = not miss and (not extra or SUPERSET)
            r["tried"].append(dict(lib=lib, result=("MATCH" if not extra else "SUPERSET") if not miss else "DIFF",
                                   lib_bits=len(got), plan_bits=len(want), extra=len(extra), missing=len(miss),
                                   extra_eg=extra[:4], missing_eg=miss[:4]))
            if ok:
                chosen[m] = lib
                break
        r["verdict"] = ("LIB " + chosen[m]) if m in chosen else "NO MATCHING LIB (stays WAIT-DEP)"
    for m, lib in chosen.items():
        for tn, kind, h in need[m]:
            h["lib"] = lib
    # nothing but the new lib keys
    for tn, t in raw["partition_types"].items():
        a, b = copy.deepcopy(t), orig["partition_types"][tn]
        for kind in ("hard_cores", "contents"):
            for x, y in zip(a.get(kind) or [], b.get(kind) or []):
                if "lib" in x and "lib" not in y:
                    x.pop("lib")
        assert a == b, tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == orig[k], k
    changed = sorted({tn for m in chosen for tn, _, _ in need[m]})
    for tn in changed:
        mm = re.search(r'^  "' + re.escape(tn) + r'": ', text, re.M)
        _, j = json.JSONDecoder().raw_decode(text, mm.end())
        text = text[:mm.end()] + CP._d(raw["partition_types"][tn], 2) + text[j:]
    assert json.loads(text) == raw
    Path(dst).write_text(text)
    still = sorted({tn for m in need if m not in chosen for tn, _, _ in need[m]})
    rep["_summary"] = dict(modules=len(need), libbed=len(chosen), types_changed=len(changed),
                           types_still_waitdep=len(still), still_waitdep=still,
                           modules_unmatched=sorted(m for m in need if m not in chosen))
    Path(rp).write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep["_summary"]))


if __name__ == "__main__":
    main()
