#!/usr/bin/env python3
"""KV/system die case -> construction plan in the shape tools/fleet_viz/dataflow_links.py `s81` reads (owner review in the
fleet-viz Dataflow Explorer, coordinator 2026-10-16).

Reads a kvsys_prep case's PRE-EXPANSION netlist / placement / frame LEF (case_kv/{die.v,place.tcl,elements.lef}.preexp:
the block-level die the planner built; real leaves are inside the frames) and writes
  plan.json.gz   {die: [W, H], insts: [[name, master, x, y, w, h, orient, kind, region]], buses: [[id, cls, bits, ends]],
                  scope, source_commit}
  pins.lef.gz    the frame LEF (exact pin rectangles for pin_align)
kind 'rly' marks the relay stations (qkd_rly_* / qkd_rlys_*) so the links collapse into their chains.  Direction: on a
relayed chain the first segment's non-relay end drives (it feeds relay port a) and the last segment's end sinks (relay
port b feeds it); a bus without relays lists its ends in netlist order (direction unknown: recorded in scope).

    python3 tools/qwen_kv_die/kv_dataflow_export.py --case RUN/case_kv --out DIR
"""
import argparse
import collections
import gzip
import json
import re
from pathlib import Path

CLOCKISH = re.compile(r'^n_(clk|ck|rst|pll|rso|hboot|rs_)')


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args(argv)
    c = a.case
    sfx = '.preexp' if (c / 'die.v.preexp').exists() else ''
    lef = (c / f'elements.lef{sfx}').read_text()
    size = {}
    cur = None
    for ln in lef.splitlines():
        t = ln.split()
        if t[:1] == ['MACRO']:
            cur = t[1]
        elif t[:1] == ['SIZE'] and cur:
            size[cur] = (float(t[1]), float(t[3]))
    place = {}
    for ln in open(c / f'place.tcl{sfx}'):
        m = re.search(r'findInst (\S+)\] ([\d.]+) ([\d.]+) (\S+)', ln)
        if m:
            place[m.group(1)] = (float(m.group(2)), float(m.group(3)), m.group(4))
    width, inst, conns = {}, {}, collections.defaultdict(list)
    for ln in open(c / f'die.v{sfx}'):
        m = re.match(r'\s*wire \[(\d+):(\d+)\] (\S+);', ln)
        if m:
            width[m.group(3)] = int(m.group(1)) - int(m.group(2)) + 1
            continue
        m = re.match(r'\s*(\w+) (\w+) \((.*)\);\s*$', ln)
        if m and m.group(1) not in ('module', 'wire', 'input', 'output'):
            inst[m.group(2)] = m.group(1)
            for p, n in re.findall(r'\.(\w+)\((n_[A-Za-z0-9_]+)', m.group(3)):
                conns[n].append((m.group(2), p))
    rly = lambda n: inst.get(n, '').startswith(('qkd_rly', 'qkd_rlys'))  # noqa: E731
    insts = []
    W = H = 0.0
    for n, (x, y, o) in place.items():
        ms = inst.get(n)
        if ms not in size:
            continue
        w, h = size[ms]
        W, H = max(W, x + w), max(H, y + h)
        fam = re.sub(r'(_[A-Z]{2})?(_\d+)*$', '', n)
        insts.append([n, ms, x, y, w, h, o, 'rly' if rly(n) else 'block', fam])
    buses = []
    for n, ends in conns.items():
        if CLOCKISH.match(n) or len(ends) < 2:
            continue
        ends = [(i, p) for i, p in ends if i in place]
        if len(ends) < 2:
            continue
        # driver first: a relay's b output drives its segment; a non-relay end feeding a relay's a input drives
        drv = [e for e in ends if rly(e[0]) and e[1] == 'b']
        if not drv:
            ra = [e for e in ends if rly(e[0]) and e[1] == 'a']
            drv = [e for e in ends if not rly(e[0])] if ra else []
        order = drv[:1] + [e for e in ends if e not in drv[:1]]
        cls = 'relay_hop' if any(rly(e[0]) for e in ends) else 'data'
        buses.append([n[2:], cls, width.get(n, 1), [list(e) for e in order]])
    a.out.mkdir(parents=True, exist_ok=True)
    src = (c / 'SOURCE_COMMIT').read_text().strip() if (c / 'SOURCE_COMMIT').exists() else None
    plan = dict(die=[round(W, 3), round(H, 3)], insts=insts, buses=buses, source_commit=src,
                scope=f'Qwen KV/system die case {c} (pre-expansion frames{sfx}); relays kind rly; direction known on relayed '
                      'chains only (a non-relayed bus lists its ends in netlist order)')
    (a.out / 'plan.json.gz').write_bytes(gzip.compress(json.dumps(plan).encode()))
    (a.out / 'pins.lef.gz').write_bytes(gzip.compress(lef.encode()))
    print(f'KV DATAFLOW EXPORT insts={len(insts)} buses={len(buses)} die={W:.1f}x{H:.1f} -> {a.out}')


if __name__ == '__main__':
    main()
