#!/usr/bin/env python3
"""S81 static return calendar (S-NET 2026-10-15): the compiler-side model of ot_s81_retn_static.

The return tree of the S81 field no longer arbitrates (owner rule 2026-10-14 18:59: static cycle schedule, no credits /
backpressure / runtime arbitration).  Every node follows the FIXED-SLOT RULE of rtl/dsrom_sys/s81_static_net/
ot_s81_retn_static.sv, and the compiler must know every partial's action and output edge.  This module is that model,
written independently of the RTL structure (pairing by arrival edges, not by window registers):

  * a word arriving at edge n merges with its golden sibling (ot_v41_ret_pkg sibling on the normalised tags) if the
    sibling arrives on the OTHER input at an edge m with |m - n| <= WIN; the sum issues at max(n, m);
  * otherwise it is forwarded;
  * every output word is visible at edge  early + WIN + 10 + RST  (early = arrival edge, the earlier one for a sum);
    10 = 7 (window exit, 5-stage adder, calendar) + 3 fixed pipeline stages of the r2 node (port, norm, issue).

Compiler obligations checked here (the RTL asserts the same, sticky fault, never re-times):
  F1 one exit-slot owner per edge; F2 one sum issue per edge; F3 at most one sibling candidate; F4 implied by F1/F2.

Sub-commands
  vectors  --win W --rst R --seed S --words N [--collide] --out DIR   bench vectors for tb_s81_retn_static (legal
           schedule, or a deliberately colliding one whose expected fault is 1)
  tree     --calendar FILE.json                                   compose a tree calendar: per node arrivals ->
           outputs -> parent arrivals (+ link stages); reports merges/forwards/exit edges and every F1-F3 violation

A tree calendar JSON: {"win": 2, "rst": 1, "nodes": {"<id>": {"a": "<child id or leaf id>", "b": ..., "link_a": 0,
"link_b": 0}}, "leaves": {"<leaf id>": [[edge, tag, data_hex, err], ...]}, "root": "<id>"}.
"""
from __future__ import annotations

import argparse
import json
import random
import struct
import sys
from pathlib import Path

import numpy as np


# ---------------- ot_v41_ret_pkg, bit for bit -----------------------------------------------------------------------
def _f(t):
    return (t >> 13) & 0x7FFFF, (t >> 8) & 31, (t >> 5) & 7, t & 31


def _mk(row19, lo, k, n):
    return (row19 << 13) | (lo << 8) | ((k & 7) << 5) | n


def norm(t: int) -> int:
    row, lo, k, n = _f(t)
    for _ in range(5):
        p2 = (1 << k) & 63                      # 6'd1 << k (6-bit)
        lok = (lo >> k) & 1 if k < 5 else None  # lo[k]: out of range -> x -> condition false
        if lok is None:
            continue
        if not (lo == 0 and p2 >= n) and lok == 0 and (lo + p2) >= n:
            k = (k + 1) & 7
    return _mk(row, lo, k, n)


def complete(t: int) -> bool:
    _, lo, k, n = _f(t)
    return lo == 0 and ((1 << k) & 63) >= n


def sibling(a: int, b: int) -> bool:
    ra, la, ka, na_ = _f(a)
    rb, lb, kb, nb_ = _f(b)
    return ra == rb and ka == kb and na_ == nb_ and (la ^ lb) == ((1 << ka) & 31)


def parent(a: int, b: int) -> int:
    ra, la, ka, na_ = _f(a)
    _, lb, _, _ = _f(b)
    return norm(_mk(ra, min(la, lb), (ka + 1) & 7, na_))


def fadd(x: int, y: int) -> tuple[int, int]:
    """ot_fp32_add_rne_pipe authority on finite operands: IEEE binary32 RNE, every zero result canonical +0."""
    a = np.frombuffer(struct.pack('<I', x), dtype=np.float32)[0]
    b = np.frombuffer(struct.pack('<I', y), dtype=np.float32)[0]
    with np.errstate(all='ignore'):
        s = np.float32(a + b)
    if not np.isfinite(a) or not np.isfinite(b):
        return 0, 1
    if not np.isfinite(s):
        return 0, 1
    r = struct.unpack('<I', s.tobytes())[0]
    if r & 0x7FFFFFFF == 0:
        r = 0
    return r, 0


