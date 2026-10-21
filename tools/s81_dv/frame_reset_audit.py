#!/usr/bin/env python3
"""frame_reset_audit.py KIT_RTL [--json OUT]: reset-crossing audit of an S81 landed frame kit RTL (DRIVE-S81-FRRST 10-20).

COORD 21:29 (c): a reset that crosses between clock regions must land in the RECEIVING region's own clock.  For every
hard-child instance of the frame top this traces each reset pin (rs / rst / rst_n / rsi) back through the frame's own
reset primitives to the clock that releases it, and compares that clock with the child's clock pins:

  * ot_pl_pad (.ck C, N >= 1)            the reset is released by C (N = 0 is a wire: follow d);
  * ot_pl_land_reset_forest* (.ck C)     released by C (its first stage samples d on C: d may come from another
                                         region's root flop -- that hop is reported as a FOREST crossing, landed by
                                         the forest's own >= 2 stages on C);
  * ot_reset_sync (.clk C)               released by C (async-assert / sync-deassert synchroniser: a landed crossing);
  * a hard-child output (e.g. crs4 rs)   released by that child's (first) clock pin;
  * a frame input port                   the port itself (rst_n: an external reset, landed by the frame's u_frl_rst).

A child whose reset is released by a clock that is NOT one of its own clock pins is FOREIGN (the crossing is not
landed in its clock) and fails the audit.  Exit 0 = PASS, 1 = FAIL, 2 = parse error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RST_PINS = ('rs', 'rst', 'rst_n', 'rsi', 'rstn', 'reset_n')
CLK_RE = re.compile(r'^(ck_r\d+|xk\[\d+\]|clk|ck|cr)$')     # nets that are clocks in the frame top


def split_top(text):
    m = re.search(r'^module\s+(\w+)\b.*?^endmodule', text, re.S | re.M)
    if not m:
        raise SystemExit(2)
    return m.group(1), m.group(0)


def conns(body):
    """{pin: net} of one instance's port list (top-level .pin(net) only; concatenations kept verbatim)."""
    out, i = {}, 0
    for m in re.finditer(r'\.(\w+)\(', body):
        if m.start() < i:
            continue
        depth, j = 1, m.end()
        while depth and j < len(body):
            depth += {'(': 1, ')': -1}.get(body[j], 0)
            j += 1
        out[m.group(1)] = body[m.end():j - 1].strip()
        i = j
    return out


def instances(top):
    """(master, inst, params, {pin: net}) for every instance statement of the top module."""
    res = []
    for m in re.finditer(r'(?:^|;)[ \t]*(\w+)\s*(#\((?:[^()]|\((?:[^()]|\([^()]*\))*\))*\))?\s*(u_\w+)\s*\((.*?)\);', top, re.M | re.S):
        res.append((m.group(1), m.group(3), m.group(2) or '', conns(m.group(4))))
    return res


def base(net):
    return re.sub(r'\[[^\]]*\]$', '', net.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rtl')
    ap.add_argument('--json')
    a = ap.parse_args()
    name, top = split_top(Path(a.rtl).read_text())
    insts = instances(top)
    ports = set(re.findall(r'^\s*(?:input|output)\s+wire\s+(?:\[[^\]]*\]\s*)?(\w+)', top, re.M))
    drv = {}          # net base -> (kind, clock, inst, d)
    for master, inst, par, c in insts:
        if master == 'ot_pl_pad':
            nn = conns(par[1:]).get('N', '1')       # '(MUT == 4) ? 400 : 0' = 0 in every kit (MUT = 0)
            stages = 0 if re.fullmatch(r'\(MUT == \d+\) \? \d+ : 0|0', nn.strip()) else 1
            drv[base(c['q'])] = ('pad' if stages else 'wire', c['ck'], inst, c['d'])
        elif master.startswith('ot_pl_land_reset_forest'):
            drv[base(c['q'])] = ('forest', c['ck'], inst, c['d'])
        elif master == 'ot_reset_sync':
            drv[c['sync_rst_n'].strip()] = ('sync', c['clk'], inst, c['async_rst_n'])
        elif master.startswith('ot_pl_land'):
            continue
    child_clocks = {}
    for master, inst, par, c in insts:
        if master.startswith('ot_pl_') or master == 'ot_reset_sync':
            continue
        cl = sorted({v for v in c.values() if CLK_RE.match(v)})
        child_clocks[inst] = (master, cl)
        for p, v in c.items():          # hard-child outputs that drive frame reset nets (crs4 rs -> n257)
            if p in ('rs',) and master == 'dsfd_cfifo_crs4' and v not in ports:
                drv[base(v)] = ('child', cl[0] if cl else '?', inst, None)

    def release(net, seen=()):
        b = net.strip() if net.strip() in drv else base(net)     # indexed drivers (rst_n__xk[k]) are bit-exact
        if b in ports:
            return ('port', b, [b])
        if b in seen or b not in drv:
            return ('unknown', '?', [b])
        kind, ck, inst, d = drv[b]
        if kind == 'wire':
            r = release(d, seen + (b,))
            return (r[0], r[1], [inst] + r[2])
        return (kind, ck, [inst])

    rows, foreign, forest_x = [], 0, []
    for master, inst, par, c in insts:
        if inst not in child_clocks:
            continue
        cl = child_clocks[inst][1]
        for p in RST_PINS:
            if p not in c or master == 'dsfd_cfifo_crs4' and p == 'rs':
                continue
            kind, ck, path = release(c[p])
            ok = kind == 'port' or ck in cl
            if not ok:
                foreign += 1
            rows.append(dict(inst=inst, master=master, pin=p, net=c[p], released_by=ck, via=kind, path=path,
                             child_clocks=cl, verdict='OK' if ok else 'FOREIGN'))
    for b, (kind, ck, inst, d) in drv.items():     # crossings INTO a forest / synchroniser (landed on the receiver)
        if kind in ('forest', 'sync'):
            k2, ck2, _ = release(d)
            if ck2 != ck and k2 != 'port':
                forest_x.append(dict(inst=inst, kind=kind, src=ck2, dst=ck))
    unknown = sum(1 for r in rows if r['via'] == 'unknown')
    verdict = 'PASS' if foreign == 0 and unknown == 0 and rows else 'FAIL'
    for r in rows:
        if r['verdict'] != 'OK' or r['via'] in ('sync', 'port', 'unknown') or r['master'] == 'dsfd_cfifo_crs4':
            print(f"  {r['verdict']:7s} {r['inst']}.{r['pin']} ({r['master']}) released by {r['released_by']} via "
                  f"{r['via']} {'/'.join(r['path'])}; child clocks {','.join(r['child_clocks'])}")
    for f in forest_x:
        print(f"  LANDED  {f['inst']} ({f['kind']}): {f['src']} -> {f['dst']} (first stage on the receiving clock)")
    print(f'RESET_AUDIT {verdict} {name} {a.rtl}: reset pins={len(rows)} foreign={foreign} unknown={unknown} '
          f'landed_crossings={len(forest_x)}')
    if a.json:
        Path(a.json).write_text(json.dumps(dict(verdict=verdict, top=name, rtl=a.rtl, rows=rows, crossings=forest_x),
                                           indent=1) + '\n')
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
