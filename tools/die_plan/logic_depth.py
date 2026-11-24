#!/usr/bin/env python3
"""DEPTH-PRE-1123 (COORD 19:15; QC-ALLFIX-COLL depth.py): logic-depth census of the generated constructor netlists.

TTC-STAGE: the B1 F5 source had 3304 of 25172 flops at logic depth >= 18 (max 38/71), the CTS-read cpub39_1 1047 of 20203; a
static count would have shown it days before the CTS read.  A generated netlist (first line "// Generated fixed production-shape
math") is a flat list of `(* .. *) CELL [#(..)] u_N(.P(net), ...);` cells: qfd_bmath_dff* flops (D in, Q out) and combinational
cells (output Y).  The depth of a flop is the longest chain of combinational cells from a flop Q / module input to its D.

Budget: the 833 ps cycle is depth_config.json depth_levels[_by_die] (default 18) bmath levels ($OT_PRE_DEPTH_LEVELS wins).  plan_gate_pre class DEPTH FAILs per netlist with
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


CONFIG = Path(__file__).resolve().parent / "depth_config.json"


def config(path=None):
    try:
        return json.loads(Path(path or os.environ.get("OT_PRE_DEPTH_CONFIG") or CONFIG).read_text())
    except (OSError, ValueError):
        return {}


def levels(die=None, cfg=None):
    """DEPTH-CAP-CONFIG-1123: the depth budget = $OT_PRE_DEPTH_LEVELS, else depth_config.json depth_levels_by_die[die], else its
    depth_levels, else DEPTH_LEVELS (18)"""
    try:
        if os.environ.get("OT_PRE_DEPTH_LEVELS"):
            return int(os.environ["OT_PRE_DEPTH_LEVELS"])
    except ValueError:
        pass
    c = config() if cfg is None else cfg
    for v in ((c.get("depth_levels_by_die") or {}).get(die) if die else None, c.get("depth_levels")):
        try:
            if v is not None:
                return int(v)
        except (TypeError, ValueError):
            pass
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




def held_rules(raw=None, env=None):
    """DEPTH-HELD-1123: -> [(kind, glob, why)] of netlists whose deep flops are a known, held cause (HELD, not FAIL):
    depth_config.json accepted (COORD-accepted modules / types), the die's typed hold list (kit_wave.json dies.<die>.hold_items, read from
    $OT_KIT_WAVE_JSON or ~/coord/autopilot/kit_wave.json when present) and $OT_PRE_DEPTH_HELD (comma list of type globs)."""
    import fnmatch  # noqa: F401  (used by held_why)
    env = os.environ if env is None else env
    rules = []
    acc = config()
    for e in acc.get("accepted") or []:
        for m in e.get("modules") or []:
            rules.append(("module", m, e.get("why", "COORD-accepted")))
        for ty in e.get("types") or []:
            rules.append(("type", ty, e.get("why", "COORD-accepted")))
    die = ((raw or {}).get("die") or {}).get("name") if isinstance((raw or {}).get("die"), dict) else None
    kw = env.get("OT_KIT_WAVE_JSON") or os.path.expanduser("~/coord/autopilot/kit_wave.json")
    if die and os.path.isfile(kw):
        try:
            hi = ((json.loads(Path(kw).read_text()).get("dies") or {}).get(die) or {}).get("hold_items") or {}
        except (OSError, ValueError):
            hi = {}
        for it in (hi if isinstance(hi, (dict, list)) else []):
            rules.append(("type", str(it), f"typed hold list kit_wave.json dies.{die}.hold_items"))
    for ty in (env.get("OT_PRE_DEPTH_HELD") or "").split(","):
        if ty.strip():
            rules.append(("type", ty.strip(), "$OT_PRE_DEPTH_HELD"))
    return rules


def held_why(rules, module, types):
    """the reason a netlist is HELD: its module matches an accepted module glob, or EVERY plan type reaching it is held; else None"""
    import fnmatch
    for k, g, why in rules:
        if k == "module" and module and fnmatch.fnmatchcase(module, g):
            return f"{why} (module {g})"
    if types:
        whys = []
        for tn in sorted(types):
            w = next((f"{why} (type {g})" for k, g, why in rules if k == "type" and fnmatch.fnmatchcase(tn, g)), None)
            if w is None:
                return None
            whys.append(w)
        return whys[0] + (f" +{len(whys) - 1} type(s)" if len(whys) > 1 else "")
    return None


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
