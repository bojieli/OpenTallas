#!/usr/bin/env python3
"""S81 hierarchical die (H-C27 c27, S-DIE cluster plan v0 2026-10-16): column / hub cluster extraction.

The owner directed S81 to go hierarchical (flat die GRT does not finish): the ROM-column field becomes replicated column
clusters built ONCE per height class, the hub becomes its own clusters, and the die top routes only inter-cluster
forwarded-clock relay chains.

    cluster_extract.py stagemap  --canonical-layout L --out J      phase-fixed stage map (compiler input; BF ids remapped)
    cluster_extract.py analyze   --plan P [--die-v V] --out J      column signatures + isomorphism report of a GEN plan
    cluster_extract.py extract   --plan P --die-v V --glue G --out D   column (+ hub) cluster masters: Verilog wrapper,
                                                                   placement, ports, clock/reset entries, ref_tile spec

BF phase (--bf-phase-fixed in tools/dsrom_s81_fulldie.py): the allocator keeps every root's pair range and BF count
(stage_map region_bounds and per-root BF count unchanged), but the BF pairs inside a root follow ONE pattern per
(pairs, BF) class, so all frames of a class pack to the same element order.  Before: 32 frame signatures, only because
floor(i * 1973 / 424) rotates the in-root BF phase.

Column cluster = one field frame (region frame_<r>) + its column FIFO cf<r> (already a member of the frame region).
Every frame boundary net of the c26 plan goes through cf<r> (xd/xf, xd2/xf2 forwarded entries, rd/rf forwarded return,
ck = clk_stream, rst = rst_stream), so the cluster boundary is registered by construction:
  * xd / xd2 are captured at the pin by ot_s81_static_column_ingress on the forwarded clock xf / xf2;
  * rd is the rr register on the column clock, launched with rf = the column clock (F1 forwarded return);
  * ck enters ONE regional tree (cf.co -> ck_col net -> every column leaf), rst is synchronised in cf (rsync -> rs_col).
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'opentallas.s81.cluster_extract.v1'


# ------------------------------------------------------------------------------------------------ BF phase
def bf_phase_pattern(n: int, nbf: int) -> list:
    """in-root BF positions for a root of n pairs with nbf BF pairs: centred even spread floor((2j+1) n / (2 nbf))."""
    assert 0 <= nbf <= n
    pos = [((2 * j + 1) * n) // (2 * nbf) for j in range(nbf)]
    assert len(set(pos)) == nbf and all(0 <= p < n for p in pos), (n, nbf, pos)
    return pos


def bf_phase_fixed_ids(canonical: dict):
    """(new BF id list, receipt) for a loaded canonical layout (s81.canonical_layout.load): per root same pair range and
    BF count, BF positions from bf_phase_pattern(pairs, bf)."""
    old = set(canonical['bf_ids'])
    new, classes, moved = [], collections.Counter(), []
    for f in sorted(canonical['placements'], key=lambda f: f['root']):
        lo, hi = f['pairs']
        n = hi - lo
        nbf = sum(1 for p in range(lo, hi) if p in old)
        assert nbf == f['bf'], (f['root'], nbf, f['bf'])
        pos = bf_phase_pattern(n, nbf)
        ids = [lo + p for p in pos]
        new += ids
        classes[(n, nbf, tuple(pos), f['height_um'])] += 1
        was = sorted(p - lo for p in range(lo, hi) if p in old)
        if was != pos:
            moved.append(dict(root=f['root'], was=was, now=pos))
    assert len(new) == len(old) == canonical['bf_pairs']
    receipt = dict(rule='per root: same pair range and BF count; BF in-root positions floor((2j+1) n / (2 nbf))',
                   bf_pairs=len(new), roots_changed=len(moved),
                   classes=[dict(pairs=k[0], bf=k[1], positions=list(k[2]), height_um=k[3], roots=v)
                            for k, v in sorted(classes.items())],
                   sha256_ids=hashlib.sha256(json.dumps(sorted(new)).encode()).hexdigest(), moved_ids=moved)
    return sorted(new), receipt


def cmd_stagemap(a):
    sys.path.insert(0, str(ROOT / 'tools'))
    from s81.canonical_layout import load
    d = load(a.canonical_layout, ROOT)
    ids, rec = bf_phase_fixed_ids(d)
    sp = ROOT / d['stage_map']
    sm = json.loads(sp.read_text())
    bounds = sm['region_bounds']
    for r in range(len(bounds) - 1):
        n_old = sum(1 for p in sm['BF_site_IDs'] if bounds[r] <= p < bounds[r + 1])
        n_new = sum(1 for p in ids if bounds[r] <= p < bounds[r + 1])
        assert n_old == n_new, ('per-region BF count changed', r, n_old, n_new)
    sm['BF_site_IDs'] = ids
    sm['bf_phase_fixed'] = dict(source_stage_map=str(sp.relative_to(ROOT)),
                                source_sha256=hashlib.sha256(sp.read_bytes()).hexdigest(),
                                canonical_layout=str(Path(d['path']).resolve().relative_to(ROOT)),
                                **{k: v for k, v in rec.items()})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(sm, indent=1) + '\n')
    print('STAGEMAP', a.out, 'roots_changed', rec['roots_changed'], 'classes',
          [(c['pairs'], c['bf'], c['positions'], c['height_um'], c['roots']) for c in rec['classes']])


# ------------------------------------------------------------------------------------------------ plan helpers
def load_plan(path):
    p = Path(path)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_text())


def frame_members(plan):
    """root -> [inst rows] of region frame_<root> (cf<root> is one of them)."""
    by = collections.defaultdict(list)
    for i in plan['insts']:
        if i[8].startswith('frame_'):
            by[int(i[8][6:])].append(i)
    for r, L in by.items():
        assert any(i[0] == f'cf{r}' for i in L), ('column FIFO not in its frame region', r)
    return dict(by)


def frame_class(f):
    """height class name of a frame record."""
    h = round(f['h'], 2)
    return {2695.68: 'h9', 2985.12: 'h10a', 3000.24: 'h10b'}.get(h, f'h{h:.2f}')


def cluster_origin(f, members):
    """cluster outline origin: frame x, and the lowest member y (the column FIFO in the street below the frame)."""
    return f['x'], min(i[3] for i in members)


def signature(plan, r, members, eps=0.002):
    """(class, element order, sorted relative geometry) of frame r; E frames are compared un-mirrored (the generator
    builds both halves R0 at the same in-frame offsets)."""
    f = plan['frames'][str(r)]
    ox, oy = cluster_origin(f, members)
    geo = tuple(sorted((i[1], round(i[2] - ox, 2), round(i[3] - oy, 2), round(i[4], 2), round(i[5], 2), i[6])
                       for i in members))
    order = tuple((e[1], e[2], e[3]) for e in f['elems'])
    return (frame_class(f), len(f['elems']), order), geo


# ------------------------------------------------------------------------------------------------ die.v parsing
_INST = re.compile(r'^\s*([A-Za-z_][\w$]*)\s+(\\?\S+)\s*\((.*)\);\s*$')
_PIN = re.compile(r'\.(\w+)\(')


def _split_top(s, sep=','):
    out, depth, cur = [], 0, []
    for ch in s:
        if ch in '({[':
            depth += 1
        elif ch in ')}]':
            depth -= 1
        if ch == sep and depth == 0:
            out.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        out.append(''.join(cur))
    return [x.strip() for x in out]


def parse_pins(body):
    """'.a(x), .b({y[1], y[0]})' -> {pin: expr}"""
    pins = {}
    for part in _split_top(body):
        if not part:
            continue
        m_ = re.match(r'\.(\w+)\((.*)\)$', part, re.S)
        assert m_, part[:200]
        pins[m_.group(1)] = m_.group(2).strip()
    return pins


def expr_bits(expr, widths):
    """expression -> list of bit refs MSB first: ('net', i) / ('const', '0'|'1') / None for empty."""
    expr = expr.strip()
    if not expr:
        return []
    if expr.startswith('{'):
        assert expr.endswith('}'), expr[:80]
        out = []
        for part in _split_top(expr[1:-1]):
            out += expr_bits(part, widths)
        return out
    m_ = re.fullmatch(r"(\d+)'([bdh])([0-9a-fA-FxXzZ_]+)", expr)
    if m_:
        n, base, v = int(m_.group(1)), m_.group(2), m_.group(3).replace('_', '')
        val = int(v, {'b': 2, 'd': 10, 'h': 16}[base])
        return [('const', str((val >> k) & 1)) for k in range(n - 1, -1, -1)]
    m_ = re.fullmatch(r'(\\?[\w$]+)\s*\[(\d+)(?::(\d+))?\]', expr)
    if m_:
        net, hi = m_.group(1), int(m_.group(2))
        lo = int(m_.group(3)) if m_.group(3) is not None else hi
        step = -1 if hi >= lo else 1
        return [(net, k) for k in range(hi, lo + step, step)]
    m_ = re.fullmatch(r'\\?[\w$]+', expr)
    assert m_, ('unsupported die.v expression', expr[:120])
    w = widths.get(expr, 1)
    return [(expr, k) for k in range(w - 1, -1, -1)]


def parse_die_v(path, want=None):
    """structural die.v -> (module header text, port decls, wire widths, instances {name: (master, {pin: expr})}).
    want: optional set of instance names to keep (all others skipped cheaply)."""
    widths, ports, insts, order = {}, [], {}, []
    head = None
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt') as fh:
        for line in fh:
            s = line.strip()
            if s.startswith('module '):
                head = s
                continue
            m_ = re.match(r'(input|output|inout|wire)\s+(?:\[(\d+):(\d+)\]\s+)?(\\?[\w$]+)\s*;', s)
            if m_:
                w = abs(int(m_.group(2)) - int(m_.group(3))) + 1 if m_.group(2) is not None else 1
                widths[m_.group(4)] = w
                if m_.group(1) != 'wire':
                    ports.append((m_.group(1), m_.group(4), w))
                continue
            m_ = _INST.match(line)
            if m_ and m_.group(1) not in ('module', 'endmodule', 'input', 'output', 'wire', 'assign'):
                name = m_.group(2)
                if want is not None and name not in want:
                    continue
                insts[name] = (m_.group(1), parse_pins(m_.group(3)))
                order.append(name)
    return dict(head=head, ports=ports, widths=widths, insts=insts, order=order)


def bit_partition(dv, names):
    """for the instances `names`: {(net, bit): [(inst, pin, k)]} with k the bit index (LSB 0) inside the pin."""
    use = collections.defaultdict(list)
    for n in names:
        master, pins = dv['insts'][n]
        for pin, ex in pins.items():
            bits = expr_bits(ex, dv['widths'])
            L = len(bits)
            for j, b in enumerate(bits):
                if b[0] == 'const':
                    continue
                use[b].append((n, pin, L - 1 - j))
    return use


# ------------------------------------------------------------------------------------------------ analyze
def analyze(plan, dv=None, all_users=None):
    """frame signatures per class; with dv, the bit-level connectivity of every frame is checked isomorphic to its
    class representative under the geometric instance map (same master, same relative box)."""
    fm = frame_members(plan)
    sigs = collections.defaultdict(list)
    for r in sorted(fm):
        key, geo = signature(plan, r, fm[r])
        sigs[(key, geo)].append(r)
    by_class = collections.defaultdict(list)
    for (key, geo), roots in sigs.items():
        by_class[key[0]].append(dict(key=key, roots=roots, n_inst=len(geo)))
    rep = dict(schema=SCHEMA, frames=len(fm), signatures=len(sigs),
               classes={c: dict(signatures=len(v), roots=sum(len(x['roots']) for x in v),
                                members=sorted({x['n_inst'] for x in v}),
                                variants=[dict(pairs=x['key'][1], roots=x['roots'], n_inst=x['n_inst'],
                                               bf_slots=[o[1] for o in x['key'][2] if o[0] == 'BF']) for x in v])
                        for c, v in sorted(by_class.items())})
    if dv is not None:
        rep['isomorphism'] = isomorphism(plan, dv, fm, sigs, all_users)
    return rep, sigs, fm


def inst_map(plan, members_a, members_b, ra, rb):
    fa, fb = plan['frames'][str(ra)], plan['frames'][str(rb)]
    oa, ob = cluster_origin(fa, members_a), cluster_origin(fb, members_b)
    ka = {(i[1], round(i[2] - oa[0], 2), round(i[3] - oa[1], 2)): i[0] for i in members_a}
    mp = {}
    for i in members_b:
        k = (i[1], round(i[2] - ob[0], 2), round(i[3] - ob[1], 2))
        assert k in ka, ('no geometric partner', rb, i[0], k)
        mp[i[0]] = ka[k]
    return mp


def boundary_and_internal(dv, names, all_users):
    """bits used by `names`: internal = every user of the bit is in names; boundary otherwise."""
    S = set(names)
    use = bit_partition(dv, names)
    internal, boundary = {}, {}
    for b, users in use.items():
        if all_users is not None and any(u not in S for u in all_users.get(b, ())):
            boundary[b] = users
        else:
            internal[b] = users
    return internal, boundary


def canon_partition(part, rename=None):
    """frozen set of frozensets of (inst, pin, k): the net partition independent of net names."""
    out = set()
    for users in part.values():
        out.add(frozenset((rename.get(u[0], u[0]) if rename else u[0], u[1], u[2]) for u in users))
    return out


def all_bit_users(dv):
    """(net, bit) -> set of instance names (for the boundary test); top ports count as user 'TOP'."""
    users = collections.defaultdict(set)
    for n, (master, pins) in dv['insts'].items():
        for pin, ex in pins.items():
            for b in expr_bits(ex, dv['widths']):
                if b[0] != 'const':
                    users[b].add(n)
    for d, p, w in dv['ports']:
        for k in range(w):
            users[(p, k)].add('TOP')
    return users


def isomorphism(plan, dv, fm, sigs, all_users):
    res = {}
    for (key, geo), roots in sigs.items():
        rep = roots[0]
        names_r = [i[0] for i in fm[rep]]
        ir, br = boundary_and_internal(dv, names_r, all_users)
        ref_int, ref_bnd = canon_partition(ir), canon_partition(br)
        bad = []
        for r in roots[1:]:
            mp = inst_map(plan, fm[rep], fm[r], rep, r)
            names = [i[0] for i in fm[r]]
            i2, b2 = boundary_and_internal(dv, names, all_users)
            if canon_partition(i2, mp) != ref_int or canon_partition(b2, mp) != ref_bnd:
                bad.append(r)
        res[f'{key[0]}:{key[1]}:{rep}'] = dict(rep=rep, roots=roots, internal_nets=len(ref_int),
                                               boundary_bits=sum(len(x) for x in br.values()) and len(br),
                                               non_isomorphic=bad)
    return res


def cmd_analyze(a):
    plan = load_plan(a.plan)
    dv = users = None
    if a.die_v:
        dv = parse_die_v(a.die_v)
        users = all_bit_users(dv)
    rep, _, _ = analyze(plan, dv, users)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    print('ANALYZE frames', rep['frames'], 'signatures', rep['signatures'],
          {c: (v['signatures'], v['roots']) for c, v in rep['classes'].items()})
    if 'isomorphism' in rep:
        print('ISO', {k: (len(v['roots']), len(v['non_isomorphic'])) for k, v in rep['isomorphism'].items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('stagemap')
    s.add_argument('--canonical-layout', required=True)
    s.add_argument('--out', required=True)
    s = sub.add_parser('analyze')
    s.add_argument('--plan', required=True)
    s.add_argument('--die-v')
    s.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    {'stagemap': cmd_stagemap, 'analyze': cmd_analyze}[a.cmd](a)


if __name__ == '__main__':
    main()
