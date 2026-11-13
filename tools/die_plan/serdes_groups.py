#!/usr/bin/env python3
"""HARD-S81-SERDES-1 2026-11-13: module membership of a FLAT synthesized netlist for placement regions.

The kit netlist is flat: registers keep their hierarchical names, logic cells do not.  Every register is labelled by
the first matching group regexp; every logic cell takes the label of the nearest labelled register it drives (backward
breadth-first walk from the register data pins, through logic only).  Output: one "group<TAB>instance" line per member.

  serdes_groups.py NETLIST.v OUT.txt  name=regexp [name=regexp ...]
"""
import collections
import re
import sys

OUT_PINS = {"Y", "Q", "QN", "CON", "SN", "CO", "S"}
inst_re = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+(\\\S+\s|[A-Za-z_][A-Za-z0-9_$\[\].]*)\s*\(\s*$")
pin_re = re.compile(r"\.([A-Za-z0-9_\[\]]+)\((.*?)\)\s*,?\s*$")


def main(argv):
    net, out = argv[1], argv[2]
    groups = [(a.split("=", 1)[0], re.compile(a.split("=", 1)[1])) for a in argv[3:]]
    insts = {}            # name -> (cell, [input nets], [output nets])
    cur = None
    with open(net, errors="replace") as f:
        for line in f:
            if cur is None:
                m = inst_re.match(line)
                if m and m.group(1) not in ("module", "input", "output", "wire", "assign", "inout"):
                    cur = [m.group(1), m.group(2).strip().lstrip("\\"), [], []]
                continue
            s = line.strip()
            if s.startswith(");"):
                insts[cur[1]] = (cur[0], cur[2], cur[3]); cur = None; continue
            m = pin_re.match(s)
            if m:
                n = m.group(2).strip()
                if not n or "'" in n or n.startswith("{"):
                    continue
                (cur[3] if m.group(1).split("[")[0] in OUT_PINS else cur[2]).append(n.lstrip("\\").strip())
    drv = {}
    for name, (cell, ins, outs) in insts.items():
        for n in outs:
            drv[n] = name
    is_seq = lambda c: "DFF" in c or "DLL" in c or "DHL" in c or "LATCH" in c
    is_macro = lambda c: c.startswith("ot_")
    label = {}
    q = collections.deque()
    for name, (cell, ins, outs) in insts.items():
        if is_seq(cell):
            for g, rx in groups:
                if rx.search(name):
                    label[name] = g; q.append(name); break
    nseq = len(label)
    while q:
        name = q.popleft(); g = label[name]
        for n in insts[name][1]:
            d = drv.get(n)
            if d is None or d in label:
                continue
            c = insts[d][0]
            if is_seq(c) or is_macro(c):
                continue
            label[d] = g; q.append(d)
    cnt = collections.Counter(label.values())
    with open(out, "w") as f:
        for name, g in label.items():
            f.write(f"{g}\t{name}\n")
    print(f"SERDES_GROUPS instances {len(insts)} labelled {len(label)} (registers {nseq}) " + " ".join(f"{g}={cnt[g]}" for g, _ in groups))


if __name__ == "__main__":
    main(sys.argv)
