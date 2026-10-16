#!/usr/bin/env python3
"""RESET-PORT FANOUT lint (design standard, coordinator 2026-10-10, drive-1010).

A reset INPUT PORT (name matching PORT_RE) must drive only a local ot_rst_relay, never the block's reset flops directly:
on ~7 blocks the port -> thousands-of-flops net was the worst setup / hold path (hgi su_unit / su_ctl, idx-topk, qwen
tile_e, ds qelem x1b).  Counts, per reset-named input port bit, the flop / latch cells with ANY input pin (D, R, S, E,
...) driven by that port through buffers / inverters and at most ONE other gate (the mux / AND of a synchronous reset).

  python3 rst_port_fanout.py netlist.json [--top T] [--max 32] [--port-re REGEX]   -> exit 1 + report on violation
Netlist: yosys write_json after `proc; flatten; techmap` (the rtl_boundary elaboration).
"""
import argparse
import json
import re
import sys

PORT_RE = r"(^|_)(p?a?rst|reset)(_?n|_ni|_i)?$"
MAX_FLOPS = 32
SEQ = re.compile(r"^\$_(S?DFF|DFFE|SDFFE|SDFFCE|ALDFF|ALDFFE|DFFSR|DFFSRE|DLATCH|SR)")
ZERO = {"$_BUF_", "$_NOT_"}


def _top(netlist, top):
    mods = netlist["modules"]
    if top and top in mods:
        return mods[top]
    return next((m for m in mods.values() if str((m.get("attributes") or {}).get("top", "0")).strip("0") != ""),
                None) or next(iter(mods.values()))


def fanout(netlist, top=None, port_re=PORT_RE):
    """{port bit name: number of flop cells it drives directly (BUF/NOT + at most one gate)} for reset-named input ports"""
    mod = _top(netlist, top)
    rx = re.compile(port_re, re.I)
    root = {}
    for name, p in mod["ports"].items():
        if p["direction"] != "input" or not rx.search(name):
            continue
        for i, b in enumerate(p["bits"]):
            if isinstance(b, int):
                root[b] = f"{name}[{i}]" if len(p["bits"]) > 1 else name
    if not root:
        return {}
    # propagate through buffers / inverters only
    fwd = {}
    for c in mod["cells"].values():
        if c["type"] in ZERO:
            dirs, conns = c.get("port_directions", {}), c["connections"]
            ins = [b for pn, bs in conns.items() if dirs.get(pn) == "input" for b in bs if isinstance(b, int)]
            outs = [b for pn, bs in conns.items() if dirs.get(pn) == "output" for b in bs if isinstance(b, int)]
            for i in ins:
                fwd.setdefault(i, []).extend(outs)
    reach = {}
    for b, name in root.items():
        stack, seen = [b], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            reach.setdefault(x, set()).add(name)
            stack.extend(fwd.get(x, []))
    # one extra gate level (a synchronous reset is a mux / AND in front of D: rst_n -> 64 gates -> 64 flops is the same
    # wide net), then buffers / inverters again
    one = {}
    for c in mod["cells"].values():
        if c["type"] in ZERO or SEQ.match(c["type"]) or not c["type"].startswith("$_"):
            continue
        dirs, conns = c.get("port_directions", {}), c["connections"]
        names = set()
        for pn, bs in conns.items():
            if dirs.get(pn) == "input":
                for b in bs:
                    if isinstance(b, int):
                        names |= reach.get(b, set())
        if names:
            for pn, bs in conns.items():
                if dirs.get(pn) == "output":
                    for b in bs:
                        if isinstance(b, int):
                            one.setdefault(b, set()).update(names)
    for b, names in list(one.items()):
        stack, seen = [b], set()
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            one.setdefault(x, set()).update(names)
            stack.extend(fwd.get(x, []))
    reach = {b: reach.get(b, set()) | one.get(b, set()) for b in set(reach) | set(one)}
    count = {n: 0 for n in root.values()}
    for c in mod["cells"].values():
        if not SEQ.match(c["type"]):
            continue
        dirs, conns = c.get("port_directions", {}), c["connections"]
        hit = set()
        for pn, bs in conns.items():
            if dirs.get(pn) == "output":
                continue
            for b in bs:
                if isinstance(b, int):
                    hit |= reach.get(b, set())
        for n in hit:
            count[n] += 1
    return count


def violations(count, max_flops=MAX_FLOPS):
    return {n: k for n, k in count.items() if k > max_flops}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("netlist")
    ap.add_argument("--top")
    ap.add_argument("--max", type=int, default=MAX_FLOPS)
    ap.add_argument("--port-re", default=PORT_RE)
    a = ap.parse_args(argv)
    count = fanout(json.load(open(a.netlist)), a.top, a.port_re)
    bad = violations(count, a.max)
    for n, k in sorted(count.items()):
        print(f"RST_PORT_FANOUT {n} {k} flops{' > ' + str(a.max) + ' VIOLATION' if n in bad else ''}")
    if bad:
        print(f"RST_PORT_FANOUT_FAIL: {len(bad)} reset port bit(s) drive > {a.max} flops directly -- route the port "
              f"through rtl/lib/ot_rst_relay.sv (one relay copy per region)")
        return 1
    print("RST_PORT_FANOUT_PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
