#!/usr/bin/env python3
"""PLAN-KV 10-23: as-built connectivity of the KV die (rtl6 GEN, source e33504a6f) for die plan v1.

Reads the GEN products of one KV die case (case_kv/die.v, place.tcl, gen_source_ports.json, elements.lef) and writes
a compact logical graph: every content block (non-relay) with its placement, and every logical connection
(src block.port -> dst block.port) after collapsing the die's pass-through masters (relays, shift/landing stations,
reset-region cells).  For each connection it counts the pass-through stages on the as-built path (= today's padded
latency on the die) and the Manhattan length between block centres.

    python3 extract_asbuilt.py --case <case_kv dir> --ports gen_source_ports.json --out asbuilt.json.gz
"""
import argparse
import collections
import gzip
import json
import re
import sys

PASS_RE = re.compile(r'^(qkd_rlys(h0?)?_\d+|qkd_landsh0?_\d+|qkd_astk_rly_296_fl|qkd_rlyi_258s|qkd_rst_region)$')
PASS_IN = ('a', 'y')            # pass-through data inputs -> output 'b' (bitwise)
INST_RE = re.compile(r'^  ([A-Za-z_][A-Za-z0-9_]*) ([A-Za-z_][A-Za-z0-9_]*) \((.*)\);\s*$')
PORT_RE = re.compile(r'\.([A-Za-z_][A-Za-z0-9_]*)\(')
WIRE_RE = re.compile(r'^  wire (\[(\d+):(\d+)\] )?([A-Za-z_][A-Za-z0-9_]*);')
TERM_RE = re.compile(r"\s*(?:(\d+)'[bh]([0-9a-fA-FxXzZ_]+)|([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)(?::(\d+))?\])?)\s*")


def split_ports(body):
    """'.p(expr), .q(expr)' -> [(p, expr)] with balanced braces/parens."""
    out, i, n = [], 0, len(body)
    while i < n:
        m = PORT_RE.search(body, i)
        if not m:
            break
        j, depth = m.end(), 1
        k = j
        while k < n and depth:
            c = body[k]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
            k += 1
        out.append((m.group(1), body[j:k - 1]))
        i = k
    return out


def expr_bits(expr, wires):
    """expr -> list of net bits, MSB first; constants -> None entries."""
    e = expr.strip()
    if not e:
        return []
    if e.startswith('{'):
        e = e[1:-1]
        parts, depth, cur = [], 0, ''
        for c in e:
            if c == ',' and depth == 0:
                parts.append(cur)
                cur = ''
                continue
            depth += c == '{'
            depth -= c == '}'
            cur += c
        parts.append(cur)
        bits = []
        for p in parts:
            bits.extend(expr_bits(p, wires))
        return bits
    m = TERM_RE.fullmatch(e)
    if not m:
        raise ValueError('expr ' + e[:80])
    if m.group(1):
        return [None] * int(m.group(1))
    name = m.group(3)
    if m.group(4) is None:
        hi, lo = wires.get(name, (0, 0))
    else:
        hi = int(m.group(4))
        lo = int(m.group(5)) if m.group(5) is not None else hi
    step = -1 if hi >= lo else 1
    return [(name, b) for b in range(hi, lo + step, step)]


def load_place(path):
    pos = {}
    for ln in open(path):
        if 'ot_mts::place' not in ln:
            continue
        f = ln.replace(']', ' ').split()
        i = f.index('findInst')
        pos[f[i + 1]] = (float(f[i + 2]), float(f[i + 3]), f[i + 4])
    return pos


def load_lef_sizes(path):
    sizes, cur = {}, None
    for ln in open(path):
        if ln.startswith('MACRO '):
            cur = ln.split()[1]
        elif cur and ln.startswith('  SIZE '):
            f = ln.split()
            sizes[cur] = (float(f[1]), float(f[3]))
            cur = None
    return sizes


