#!/usr/bin/env python3
"""depth_scan.py -- PRECHECK-1119 DEPTH: logic levels per register D cone in ASAP7 CELLS, read from a kit's mapped
synthesis netlist (1_2_yosys.v), for CBC-RULES-1119 rule 3 (cbc_pass.py --depth).

  depth_scan.py --kit-work KIT/work [--type T] [--min-levels 10] >> depth.tsv
  depth_scan.py --roots /srv/opentallas-scratch2/claude/ot-jobs [--max-age-h 48] --out depth.tsv   (newest kit per type)

Output rows: type <TAB> endpoint <TAB> levels  (cbc_pass.depth_rows format; endpoint = capture instance.pin or port).
Levels = combinational standard cells on the longest path from a launch (register / latch output, input port, macro
output, constant) to the endpoint (register / latch data pin, macro input, output port).  ICG and clock pins are not
endpoints.  Rows below --min-levels are not written (the CBC limit is cbc_rules.DEPTH_LEVELS_MAX = 13).
A generic-gate yosys depth (precheck_synth) is NOT this number: unmapped 2-input gates over-count 1.3-1.6x and the
S81 leaf read 276 generic levels through unbroken adder chains, so cell levels come from the kit netlist.
"""
import argparse
import collections
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import cbc_rules as CBC  # noqa: E402
sys.path.pop(0)

SEQ = re.compile(r"^(ASYNC_DFF|DFF|DHL|DLL|SDF|ICG)", re.I)
STD = re.compile(r"_ASAP7_")
OUT_PINS = {"Y", "QN", "Q", "CON", "SN", "H", "L", "GCLK", "IQ", "IQN"}
CLK_PINS = {"CLK", "CK", "CLKN", "GCLK", "ENA", "SE"}
INST = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+(\\\S+|[A-Za-z_][\w$.\[\]]*)\s*\((.*?)\)\s*;", re.S | re.M)
PIN = re.compile(r"\.([A-Za-z_]\w*)\s*\(\s*(.*?)\s*\)\s*(?:,|$)", re.S)
OUTPORT = re.compile(r"^\s*output\s+(?:wire\s+)?(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?(\\\S+|[A-Za-z_]\w*)\s*;", re.M)


def nets_of(expr):
    e = expr.strip()
    if not e:
        return []
    if e.startswith("{") and e.endswith("}"):
        return [x.strip() for x in re.split(r",(?![^\[]*\])", e[1:-1]) if x.strip()]
    return [e]


def is_const(n):
    return bool(re.match(r"^\d+'[bhdo]", n)) or n in ("1'b0", "1'b1")


def levels(text, min_levels=10):
    """[(endpoint, levels)] over min_levels, and the max level"""
    drv = {}                 # net -> ('comb', inst) | ('launch', None)
    comb_in = {}             # comb inst -> [input nets]
    ends = []                # (endpoint, net)
    for m in INST.finditer(text):
        cell, inst, body = m.group(1), m.group(2).strip(), m.group(3)
        if cell in ("module", "assign", "wire", "input", "output"):
            continue
        pins = PIN.findall(body)
        std = bool(STD.search(cell))
        seq = std and bool(SEQ.match(cell))
        if std and not seq:
            ins = []
            for p, e in pins:
                for n in nets_of(e):
                    if p in OUT_PINS:
                        drv[n] = ("comb", inst)
                    elif not is_const(n):
                        ins.append(n)
            comb_in[inst] = ins
        elif seq:
            for p, e in pins:
                for n in nets_of(e):
                    if p in OUT_PINS:
                        drv[n] = ("launch", None)
                    elif p not in CLK_PINS and not is_const(n):
                        ends.append((f"{inst}.{p}", n))
        else:                # macro / black box: inputs are endpoints, anything it drives is a launch
            for p, e in pins:
                for n in nets_of(e):
                    if not is_const(n):
                        ends.append((f"{inst}.{p}", n))
    for m in OUTPORT.finditer(text):
        name = m.group(3)
        if m.group(1):
            for b in range(min(int(m.group(1)), int(m.group(2))), max(int(m.group(1)), int(m.group(2))) + 1):
                ends.append((f"port:{name}[{b}]", f"{name}[{b}]"))
        else:
            ends.append((f"port:{name}", name))
    lv = {}

    def net_level(n0):
        stack, onstack = [(n0, False)], set()
        while stack:
            n, expanded = stack.pop()
            if n in lv:
                continue
            d = drv.get(n)
            if not d or d[0] != "comb":
                lv[n] = 0
                continue
            ins = comb_in.get(d[1], [])
            if expanded:
                onstack.discard(n)
                lv[n] = 1 + max((lv.get(x, 0) for x in ins), default=0)    # a loop member still open counts 0
                continue
            onstack.add(n)
            stack.append((n, True))
            stack.extend((x, False) for x in ins if x not in lv and x not in onstack)
        return lv[n0]

    out = []
    mx = 0
    for ep, n in ends:
        v = net_level(n) if n in drv else 0
        mx = max(mx, v)
        if v >= min_levels:
            out.append((ep, v))
    return out, mx


def kit_netlist(kit_work):
    c = sorted(Path(kit_work).glob("run/results/*/*/base/1_2_yosys.v"))
    return c[0] if c else None


def kit_type(kit):
    m = re.match(r"^(.+?)-(route|place|cts|grt|kit|sign|signoff|flow|full)-", Path(kit).name)
    return m.group(1) if m else Path(kit).name


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit-work", default="")
    ap.add_argument("--type", default="")
    ap.add_argument("--roots", default="")
    ap.add_argument("--max-age-h", type=float, default=48)
    ap.add_argument("--min-levels", type=int, default=10)
    ap.add_argument("--out", default="")
    a = ap.parse_args(argv)
    jobs = []
    if a.kit_work:
        jobs.append((a.type or kit_type(Path(a.kit_work).parent), Path(a.kit_work)))
    now = time.time()
    newest = {}
    for root in [r for r in a.roots.split(",") if r]:
        for k in Path(root).glob("*/work"):
            nl = kit_netlist(k)
            if not nl or now - nl.stat().st_mtime > a.max_age_h * 3600:
                continue
            tn = kit_type(k.parent)
            if tn not in newest or nl.stat().st_mtime > newest[tn][0]:
                newest[tn] = (nl.stat().st_mtime, k)
    jobs += [(tn, k) for tn, (_t, k) in sorted(newest.items())]
    fh = open(a.out, "a") if a.out else sys.stdout
    for tn, k in jobs:
        nl = kit_netlist(k)
        if not nl:
            continue
        rows, mx = levels(nl.read_text(errors="replace"), a.min_levels)
        for ep, v in sorted(rows, key=lambda r: -r[1]):
            fh.write(f"{tn}\t{ep}\t{v}\n")
        print(f"DEPTH {tn}: max {mx} levels, {sum(1 for _e, v in rows if v > CBC.DEPTH_LEVELS_MAX)} endpoints > "
              f"{CBC.DEPTH_LEVELS_MAX} ({nl})", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
