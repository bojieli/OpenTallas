#!/usr/bin/env python3
"""TYPE-SAFE-2 11-08: latency miter of the relay constructor on BOUND RTL (structural, exact), per LANE.

Inputs: the plan the event produced (NEW_PLAN), the event JSON, and two bind output rtl dirs from the same bind tool:
OLD (base plan) and NEW (event plan).  For every .sv that differs, every differing line must be a register stage of a
declared lane's bus, and per lane the stages added in the source type (out bus) plus the receiver type (in bus) must
equal the declared pin-cycle delta:
  stage forms counted: `ot_dp_dly #(.W(w), .D(d)) u_lpad_<bus>` (D, the native lane pad, right after u_bin_<bus>) and
  `ot_dp_st #(.W(w)) u_ist_<bus>_<j>` (one station; kit_istations / native_istations)
  tolerated: the u_bin_/u_bout_ face register line of that bus re-pointed onto the first/last stage, the stage wires,
  comments and the `// lane ... N cycles` port notes (they restate the latency).
Each stage is one register on the whole bus (data + epoch), so a lane whose only change is k added stages is the old
lane delayed by exactly k cycles (new == old delayed k), and every other line is identical.

usage: ts_relay_miter.py NEW_PLAN.json EVENT.json OLD_RTL_DIR NEW_RTL_DIR [OUT.json] -> exit 0 PASS / 1 FAIL"""
import difflib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


def norm(txt):
    out = []
    for ln in txt.splitlines():
        s = re.sub(r"//.*$", "", ln).strip()
        if s:
            out.append(re.sub(r"\s+", " ", s))
    return out


def main(argv):
    plan_f, ev_f, old_d, new_d = argv[1:5]
    out_f = argv[5] if len(argv) > 5 else None
    P = json.load(open(plan_f))
    ev = json.load(open(ev_f))
    ports = {p["id"]: p for p in P["ports"]}
    ptype = {p["name"]: p["type"] for p in P["partitions"]}
    declared = defaultdict(int)
    for e in ev["edits"]:
        for lid, v in e["lanes"].items():
            declared[lid] = max(declared[lid], v["delta"])
    # (type, bus) -> lanes through it (source out bus / receiver in bus)
    tb = defaultdict(set)
    for ln in P["lanes"]:
        if ln["id"] not in declared:
            continue
        a, b = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        if a["src"]["part"] in ptype:
            tb[(ptype[a["src"]["part"]], a["src"]["bus"])].add(ln["id"])
        if b["dst"]["part"] in ptype:
            tb[(ptype[b["dst"]["part"]], b["dst"]["bus"])].add(ln["id"])
    # a type's bus stage delta is shared by all its instances' lanes: count it once per (type, bus) and attribute it to
    # each lane through it (instances of one type are identical)
    realised = defaultdict(int)
    bad, files = [], 0
    for nf in sorted(Path(new_d).glob("*.sv")):
        of = Path(old_d) / nf.name
        if not of.exists():
            bad.append(f"new file {nf.name}")
            continue
        A, B = norm(of.read_text()), norm(nf.read_text())
        if A == B:
            continue
        files += 1
        tn = nf.stem[5:] if nf.stem.startswith("s81p_") else nf.stem
        buses = {b for (t, b) in tb if t == tn}
        sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
        delta = defaultdict(int)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            for sign, lines in ((-1, A[i1:i2]), (1, B[j1:j2])):
                for ln in lines:
                    m = re.match(r"^ot_dp_dly #\(\.W\(\d+\), \.D\((\d+)\)\) u_lpad_(\w+) \(", ln)
                    if m and m.group(2) in buses:
                        delta[m.group(2)] += sign * int(m.group(1))
                        continue
                    m = re.match(r"^ot_dp_st #\(\.W\(\d+\)\) u_ist_(\w+)_(\d+) \(", ln)
                    if m and m.group(1) in buses:
                        delta[m.group(1)] += sign
                        continue
                    m = re.match(r"^ot_dp_st #\(\.W\(\d+\)\) u_b(?:in|out)_(\w+) \(", ln)
                    if m and m.group(1) in buses:
                        continue
                    if re.match(r"^wire ", ln) and any(re.search(rf"\b{re.escape(b)}_(?:is\d+_e?q|b|eb|q|eq)\b", ln)
                                                       for b in buses):
                        continue
                    bad.append(f"{nf.name}: {'+' if sign > 0 else '-'} {ln[:180]}")
        for b, d in delta.items():
            for lid in tb[(tn, b)]:
                realised[lid] += d
    mism = {lid: dict(declared=declared[lid], realised=realised.get(lid, 0))
            for lid in declared if realised.get(lid, 0) != declared[lid]}
    ok = not bad and not mism
    rec = dict(verdict="PASS" if ok else "FAIL", lanes=len(declared), files_changed=files,
               lanes_matching=len(declared) - len(mism), mismatch=dict(list(mism.items())[:60]), n_mismatch=len(mism),
               undeclared_changes=bad[:60], n_undeclared=len(bad))
    if out_f:
        Path(out_f).write_text(json.dumps(dict(rec, realised=realised, declared=declared), indent=1) + "\n")
    print(json.dumps(rec, indent=1)[:4000])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
