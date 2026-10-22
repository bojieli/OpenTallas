#!/usr/bin/env python3
"""HBM-PGLG2 10-19: UNLOADED input pins of a closed leaf, read from its ROUTED NETLIST (never from a pin name).

A closed leaf may keep input ports that drive nothing inside it (KIND0 kind0_l4_leaf1: clk_insert_0..3 / clk_stage_4 --
the RTL declares them, synthesis removed every load).  A landed parent ties them to its region root like the leaf's
real clock pins; clock_entries.tcl must then admit them as harmless (no sink, no arc) instead of failing "CTS source must
reach only standard-cell clock pins".  The proof is the leaf's routed netlist (<route>/6_final.v of the CLOSED route):
an input port bit is UNLOADED when no instance connection and no continuous assignment reads it.

  unloaded_pins.py NETLIST --top TOP --job JOB [--out unloaded_pins.json]

writes {"schema": 1, "job", "top", "netlist": basename, "netlist_sha256", "inputs": n, "unloaded": [pin, ...]}.  The
file is committed next to the closed record's signoff.sdc; clock_entry_constraints.landed_unused_pins reads it and
cross-checks every listed pin against the leaf's ETMs (capacitance 0, no timing group, not a related pin)."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

_ID = r'(?:\\\S+|[A-Za-z_][\w$]*)'


def _strip_comments(text):
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    return re.sub(r'//[^\n]*', ' ', text)


def module_body(text, top):
    m = re.search(r'\bmodule\s+' + re.escape(top) + r'\s*\((.*?)\)\s*;(.*?)\bendmodule\b', text, re.S)
    if not m:
        raise ValueError(f'module {top} not found in the routed netlist')
    return m[2]


def unloaded_inputs(text, top):
    """(input port bits, unloaded port bits) of module `top` of a flat routed Verilog netlist"""
    body = module_body(_strip_comments(text), top)
    inputs, rest = [], []
    for stmt in body.split(';'):
        s = stmt.strip()
        d = re.match(r'input\s+(?:wire\s+)?(?:\[(\d+):(\d+)\]\s*)?(.*)$', s, re.S)
        if d:
            names = [n.strip() for n in d[3].split(',') if n.strip()]
            for n in names:
                if d[1] is None:
                    inputs.append(n)
                else:
                    hi, lo = int(d[1]), int(d[2])
                    inputs.extend(f'{n}[{i}]' for i in range(min(hi, lo), max(hi, lo) + 1))
            continue
        if re.match(r'(output|inout|wire|reg|supply0|supply1|tri)\b', s):
            continue
        rest.append(s)
    # every read of a net: instance connections .PIN(expr) and assign right-hand sides (and concatenations)
    reads = set()
    for s in rest:
        if s.startswith('assign'):
            lhs, _, rhs = s[len('assign'):].partition('=')
            exprs = [rhs]
        else:
            exprs = re.findall(r'\.\s*' + _ID + r'\s*\(([^()]*)\)', s)
        for e in exprs:
            for tok in re.finditer(r'(' + _ID + r')\s*(\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?', e):
                name = tok[1].rstrip()
                if tok[2] is None:
                    reads.add(name)
                elif tok[4] is None:
                    reads.add(f'{name}[{int(tok[3])}]')
                else:
                    a, b = int(tok[3]), int(tok[4])
                    reads.update(f'{name}[{i}]' for i in range(min(a, b), max(a, b) + 1))
    def used(p):
        base = p.split('[', 1)[0]
        return p in reads or base in reads
    return inputs, [p for p in inputs if not used(p)]


def evidence(netlist, top, job):
    data = Path(netlist).read_bytes()
    inputs, unloaded = unloaded_inputs(data.decode(), top)
    if not inputs:
        raise ValueError(f'{netlist}: module {top} has no input ports')
    return dict(schema=1, job=job, top=top, netlist=Path(netlist).name,
                netlist_sha256=hashlib.sha256(data).hexdigest(), inputs=len(inputs), unloaded=sorted(unloaded))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('netlist')
    ap.add_argument('--top', required=True)
    ap.add_argument('--job', required=True)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    rep = json.dumps(evidence(a.netlist, a.top, a.job), indent=1) + '\n'
    if a.out:
        Path(a.out).write_text(rep)
    sys.stdout.write(rep)
    return 0


if __name__ == '__main__':
    sys.exit(main())
