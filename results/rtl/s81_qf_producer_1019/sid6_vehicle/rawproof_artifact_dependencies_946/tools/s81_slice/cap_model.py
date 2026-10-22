#!/usr/bin/env python3
"""S81-SLICE capture root (ot_s81sl_cap) -- compiler model, return-slot legaliser and bench vectors (2026-10-17).

The model reproduces rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv edge for edge:
  * lane word = the frame column-return root word {e, d32, t32, v} delivered on the cfifo rd; ARR = the edge the cap
    samples rd (its pin flop);
  * TREE: 7 x ot_s81_retn_static (fixed-slot rule, as tools/s81/static_return_calendar.py node()): a lane word arrives
    at its level-1 node at ARR + 1; every node output is visible at early + WIN + 10 + RST and is the parent's arrival;
  * FIN: F1 edge X = the root node's output edge.  A complete word is written at X + 4 (port pipe A); a non-complete
    word inserts into / merges at the direct-mapped pairing store {slot = (row + 8 pos) mod 64, h = parent node}; a
    merge re-enters F1 at X + RE (pipe B) with sum = fadd(stored, new), tag = norm(pre-parent);
  * DEC: e = row - rbase, chunk = e >> 6, leaf = chunk % 5, word = obase + pos * ops + 64 (chunk // 5) + e % 64,
    port = word bit 2, FP32 or BF16 RNE.
Expected VALUES do not come from this path model: they are the GOLDEN tree sums of each row's segments (ot_v41_ret_pkg
order, padding promoted), computed independently (golden_row); the model's own sums are asserted equal to them.

The legaliser is the compiler's return-slot assignment: lane words get globally distinct ARR edges (the tree root
carries one word an edge), in lane order (the cfifo is in order), no earlier than the frame produces them, and are
pushed later until the model shows no obligation violated (F5 two non-complete words at F1, F8 two writes to one leaf
port, F6 slot conflict, tree F1-F4).

  cap_model.py gen --case real|random --seed S --out DIR [--rows N] [--phases P]
writes DIR/stim.hex (per edge: cfg_v, cfg_d, 8 lane column-root words, as the bench drives the column root node),
DIR/expect.txt (W edge leaf port addr data; L row pos last_arr write_edge), DIR/meta.json.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 's81'))
from static_return_calendar import norm, complete, sibling, fadd, _mk, _f  # noqa: E402

WIN, RST = 2, 1
C_NODE = WIN + 10 + RST          # ot_s81_retn_static exit constant
RE = 10                          # F1 merge decision -> re-entry F1 edge (calibrated against the RTL: bench exact edges)
WR = 4                           # F1 edge -> cw output flop edge
LL = 16                          # bench: column-root node input edge -> cap rd sample edge (node 13 + rstg 1 + cfifo 2)


# ------------------------------------------------------------------ golden
def tree_nodes(a, b, n):
    """maximal golden tree nodes (lo, k) covering [a, b) of an n-leaf row (the frame's own tree), normalised"""
    out = []
    lo = a
    while lo < b:
        k = 0
        while k < 5 and lo % (1 << (k + 1)) == 0 and min(lo + (1 << (k + 1)), n) <= b:
            k += 1
        out.append(norm(_mk(0, lo, k, n)) & 0x1FFF)        # lo/k/n only (the frame tree's normalised node)
        lo += 1 << k
    return out


def golden_node(vals, lo, k, n):
    """golden value of tree node (lo, k): left + right, a child wholly in padding is absent (promotion)"""
    if k == 0:
        return vals[lo], 0
    h = 1 << (k - 1)
    l, el = golden_node(vals, lo, k - 1, n)
    if lo + h >= n:
        return l, el
    r, er = golden_node(vals, lo + h, k - 1, n)
    s, e = fadd(l, r)
    return s, el | er | e


def golden_row(vals):
    n = len(vals)
    k = max(0, (n - 1).bit_length())
    return golden_node(vals, 0, k, n)


def golden_sub(vals, t):
    _, lo, k, n = _f(t)
    return golden_node(vals, lo, k, n)


# ------------------------------------------------------------------ model
def h_of(t):
    _, lo, k, _ = _f(t)
    return (1 << (4 - k)) | (lo >> (k + 1))


def node_model(A, B):
    """A/B: {edge: (tag, data, err, src)} -> ({edge: word}, faults); fixed-slot rule"""
    faults = []
    An = {e: (norm(w[0]),) + w[1:] for e, w in A.items()}
    Bn = {e: (norm(w[0]),) + w[1:] for e, w in B.items()}
    usedB = set()
    out = []
    pairedA = set()
    for ea, wa in sorted(An.items()):
        c = [eb for eb in range(ea - WIN, ea + WIN + 1) if eb in Bn and sibling(wa[0], Bn[eb][0])]
        if len(c) > 1:
            faults.append(('F3', ea))
        if c:
            eb = c[0]
            wb = Bn[eb]
            usedB.add(eb)
            pairedA.add(ea)
            s, er = fadd(wa[1], wb[1])
            _, lo_a, ka, n = _f(wa[0])
            _, lo_b, _, _ = _f(wb[0])
            row = wa[0] >> 13
            pt = norm(_mk(row, min(lo_a, lo_b), (ka + 1) & 7, n))
            out.append((min(ea, eb) + C_NODE, pt, s, wa[2] | wb[2] | er, wa[3] + wb[3], max(ea, eb)))
    for ea, wa in An.items():
        if ea not in pairedA:
            out.append((ea + C_NODE, wa[0], wa[1], wa[2], wa[3], None))
    for eb, wb in Bn.items():
        if eb not in usedB:
            out.append((eb + C_NODE, wb[0], wb[1], wb[2], wb[3], None))
    issues = [o[5] for o in out if o[5] is not None]
    for e in set(issues):
        if issues.count(e) > 1:
            faults.append(('F2', e))
    res = {}
    for o in out:
        if o[0] in res:
            faults.append(('F1', o[0], o[4]))
        res[o[0]] = (o[1], o[2], o[3], o[4])
    return res, faults


def decode(t, d, cfg):
    pos, row = t >> 29, (t >> 13) & 0xFFFF
    e = (row - cfg['rbase']) & 0xFFFF
    bad = e >= cfg['rcnt'] or pos > cfg['np'] or cfg['fmt'] == 3
    ch = (e >> 6) & 15
    leaf = 0 if ch >= 15 else ch % 5
    wrap = 3 if ch >= 15 else ch // 5
    addr = (cfg['obase'] + pos * cfg['ops'] + 64 * wrap + (e & 63)) & 0xFFF
    fp32 = cfg['fmt'] == 1 or (cfg['fmt'] == 0 and (cfg['lo32'] if row < cfg['rsplit'] else cfg['hi32']))
    if not fp32:
        d = ((((d + 0x7FFF + ((d >> 16) & 1)) & 0x1FFFFFFFF) >> 16) & 0xFFFF) << 16
    return bad, leaf, (addr >> 2) & 1, addr, d


def model(lanes, cfgs):
    """lanes: list of 8 dicts {arr_edge: (tag, data, err, [src ids])}; cfgs: [(edge_at_pin, cfg)] (cfg pin edge).
    Returns dict(writes=[(edge, leaf, port, addr, data, row, pos, srcs)], faults=[...])"""
    faults = []
    L1 = [{e + 1: w for e, w in lanes[l].items()} for l in range(8)]
    lvl = []
    for i in range(4):
        o, f = node_model(L1[2 * i], L1[2 * i + 1]); faults += [('n%d' % i,) + x for x in f]; lvl.append(o)
    o4, f = node_model(lvl[0], lvl[1]); faults += [('n4',) + x for x in f]
    o5, f = node_model(lvl[2], lvl[3]); faults += [('n5',) + x for x in f]
    o6, f = node_model(o4, o5); faults += [('n6',) + x for x in f]
    # cfg: pin edge c -> cfgv_q visible after c -> config registers updated at c + 1, used by D1 words at D2 edge
    cfg_at = sorted(cfgs)
    store = {}         # slot -> dict(key, n=count, e={h: (side, data, srcs)})
    reent = {}
    writes = []
    edges = sorted(set(o6) | set(reent))
    t_end = max(edges, default=0) + 200
    X = min(edges, default=0)
    pend = dict(o6)

    def cfg_for(edge2):   # config in force at D2 edge (X + 2)
        c = None
        for ce, cf in cfg_at:
            if ce + 1 < edge2:   # applied at ce + 1 (register), seen from the next cycle
                c = cf
        return c
    while X <= t_end:
        a = pend.get(X)
        b = reent.get(X)
        # F11: cfg at pin edge ce is checked when cfgv_q is visible (cycle after ce) against open slots
        for ce, _ in cfg_at:
            if ce == X and any(s['n'] for s in store.values()):
                faults.append(('F11', X))
        comp = []
        sw = []
        for p, w in ((0, a), (1, b)):
            if w is None:
                continue
            if w[2]:
                faults.append(('F10', X))
            if complete(w[0]):
                comp.append((p, w))
            else:
                sw.append(w)
        if len(sw) > 1:
            faults.append(('F5', X, a[3], b[3]))
        if sw:
            w = sw[1] if len(sw) > 1 else sw[0]
            fromb = w is b
            t = w[0]
            pos, row, lo, k, n = t >> 29, (t >> 13) & 0xFFFF, (t >> 8) & 31, (t >> 5) & 7, t & 31
            key = (pos, row, n)
            slot = (row + 8 * pos) & 63
            if k > 4 or lo & ((1 << k) - 1):
                faults.append(('F7', X))
            else:
                h = h_of(t)
                side = (lo >> k) & 1
                s = store.get(slot)
                if s and s['n'] and s['key'] != key:
                    faults.append(('F6', X, w[3]))
                elif s and s['n'] and h in s['e']:
                    sd, dd, ss = s['e'][h]
                    if sd == side:
                        faults.append(('F7', X))
                    else:
                        del s['e'][h]                 # the slot stays held by the parent in flight
                        if fromb:
                            s['n'] -= 1
                        sm, er = fadd(dd, w[1])
                        pt = norm(_mk((t >> 13), lo & ~(1 << k), k + 1, n))
                        reent[X + RE] = (pt, sm, er, ss + w[3])
                        t_end = max(t_end, X + RE + 50)
                else:
                    if not (s and s['n']):
                        s = store[slot] = dict(key=key, n=0, e={})
                    s['e'][h] = (side, w[1], w[3])
                    if not fromb:
                        s['n'] += 1
        for p, w in comp:
            if p == 1:                               # a complete re-entry releases its slot
                t = w[0]
                store[((t >> 13) + 8 * (t >> 29)) & 63]['n'] -= 1
            cf = cfg_for(X + 2)
            bad, leaf, port, addr, d = decode(w[0], w[1], cf)
            if bad:
                faults.append(('F9', X))
                continue
            writes.append((X + WR, leaf, port, addr, d, (w[0] >> 13) & 0xFFFF, w[0] >> 29, w[3], p))
        if len(comp) == 2:
            ww = [x for x in writes[-2:]]
            if len(ww) == 2 and ww[0][0] == ww[1][0] and ww[0][1] == ww[1][1] and ww[0][2] == ww[1][2]:
                faults.append(('F8', X, ww[0][7], ww[1][7]))
        X += 1
    if any(s['n'] for s in store.values()):
        faults.append(('OPEN_AT_END',))
    return dict(writes=writes, faults=faults)


# ------------------------------------------------------------------ workloads
def fval(rng, scale=None):
    while True:
        if scale is None:
            s, e, m = rng.getrandbits(1), rng.randint(110, 140), rng.getrandbits(23)
            return (s << 31) | (e << 23) | m
        import struct
        x = rng.gauss(0.0, scale)
        r = struct.unpack('<I', struct.pack('<f', x))[0]
        if r & 0x7FFFFFFF:
            return r


def make_phase(rng, case, slice_id, rows, np_, nseg_choices, ph):
    """one field phase: rows of this slice, their segments split over the 8 frames.  Returns (cfg, rows, words)
    words: (natural_arr_edge, lane, tag, data, src_id)"""
    rbase = 320 * slice_id if case == 'real' else rng.randint(0, 60000)
    rcnt = rows
    cfg = dict(obase=rng.randrange(0, 1024, 4) if case == 'random' else 1024 * (ph % 3), ops=rows + (0 if case == 'real' else rng.randint(0, 64)),
               np=np_, fmt=rng.choice([0, 1, 2]) if case == 'random' else (2 if ph % 2 else 1),
               rbase=rbase, rcnt=rcnt, rsplit=rbase + rng.randint(0, rows), lo32=rng.getrandbits(1), hi32=rng.getrandbits(1))
    # ensure distinct addresses: positions do not overlap in the leaf address space
    if cfg['ops'] < 64 * math.ceil(math.ceil(rows / 64) / 5):
        cfg['ops'] = 64 * math.ceil(math.ceil(rows / 64) / 5)
    nseg = rng.choice(nseg_choices)
    K = nseg * 256
    dist = [8, 2, 0, 3, 8, 2, 0, 3]                       # frame -> slice stages (p4 plan r_f_*: s = 8, 2, 0, 3 ...)
    rowsd = {}
    words = []
    sid = 0
    for pos in range(np_ + 1):
        for e in range(rows):
            row = rbase + e
            n = nseg if case == 'real' else rng.randint(1, 31)
            vals = [fval(rng, None if case == 'random' else 1.0 / math.sqrt(n)) for _ in range(n)]
            rowsd[(row, pos)] = vals
            # contiguous runs over consecutive frames (the compiler keeps a row's segments in the slice's frames)
            nr = min(n, rng.choice([1, 2, 2, 3, 3, 4]))
            cuts = sorted(rng.sample(range(1, n), nr - 1)) if nr > 1 else []
            bounds = [0] + cuts + [n]
            f0 = (e + pos) % 8 if case == 'real' else rng.randrange(8)
            for r in range(nr):
                lane = (f0 + r) % 8 if case == 'real' else rng.randrange(8)
                a, b = bounds[r], bounds[r + 1]
                for t13 in tree_nodes(a, b, n):
                    _, lo, k, _ = _f(t13)
                    tag = (pos << 29) | ((row & 0xFFFF) << 13) | (t13 & 0x1FFF)
                    end_seg = min(lo + (1 << k), n)
                    # frame partial ready: x streamed at 64 elements a cycle, + element latency, + frame tree, + stages
                    nat = math.ceil(end_seg * K / n / 64) + 31 + 13 * 3 + dist[lane] + (e // 32) + 4 * pos
                    if case == 'random':
                        nat = 2 * e + rng.randint(0, 40) + 8 * pos
                    words.append([nat, lane, tag, None, sid])
                    sid += 1
    for w in words:
        t = w[2]
        vals = rowsd[(((t >> 13) & 0xFFFF), t >> 29)]
        d, _ = golden_sub(vals, t)
        w[3] = d
    return cfg, rowsd, words


D_TREE = 1 + 3 * C_NODE          # lane word ARR -> F1 edge (unmerged, or a tree pair from the earlier word's ARR)


def legalise(words, t0, cfg):
    """causal return-slot assignment in F1 time.  Slot X takes at most one lane word (ARR = X - D_TREE), chosen oldest
    first among the frame-ready words such that the finish obligations hold (F5: a non-complete re-entry leaves A only
    to a complete word; F8: two complete words not on one leaf port; F6: the store slot is free or the row's own).
    A non-complete word whose golden sibling is ready on another lane is placed as a TREE PAIR (ARR X - D and X + 1 - D):
    the two meet in the static tree (WIN 2) and F1 slot X sees their parent; slot X + 1 stays empty.
    Returns ({word id: ARR}, slots used).  The full model then re-checks the result edge for edge."""
    pend = sorted(words, key=lambda w: (w[0], w[4]))
    left = {w[4]: w for w in words}
    arr = {}
    store, reent, blocked, slottags = {}, {}, set(), {}
    bytag = {norm(w[2]): w for w in words}
    def sib_tag(t):
        r19, lo, k, n = _f(t)
        return _mk(r19, lo ^ (1 << k), k, n) if k < 5 else -1
    X = t0 + D_TREE
    def leafport(t, d):
        bad, leaf, port, addr, dd = decode(t, d, cfg)
        assert not bad
        return leaf, port
    def store_ok(t):
        pos, row, n = t >> 29, (t >> 13) & 0xFFFF, t & 31
        s = store.get((row + 8 * pos) & 63)
        return not (s and s['n'] and s['key'] != (pos, row, n))
    def f1_word(t, d, fromb):
        pos, row, lo, k, n = t >> 29, (t >> 13) & 0xFFFF, (t >> 8) & 31, (t >> 5) & 7, t & 31
        slot = (row + 8 * pos) & 63
        h = h_of(t); side = (lo >> k) & 1
        s = store.get(slot)
        if s and s['n'] and h in s['e']:
            assert s['key'] == (pos, row, n)
            sd, dd = s['e'].pop(h)
            assert sd != side
            if fromb:
                s['n'] -= 1
            sm, er = fadd(dd, d)
            reent[X + RE] = (norm(_mk(t >> 13, lo & ~(1 << k), k + 1, n)), sm)
        else:
            if not (s and s['n']):
                s = store[slot] = dict(key=(pos, row, n), n=0, e={})
            s['e'][h] = (side, d)
            if not fromb:
                s['n'] += 1
    guard = 0
    while left or reent or any(s['n'] for s in store.values()):
        guard += 1
        if guard > 20000 + 40 * len(words):
            opn = {k_: (v_['key'], v_['n'], sorted(v_['e'])) for k_, v_ in store.items() if v_['n']}
            raise SystemExit(f'legalise: no progress at X={X}: {len(left)} words left, reent {sorted(reent)}, open {opn}, '
                             f'next {[ (hex(norm(w[2])), w[1]) for w in pend if w[4] in left][:6]}')
        b = reent.pop(X, None)
        b_nc = b is not None and not complete(b[0])
        b_lp = leafport(*b) if b is not None and not b_nc else None
        choice = None
        if X not in blocked:
            pend = [w for w in pend if w[4] in left]
            near = [u for y in range(X - WIN, X + WIN + 2) for u in slottags.get(y, ())]
            for w in pend:
                if w[0] + t0 + D_TREE > X:
                    break
                t, d = norm(w[2]), w[3]
                pair = None
                if not complete(t) and (X + 1) not in blocked:
                    v = bytag.get(sib_tag(t))
                    if v is not None and v[4] in left and v[1] != w[1] and v[0] + t0 + D_TREE <= X + 1:
                        pair = v
                if any(sibling(t, u) for u in near) or (pair is not None and any(sibling(norm(pair[2]), u) for u in near)):
                    continue                          # would meet a placed word in the tree within WIN: not this slot
                if pair is not None:
                    _, lo_a, ka, n = _f(t); _, lo_b, _, _ = _f(norm(pair[2]))
                    t = norm(_mk(t >> 13, min(lo_a, lo_b), ka + 1, n))
                    d = fadd(w[3], pair[3])[0]
                if pair is not None and any(sibling(t, u) for u in near):
                    continue
                if complete(t):
                    if b_lp is not None and leafport(t, d) == b_lp:
                        continue
                else:
                    if b_nc or not store_ok(t):
                        continue
                choice = (w, pair, t, d)
                break
        if b_nc:
            f1_word(b[0], b[1], True)
        elif b is not None:
            store[((b[0] >> 13) + 8 * (b[0] >> 29)) & 63]['n'] -= 1
        if choice is not None:
            w, pair, t, d = choice
            arr[w[4]] = X - D_TREE; del left[w[4]]
            slottags.setdefault(X, []).extend([norm(w[2]), t])
            if pair is not None:
                arr[pair[4]] = X + 1 - D_TREE; del left[pair[4]]; blocked.add(X + 1)
                slottags.setdefault(X + 1, []).append(norm(pair[2]))
            if not complete(t):
                f1_word(t, d, False)
        X += 1
    return arr, X - t0


def gen(case, seed, out: Path, rows=None, phases=None):
    rng = random.Random(seed)
    slice_id = 5
    phases = phases or (3 if case == 'real' else 4)
    allw, allcfg, rowsd_all = [], [], {}
    t0 = 60
    meta_ph = []
    for ph in range(phases):
        R = rows or (320 if case == 'real' else rng.choice([40, 100, 320, 700]))
        npp = 0 if case == 'real' and ph < 2 else (1 if case == 'real' else rng.randint(0, 2))
        cfg, rowsd, words = make_phase(rng, case, slice_id, R, npp,
                                       [16, 28, 7, 31, 2] if case == 'real' else [0], ph)
        # legalise this phase on its own, after the previous phase drained
        cfg_edge = t0 - 8
        arr, bumps = legalise(words, t0, cfg)
        lanes = [dict() for _ in range(8)]
        for w in words:
            assert arr[w[4]] not in lanes[w[1]]
            lanes[w[1]][arr[w[4]]] = (w[2], w[3], 0, [w[4]])
        res = model(lanes, [(cfg_edge, cfg)])
        if res['faults']:
            raise SystemExit(f'model: legalised schedule faults {res["faults"][:5]}')
        if any(f[0] == 'OPEN_AT_END' for f in res['faults']):
            raise SystemExit('model: rows left open')
        # golden check of the model's sums against the independent golden tree
        for wr in res['writes']:
            row, pos = wr[5], wr[6]
            g, _ = golden_row(rowsd[(row, pos)])
            _, _, _, _, gd = decode((pos << 29) | (row << 13), g, cfg)
            assert gd == wr[4], ('model sum != golden', row, pos)
        assert len(res['writes']) == len(rowsd), 'model: not every row written'
        last_arr = {}
        for w in words:
            t = w[2]
            k_ = (((t >> 13) & 0xFFFF), t >> 29)
            last_arr[k_] = max(last_arr.get(k_, -1), arr[w[4]])
        allcfg.append((cfg_edge, cfg))
        for w in words:
            allw.append((arr[w[4]], w[1], w[2], w[3]))
        for wr in res['writes']:
            rowsd_all.setdefault('W', []).append(wr + (last_arr[(wr[5], wr[6])],))
        t_last = max(wr[0] for wr in res['writes'])
        meta_ph.append(dict(rows=R, np=npp, words=len(words), slots=bumps, cfg=cfg, first_arr=min(arr.values()),
                            last_arr=max(arr.values()), last_write=t_last,
                            merges_tree=None))
        t0 = t_last + 20
    T = t0 + 40
    out.mkdir(parents=True, exist_ok=True)
    # stim: line n drives the column-root node inputs sampled at edge n; lane word with ARR a -> line a - LL
    lines = [[0, 0] + [0] * 8 for _ in range(T)]
    for (ce, cfg) in allcfg:
        c = (cfg['obase'] | cfg['ops'] << 12 | cfg['np'] << 24 | cfg['fmt'] << 27 | cfg['rbase'] << 29 |
             cfg['rcnt'] << 45 | cfg['rsplit'] << 56 | cfg['lo32'] << 72 | cfg['hi32'] << 73)
        lines[ce][0] = 1; lines[ce][1] = c                  # the cap's cfg pin flop samples cfg_v at edge ce
    for a, lane, t, d in allw:
        n = a - LL
        assert n >= 0 and lines[n][2 + lane] == 0
        lines[n][2 + lane] = (d << 33) | (t << 1) | 1           # {e 0, d, t, v}: the dsfd_node output word
    with open(out / 'stim.hex', 'w') as f:
        for ln in lines:
            f.write('%d %040x ' % (ln[0], ln[1]) + ' '.join('%017x' % x for x in ln[2:]) + '\n')
    W = sorted(rowsd_all['W'])
    with open(out / 'expect.txt', 'w') as f:
        for a, lane, t, d in sorted(allw):
            f.write('A %d %d %08x %08x\n' % (a, lane, t, d))
        for wr in W:
            f.write('W %d %d %d %d %08x %d %d %d\n' % (wr[0], wr[1], wr[2], wr[3], wr[4], wr[5], wr[6], wr[9]))
    lat = [wr[0] - wr[9] for wr in W]
    meta = dict(case=case, seed=seed, edges=T, words=len(allw), rows_written=len(W), phases=meta_ph,
                lat_last_arr_to_write=dict(min=min(lat), max=max(lat), mean=sum(lat) / len(lat)),
                constants=dict(WIN=WIN, RST=RST, C_NODE=C_NODE, RE=RE, WR=WR, LL=LL))
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'T').write_text(str(T))
    (out / 'NW').write_text(str(len(W)))
    print('CAP_VECTORS', json.dumps({k: meta[k] for k in ('case', 'seed', 'edges', 'words', 'rows_written',
                                                         'lat_last_arr_to_write')}),
          'slots', [p['slots'] for p in meta_ph])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen')
    g.add_argument('--case', choices=['real', 'random'], default='real')
    g.add_argument('--seed', type=int, default=1)
    g.add_argument('--rows', type=int)
    g.add_argument('--phases', type=int)
    g.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    gen(a.case, a.seed, a.out, a.rows, a.phases)


if __name__ == '__main__':
    main()