def ranges(ix):
    out, ix = [], sorted(ix)
    for i in ix:
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', required=True)
    ap.add_argument('--ports', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    ports = json.load(open(a.ports))['masters']
    pos = load_place(a.case + '/place.tcl')
    sizes = load_lef_sizes(a.case + '/elements.lef')
    wires, insts = {}, {}
    drv = {}                                  # (net, bit) -> (inst, port, idx)
    sinks = collections.defaultdict(list)     # (net, bit) -> [(inst, port, idx)]
    for ln in open(a.case + '/die.v'):
        m = WIRE_RE.match(ln)
        if m:
            wires[m.group(4)] = (int(m.group(2)), int(m.group(3))) if m.group(1) else (0, 0)
            continue
        m = INST_RE.match(ln)
        if not m or m.group(1) in ('assign', 'wire', 'module'):
            continue
        mst, name, body = m.groups()
        pdef = ports.get(mst, {}).get('ports')
        if pdef is None:
            print('WARN no ports for', mst, file=sys.stderr)
            continue
        insts[name] = mst
        for p, e in split_ports(body):
            dirs = pdef.get(p)
            if dirs is None:
                continue
            bits = expr_bits(e, wires)
            w = len(dirs)
            # port bit index = w-1 .. 0 (MSB first)
            for k, nb in enumerate(bits):
                if nb is None:
                    continue
                idx = w - 1 - k
                d = dirs[min(max(w - 1 - idx, 0), w - 1)] if w else 'INPUT'
                if d == 'OUTPUT':
                    drv[nb] = (name, p, idx)
                else:
                    sinks[nb].append((name, p, idx))
    print('insts', len(insts), 'driven bits', len(drv), file=sys.stderr)
    # pass-through outputs: (inst, 'b', idx) -> net bit
    out_of = {}
    for nb, (i, p, idx) in drv.items():
        if PASS_RE.match(insts[i]) and p == 'b':
            out_of[(i, idx)] = nb
    edges = collections.defaultdict(lambda: [0, 0, set(), set()])   # (src,sp,dst,dp) -> [bits, max stages, stage insts, src bits]
    for nb, (si, sp, sidx) in drv.items():
        if PASS_RE.match(insts[si]):
            continue
        stack = [(nb, 0, ())]
        seen = set()
        while stack:
            cur, st, path = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            for (di, dp, didx) in sinks.get(cur, ()):
                if PASS_RE.match(insts[di]):
                    if dp in PASS_IN:
                        nxt = out_of.get((di, didx))
                        if nxt is not None:
                            stack.append((nxt, st + 1, path + (di,) if len(path) < 400 else path))
                    continue
                e = edges[(si, sp, di, dp)]
                e[0] += 1
                e[1] = max(e[1], st)
                e[3].add(sidx)
                if len(e[2]) < 2000:
                    e[2].update(path)
    blocks = {}
    for n, mst in insts.items():
        if PASS_RE.match(mst):
            continue
        x, y, o = pos.get(n, (None, None, None))
        w, h = sizes.get(mst, (0, 0))
        blocks[n] = {'m': mst, 'x': x, 'y': y, 'w': w, 'h': h, 'o': o}
    pass_count = collections.Counter(m for m in insts.values() if PASS_RE.match(m))
    out = {'schema': 'opentallas.plan_kv.asbuilt.v1', 'case': a.case,
           'blocks': blocks, 'pass_masters': pass_count,
           'edges': [{'s': s, 'sp': sp, 'd': d, 'dp': dp, 'bits': v[0], 'stages': v[1], 'n_stage_insts': len(v[2]),
            'sbits': ranges(v[3])}
                     for (s, sp, d, dp), v in edges.items()]}
    with gzip.open(a.out, 'wt') as f:
        json.dump(out, f)
    print('blocks', len(blocks), 'edges', len(out['edges']), 'pass', sum(pass_count.values()), file=sys.stderr)


if __name__ == '__main__':
    main()