PIPE_C = 10   # r2 node: 7 + P1 port + P2 norm + P3 issue register (ot_s81_retn_static.sv)


# ---------------- one node --------------------------------------------------------------------------------------------
def node(a_words, b_words, win: int, rst: int):
    """a_words / b_words: lists of (edge, tag, data, err).  Returns (outputs [(edge, tag, data, err, kind)], faults)."""
    exit_c = win + PIPE_C + rst
    A = [(n, norm(t), d, e, 'a', i) for i, (n, t, d, e) in enumerate(a_words)]
    B = [(n, norm(t), d, e, 'b', i) for i, (n, t, d, e) in enumerate(b_words)]
    faults = []
    for side in (A, B):
        edges = [w[0] for w in side]
        if len(set(edges)) != len(edges):
            faults.append(('INPUT', 'two words on one input at one edge'))
    used = set()
    pairs = []
    for wa in A:
        cands = [wb for wb in B if abs(wb[0] - wa[0]) <= win and sibling(wa[1], wb[1])]
        if len(cands) > 1:
            faults.append(('F3', wa[0], hex(wa[1])))
        if cands:
            pairs.append((wa, cands[0]))
    for wb in B:
        if sum(1 for wa in A if abs(wb[0] - wa[0]) <= win and sibling(wa[1], wb[1])) > 1:
            faults.append(('F3', wb[0], hex(wb[1])))
    out = []
    issues = {}
    for wa, wb in pairs:
        used.add(('a', wa[5])); used.add(('b', wb[5]))
        issue = max(wa[0], wb[0])
        issues[issue] = issues.get(issue, 0) + 1
        d, er = fadd(wa[2], wb[2])
        out.append((min(wa[0], wb[0]) + exit_c, parent(wa[1], wb[1]), d, wa[3] | wb[3] | er, 'sum'))
    for e_, c in issues.items():
        if c > 1:
            faults.append(('F2', e_, c))
    for w in A + B:
        if (w[4], w[5]) not in used:
            out.append((w[0] + exit_c, w[1], w[2], w[3], 'fwd'))
    out.sort()
    ex = [o[0] for o in out]
    for e_ in sorted(set(ex)):
        if ex.count(e_) > 1:
            faults.append(('F1', e_, ex.count(e_)))
    return out, faults


# ---------------- tree composition (compiler check) ------------------------------------------------------------------
def tree(cal: dict) -> dict:
    win, rst = cal.get('win', 2), cal.get('rst', 1)
    streams = {k: [tuple(w[:2]) + (int(w[2], 16) if isinstance(w[2], str) else w[2], w[3]) for w in v]
               for k, v in cal['leaves'].items()}
    done, rep = {}, {}
    todo = dict(cal['nodes'])
    while todo:
        for nid, nd in list(todo.items()):
            if nd['a'] in streams and nd['b'] in streams:
                la, lb = nd.get('link_a', 0), nd.get('link_b', 0)
                aw = [(n + la, t, d, e) for n, t, d, e in streams[nd['a']]]
                bw = [(n + lb, t, d, e) for n, t, d, e in streams[nd['b']]]
                out, faults = node(aw, bw, win, rst)
                streams[nid] = [(o[0], o[1], o[2], o[3]) for o in out]
                rep[nid] = dict(merges=sum(o[4] == 'sum' for o in out), forwards=sum(o[4] == 'fwd' for o in out),
                                first_exit=min((o[0] for o in out), default=None),
                                last_exit=max((o[0] for o in out), default=None), faults=faults)
                del todo[nid]
                break
        else:
            raise SystemExit(f'tree: unresolved inputs for {sorted(todo)}')
    root = streams[cal['root']]
    return dict(schema='opentallas.s81.static_return_calendar.tree.v1', win=win, rst=rst,
                verdict='PASS' if not any(r['faults'] for r in rep.values()) else 'FAIL',
                nodes=rep, root_words=len(root), root_complete=sum(complete(t) for _, t, _, _ in root),
                root_last_edge=max((w[0] for w in root), default=None))


