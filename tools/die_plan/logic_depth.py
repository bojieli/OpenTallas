#!/usr/bin/env python3
"""DEPTH-PRE-1123 (COORD 19:15; QC-ALLFIX-COLL depth.py): logic-depth census of the generated constructor netlists.

TTC-STAGE: the B1 F5 source had 3304 of 25172 flops at logic depth >= 18 (max 38/71), the CTS-read cpub39_1 1047 of 20203; a
static count would have shown it days before the CTS read.  A generated netlist (first line "// Generated fixed production-shape
math") is a flat list of `(* .. *) CELL [#(..)] u_N(.P(net), ...);` cells: qfd_bmath_dff* flops (D in, Q out) and combinational
cells (output Y).  The depth of a flop is the longest chain of combinational cells from a flop Q / module input to its D.

Budget: the 833 ps cycle is DEPTH_LEVELS (18) bmath levels ($OT_PRE_DEPTH_LEVELS).  plan_gate_pre class DEPTH FAILs per netlist with
any flop at depth >= the budget (every generated netlist the plan's RTL reaches; without an as-built, every one under rtl/).

usage: logic_depth.py NETLIST.sv [...] [--levels N] [--json OUT]     exit 1 when any flop is at depth >= N
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

MARK = "// Generated fixed production-shape math"
FLOP = "qfd_bmath_dff"
DEPTH_LEVELS = 18
INST = re.compile(r"^\s*(?:\(\*[^*]*\*\)\s*)?([A-Za-z_]\w*)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*([A-Za-z_][\w$]*)\s*\((.*)\)\s*;\s*$")
PIN = re.compile(r"\.(\w+)\s*\(([^()]*)\)")
KEYWORDS = {"module", "input", "output", "inout", "wire", "reg", "assign", "endmodule", "parameter", "localparam"}


def levels():
    try:
        return int(os.environ.get("OT_PRE_DEPTH_LEVELS") or DEPTH_LEVELS)
    except ValueError:
        return DEPTH_LEVELS


def is_generated(path):
    try:
        with open(path, errors="replace") as f:
            return f.read(4096).lstrip().startswith(MARK)
    except OSError:
        return False


def census(path, budget=None, flop=FLOP):
    """-> dict(module, flops, deep, max, budget, hist {depth: n}, worst [(inst, depth)])"""
    budget = levels() if budget is None else budget
    drv, ins, kind, module = {}, {}, {}, None
    for line in open(path, errors="replace"):
        if module is None:
            m = re.match(r"\s*module\s+([A-Za-z_]\w*)", line)
            if m:
                module = m.group(1)
                continue
        m = INST.match(line)
        if not m or m.group(1) in KEYWORDS:
            continue
        t, u, body = m.groups()
        kind[u] = t
        ins[u] = []
        ff = t.startswith(flop)
        for p, n in PIN.findall(body):
            n = n.strip()
            if ff:
                if p == "Q":
                    drv[n] = u
                elif p == "D":
                    ins[u].append(n)
            elif p == "Y":
                drv[n] = u
            else:
                ins[u].append(n)
    memo = {}

    def depth_of(cell):                                  # iterative longest path; a combinational loop counts as 0 where it closes
        stack = [(cell, 0)]
        busy = set()
        while stack:
            c, i = stack.pop()
            if c in memo:
                continue
            if i == 0:
                busy.add(c)
            src = ins[c]
            while i < len(src):
                d = drv.get(src[i])
                if d is not None and not kind[d].startswith(flop) and d not in memo and d not in busy:
                    stack.append((c, i + 1))
                    stack.append((d, 0))
                    break
                i += 1
            else:
                best = 0
                for n in src:
                    d = drv.get(n)
                    if d is not None and not kind[d].startswith(flop):
                        best = max(best, memo.get(d, 0))
                memo[c] = best + 1
                busy.discard(c)
        return memo[cell]

    hist, per = Counter(), []
    for u, t in kind.items():
        if not t.startswith(flop):
            continue
        dp = 0
        for n in ins[u]:
            d = drv.get(n)
            if d is not None and not kind[d].startswith(flop):
                dp = max(dp, depth_of(d))
        hist[dp] += 1
        per.append((dp, u))
    per.sort(reverse=True)
    deep = sum(v for k, v in hist.items() if k >= budget)
    return dict(path=str(path), module=module, flops=sum(hist.values()), deep=deep, max=max(hist) if hist else 0, budget=budget,
                hist=dict(sorted(hist.items())), worst=[(u, d) for d, u in per[:5]])


def finding(r):
    if not r["deep"]:
        return None
    return (f"FAIL DEPTH {r['module']}: {r['deep']} of {r['flops']} flops at logic depth >= {r['budget']} (the 833 ps budget; max "
            f"{r['max']}; worst {', '.join(f'{u}={d}' for u, d in r['worst'][:3])}) in {r['path']} -- cap / retime the constructor")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("netlists", nargs="+")
    ap.add_argument("--levels", type=int)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    rs = [census(p, a.levels) for p in a.netlists]
    for r in rs:
        print(finding(r) or f"PASS DEPTH {r['module']}: {r['flops']} flops, max depth {r['max']} < {r['budget']}")
    if a.json:
        Path(a.json).write_text(json.dumps(rs, indent=1) + "\n")
    return 1 if any(r["deep"] for r in rs) else 0


if __name__ == "__main__":
    sys.exit(main())