# ---------------- bench vectors --------------------------------------------------------------------------------------
def _val(rng):
    # finite normal binary32, never zero (the authority canonicalises -0) and never near overflow
    while True:
        s, e, m = rng.getrandbits(1), rng.randint(100, 150), rng.getrandbits(23)
        return (s << 31) | (e << 23) | m


def vectors(win: int, rst: int, seed: int, words: int, collide: bool, out: Path, leaf_a=False, leaf_b=False):
    rng = random.Random(seed)
    A, B = [], []
    occ = {'a': set(), 'b': set()}
    row = 0
    edge = 4
    kinds = []

    def legal(trialA, trialB):
        _, f = node(trialA, trialB, win, rst)
        return not f

    while len(A) + len(B) < words:
        row += 1
        kind = rng.choice(['pair_same', 'pair_win', 'pair_far', 'single', 'same_side', 'complete', 'pad'])
        nseg = rng.choice([2, 3, 4, 6, 8, 16])
        r19 = (rng.getrandbits(3) << 16) | (row & 0xFFFF)
        for _try in range(40):
            base = edge + rng.randint(0, 3)
            if kind in ('pair_same', 'pair_win', 'pair_far', 'same_side'):
                lo = rng.randrange(0, nseg & ~1, 2) if nseg > 2 else 0
                ta, tb = _mk(r19, lo, 0, nseg), _mk(r19, lo ^ 1, 0, nseg)
                if norm(ta) != ta or norm(tb) != tb:
                    continue
                d = 0 if kind in ('pair_same', 'same_side') else rng.randint(1, win) if kind == 'pair_win' else \
                    rng.randint(win + 1, win + 4)
                d = d if kind != 'same_side' else rng.randint(1, 3)
                sgn = rng.choice([1, -1])
                na_, nb_ = base, base + sgn * d
                if nb_ < 1:
                    continue
                if kind == 'same_side':
                    tA = A + [(na_, ta, _val(rng), 0), (na_ + d, tb, _val(rng), 0)]
                    tB = B
                else:
                    tA = A + [(na_, ta, _val(rng), 0)]
                    tB = B + [(nb_, tb, _val(rng), 0)]
            elif kind == 'complete':
                side = rng.choice('ab')
                leaf = leaf_a if side == 'a' else leaf_b
                t = _mk(r19, 0, 0, 1) if leaf else _mk(r19, 0, 3, rng.randint(1, 8))
                tA = A + [(base, t, _val(rng), 0)] if side == 'a' else A
                tB = B + [(base, t, _val(rng), 0)] if side == 'b' else B
            elif kind == 'pad':      # right sibling wholly in +0 padding: promoted unchanged by norm (k grows)
                t = _mk(r19, 4, 0, 5)
                side = rng.choice('ab')
                tA = A + [(base, t, _val(rng), rng.getrandbits(1))] if side == 'a' else A
                tB = B + [(base, t, _val(rng), 0)] if side == 'b' else B
            else:                    # single: sibling never arrives at this node
                t = _mk(r19, 2, 0 if (leaf_a or leaf_b) else 1, 8)
                side = rng.choice('ab')
                tA = A + [(base, t, _val(rng), 0)] if side == 'a' else A
                tB = B + [(base, t, _val(rng), 0)] if side == 'b' else B
            if legal(tA, tB):
                A, B = tA, tB
                kinds.append(kind)
                break
        edge += rng.randint(1, 3)
    if collide:                       # F1: two unmerged non-sibling words at the same edge
        e_ = max([w[0] for w in A + B]) + 3
        A.append((e_, _mk(0x7FF00 | 1, 2, 0 if leaf_a else 1, 8), _val(rng), 0))
        B.append((e_, _mk(0x7FF00 | 2, 2, 0 if leaf_b else 1, 8), _val(rng), 0))
    outw, faults = node(A, B, win, rst)
    T = max(o[0] for o in outw) + 8
    ai = {w[0]: w for w in A}
    bi = {w[0]: w for w in B}
    oi = {o[0]: o for o in outw}
    dup = {e_ for e_ in oi if sum(1 for o in outw if o[0] == e_) > 1}   # F1 edges: the word left there is not specified
    out.mkdir(parents=True, exist_ok=True)

    def pack(w, leaf):
        # dsfd_node_<a><b> port formats: leaf L = the q lane's 63 b {ppos[62:60], perr[59], pnseg[58:54], pseg[53:49],
        # prow[48:33], pval[32:1], pv[0]} (k = 0); node N = {e[65], data[64:33], tag[32:1], v[0]}
        if w is None:
            return 0
        _, t, d, e = w
        if not leaf:
            return (e << 65) | (d << 33) | (t << 1) | 1
        row19, lo, k, n = _f(t)
        assert k == 0, 'leaf partials are k = 0'
        return ((row19 >> 16) << 60) | (e << 59) | (n << 54) | (lo << 49) | ((row19 & 0xFFFF) << 33) | (d << 1) | 1
    with open(out / 'stim_packed.hex', 'w') as f:
        for n in range(T):
            f.write('%017x %017x\n' % (pack(ai.get(n), leaf_a), pack(bi.get(n), leaf_b)))
    with open(out / 'stim.hex', 'w') as f:
        for n in range(T):
            a = ai.get(n); b = bi.get(n)
            f.write('%d %08x %08x %d %d %08x %08x %d\n' % (
                1 if a else 0, a[1] if a else 0, a[2] if a else 0, a[3] if a else 0,
                1 if b else 0, b[1] if b else 0, b[2] if b else 0, b[3] if b else 0))
    with open(out / 'expect.hex', 'w') as f:
        for n in range(T):
            o = oi.get(n)
            f.write('%d %08x %08x %d\n' % ((2, 0, 0, 0) if n in dup else (1, o[1], o[2], o[3]) if o else (0, 0, 0, 0)))
    meta = dict(win=win, rst=rst, seed=seed, edges=T, words_a=len(A), words_b=len(B), outputs=len(outw),
                merges=sum(o[4] == 'sum' for o in outw), forwards=sum(o[4] == 'fwd' for o in outw),
                kinds={k: kinds.count(k) for k in sorted(set(kinds))}, expect_fault=bool(faults),
                faults=[list(map(str, x)) for x in faults])
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'T').write_text(str(T))
    (out / 'FAULT').write_text('1' if faults else '0')
    print('VECTORS', json.dumps(meta))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    v = sp.add_parser('vectors')
    v.add_argument('--win', type=int, default=2)
    v.add_argument('--rst', type=int, default=1)
    v.add_argument('--seed', type=int, default=1)
    v.add_argument('--words', type=int, default=400)
    v.add_argument('--collide', action='store_true')
    v.add_argument('--leaf-a', action='store_true', help='input a is a leaf (q lane 63-b format, k = 0)')
    v.add_argument('--leaf-b', action='store_true')
    v.add_argument('--out', type=Path, required=True)
    t = sp.add_parser('tree')
    t.add_argument('--calendar', type=Path, required=True)
    t.add_argument('--out', type=Path)
    a = ap.parse_args()
    if a.cmd == 'vectors':
        vectors(a.win, a.rst, a.seed, a.words, a.collide, a.out, a.leaf_a, a.leaf_b)
        return 0
    r = tree(json.loads(a.calendar.read_text()))
    s = json.dumps(r, indent=1)
    if a.out:
        a.out.write_text(s + '\n')
    print('STATIC_RETURN_CALENDAR', r['verdict'], 'root_words', r['root_words'], 'root_last_edge', r['root_last_edge'])
    return 0 if r['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
