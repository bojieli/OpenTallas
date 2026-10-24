#!/usr/bin/env python3
"""TOK-S81-GAPS/XS2 (10-19): BF16 PAIR phases of the DV field placement compiler (xs_place.py) -- the frame-held BF16
matvecs of a layer on the frames' BF pairs (dsfd_bf_front_roots + two dsfd_bf_col columns, ot_s81_cfg7_seq_bfp with the
static BF programme producer ot_s81_bf_prog_seq):

  ffn.router    gate [96, 5120] BF16 (rank rows), 6 / slice, 1 / frame; x = ffn.norm.scale; FP32 out (no BF16 round)
  attn.wo_a     grouped: rank rows [2048, 4096] FP8 dequantised (exact in BF16), 128 / slice (a slice's rows are in ONE
                head group: o_rank 1024), 16 / frame; x = o[group of the slice] (attn.normalize.unrope); BF16 out
  attn.cmp.wk   indexer.wk [128, 512] BF16 (every rank), 8 / slice, 1 / frame; x = attn.cmp.norm.scale; BF16 out;
                K zero-padded to 1,024 (zero weights x reserved zero x words: every sum is the golden one)

PROGRAMME ABI LIMIT (the reason for the shape below).  The BF front issues only on its compiled calendar (f_prog from
ot_s81_bf_prog_seq, owner rule 10-14 18:59) and faults on any word that differs from its walker (programme_fault).  The
producer's 82-bit descriptor (tools/s81/bf_programme_compile.py) regenerates the operand as unit = i & (8 << LU) - 1,
block = i >> (3 + LU): it has NO unit base and NO sub-block term.  The element walks a class of > 8 units sub-block
major (q, b, unit: S.element_order), and a segment not starting at unit 0 needs a base -- so the ONLY BF segment the
current ABI can express is units [0, 8) = the first 1,024 elements of the phase's x (measured: a 16-unit router segment
mismatches 126 of 128 words, a segment at unit 16 all of them).  The compiler therefore runs every BF phase on ONE
1,024-element slice of K (BSEG): x base = s x 1,024 (the issue's xbase), the pairs' ROM words = the rows' columns
[1024 s, 1024 s + 1024), tagged as golden segment s of n = K / 1,024 (cfg seg / nseg), up to 2 x 3 rows per phase (super
row R on BF pair R).  Each phase returns one partial per row (lo s, n); the cap / collector folds the n partials (golden
padded tree).  Cost: n phases per row chunk instead of one (router 5, wo_a 4 x 3 chunks, cmp.wk 1 per layer).
COORD: a unit-base + sub-block descriptor (2 fields in desc[95:82], ot_s81_bf_prog_seq) would let one phase hold a full
row (K-split over the pairs) -- RTL change of the cfg7_seq_bfp tile, not done here.

CALENDAR.  Every BF phase streams one BSEG slice (8 units, one sub-block), so ONE measurement per frame master gives the
whole calendar: a frame bench build whose BF core issues on its own walker availability (xs_bench.sh BF_LEGACY=1: a
patched COPY of the core in the build dir, a measurement probe; the source is untouched) with -DTB_BFTRACE (every
availability edge + identity in the bf_programme_compile trace format, and every BF column partial edge).  Each pair's
trace fits ONE descriptor exactly (measured col_h9 E5: OFF 4 PER 1, 64 issues on consecutive edges, partial 106 edges
after the last issue) -- c10_nlock boundary (the roots front's programme register: OFF - 1).  A phase's descriptor =
that descriptor with BASE = the pair's ROM phase start; it rides the spare columns [71:48] of cfg words 0..3 of the
pair's phase block (il7: banks 0..3, row 4 p).  The measured column partial edges are the BF emission constants; the
return calendar is composed with them (frame_return_plan topology, static_return_calendar node rule) and the production
run (static programme, no probe) must reproduce it word for word.  Another lane latency E of the same master is
predicted by moving every partial edge by E - E_measured (frame_return_plan.x_shift: every frame event rides the
landed lanes; the programme is go-relative).

    xs_bf.py measure --log RUN.LOG --vec VECDIR [--out REC.json] [--frame lp] [--lk E]   descriptor + emission record

FRAME VARIANT (S81-P8 10-23).  The banded landed-parent frame with plan-width seams (plan v4.3, vgcs twin
col_<M>_l4_lp_rf3r, ot_pl_seam_*) moves the BF pairs' x / go inputs and return links by its landed crossings (the
frame's landed schedule results/arch/s81_dv_1016/frame_l4_cluster/compiler/col_<M>_schedule.json: e8w.r +6, n15 / n7 /
n23 +3, root link +3 ...), so the _l4 measurement does NOT carry over (the l4 E5 calendar was +3 / +6 edges early on
the first word and up to +12 later; S81-P7 seam bench).  The LP frame is measured on its own build
(tools/s81_dv/frame_bf_measure.sh: frame_bench.sh FRAME_LP=1 BF_LEGACY=1) and keyed col_<M>_lp|E<E>|bseg1024; its
return calendar is composed on the LP schedule topology.  The compiler takes the LP key when the die frame master is a
landed-parent wrapper (*_lp) or OT_XS_BF_FRAME=lp (the die of record still binds col_h*_l4); never the _l4 key.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lower_xs as LX  # noqa: E402
import numpy as np  # noqa: E402
import xs_topo as TP  # noqa: E402  S81-RATE3: physical frames per slice (OT_XS_TOPO=1)

ROOT = LX.ROOT
NSLICE, NFRAME = 16, 8
BF_OPS = ('attn.wo_a', 'ffn.router', 'attn.cmp.wk')
MEAS = 'results/rtl/s81_layer_tput_1018/compiler/bench_xsb/measure.json'


def deal(n, parts):
    b, e = divmod(n, parts)
    out, s = [], 0
    for i in range(parts):
        k = b + (1 if i < e else 0)
        out.append(list(range(s, s + k)))
        s += k
    return out


def deal_into(items, parts):
    return [[items[i] for i in idx] for idx in deal(len(items), parts)]


def bf_groups(fx, op):
    """[dict(mat, u16 [rows, K], rows, x, tie [(fixture op, index)], tie_kind 'fp32' | 'bf16', groups[g][f])]; K is
    zero-padded to a multiple of BSEG (k_pad: zero weights x zero x -- the compiler reserves k_pad zero words after x in
    the vector memory; the padded products are +0, so every segment / row sum is the golden one)"""
    out = []
    for grp in _bf_groups(fx, op):
        K = grp['u16'].shape[1]
        pad = (-K) % BSEG
        grp['k'], grp['k_pad'] = K, pad
        if pad:
            grp['u16'] = np.concatenate([grp['u16'], np.zeros((grp['u16'].shape[0], pad), grp['u16'].dtype)], axis=1)
            for kx in ('x', 'x_slice'):
                if grp.get(kx) is not None:
                    v = grp[kx]
                    grp[kx] = (np.concatenate([np.asarray(v, np.float32), np.zeros(pad, np.float32)]) if kx == 'x' else
                               [np.concatenate([np.asarray(z, np.float32), np.zeros(pad, np.float32)]) for z in v])
        out.append(grp)
    return out


def _bf_groups(fx, op):
    import hdc_golden_v41 as G
    m = fx.meta
    if op == 'ffn.router':
        u = fx.w('gate').view('<u2')
        r0 = m['tp_split']['router_rows'][m['rank']][0]
        rows = list(range(u.shape[0]))
        g = [deal_into(js, TP.nfr(s)) for s, js in enumerate(deal(len(rows), NSLICE))]
        return [dict(mat='gate', u16=u, rows=rows, x=fx.op('ffn.norm.scale'), tie=[('ffn.router', r0 + r) for r in rows],
                     tie_kind='fp32', groups=g, out='fp32')]
    if op == 'attn.cmp.wk':
        u = fx.w('indexer.wk').view('<u2')
        rows = list(range(u.shape[0]))
        g = [deal_into(js, TP.nfr(s)) for s, js in enumerate(deal(len(rows), NSLICE))]
        return [dict(mat='indexer.wk', u16=u, rows=rows, x=fx.op('attn.cmp.norm.scale'),
                     tie=[('attn.cmp.wk', r) for r in rows], tie_kind='bf16', groups=g, out='bf16')]
    if op == 'attn.wo_a':
        w, sc = fx.w('wo_a'), fx.sc('wo_a')
        e = np.repeat(np.repeat(sc, 32, axis=0), 32, axis=1).astype(np.int64)[:w.shape[0], :w.shape[1]] - 127
        deq = np.ldexp(G.E4M3[w], e)
        b = np.asarray(G.to_bf16(deq.astype(np.float32)), dtype=np.float64)
        assert np.array_equal(b, deq), 'wo_a dequantised weight not exact in BF16'
        u = (G.bits(G.to_bf16(deq.astype(np.float32))).astype(np.uint32) >> 16).astype(np.uint16)
        ra0, ra1 = m['tp_split']['wo_a_rows'][m['rank']]
        tot = m['tp_split']['wo_a_rows'][-1][1]
        o = fx.op('attn.normalize.unrope').reshape(-1)
        K = w.shape[1]
        ngr = o.size // K
        o_rank = tot // ngr
        per = deal(ra1 - ra0, NSLICE)            # slice s owns rank rows per[s] (all in one head group: o_rank % per == 0)
        # S81-SMWIRE (10-19): the SO target gather wiring delivers each head group's o to ONE slice tier (group 0 =
        # heads 0..7, E svc half -> s_4S band -> S-tier line, even sid; group 1 = heads 8..15, W half -> s_3S band -> V rung
        # -> s_3N -> N-tier line, odd sid; tools/s81_dv/sm_target/smwire_cal.py wo_a_group).  So slice s takes row
        # chunk 8 (s & 1) + (s >> 1) when the rank's rows split into two equal groups of 8 chunks.
        _g = [sorted({(ra0 + r) // o_rank for r in c}) for c in per]
        if NSLICE == 16 and all(len(x) == 1 for x in _g) and len({x[0] for x in _g[:8]}) == 1 and \
                len({x[0] for x in _g[8:]}) == 1 and _g[0] != _g[8]:
            per = [per[8 * (s & 1) + (s >> 1)] for s in range(NSLICE)]
            if TP.PROP and TP.TOPO is not None:
                # S81-RATE3 (OT_XS_PROP=1): inside each head group (even sids = group 0, odd = group 1) the group's
                # contiguous rows go to its 8 slices in proportion to their physical frames (chunk order s >> 1), so a
                # 6-frame slice no longer sets the die-wide BF phase count; every slice stays inside one head group
                for k in (0, 1):
                    sl_k = sorted((s for s in range(NSLICE) if (s & 1) == k), key=lambda s: s >> 1)
                    rows_k = [r for s in sl_k for r in per[s]]
                    ftot = sum(TP.TOPO[s] for s in sl_k)
                    q = [len(rows_k) * TP.TOPO[s] / ftot for s in sl_k]
                    cnt = [int(x) for x in q]
                    for i in sorted(range(len(sl_k)), key=lambda i: (-(q[i] - cnt[i]), i))[:len(rows_k) - sum(cnt)]:
                        cnt[i] += 1
                    off = 0
                    for s, c in zip(sl_k, cnt):
                        per[s] = rows_k[off:off + c]
                        off += c
        grp_of = [{(ra0 + r) // o_rank for r in per[s]} for s in range(NSLICE)]
        assert all(len(x) == 1 for x in grp_of), 'a slice spans two wo_a groups'
        rows = list(range(ra1 - ra0))
        g = [deal_into(per[s], TP.nfr(s)) for s in range(NSLICE)]
        # ONE die-wide phase sequence: every slice streams ITS group's o from its own vector memory (same phase words,
        # same stream shape, the x differs per slice)
        return [dict(mat='wo_a', u16=u, rows=rows, x=None, x_slice=[o.reshape(ngr, K)[grp_of[s].pop()] for s in range(NSLICE)],
                     tie=[('attn.wo_a', ra0 + r) for r in rows], tie_kind='bf16', groups=g, out='bf16')]
    raise KeyError(op)


def x_of(grp, g):
    return grp['x_slice'][g] if grp.get('x_slice') is not None else grp['x']


BSEG = 1024            # elements per BF segment: 8 units of 128 (one sub-block) -- the programme ABI's reach (see below)
BF_PAIRS_DIE = 3       # BF pairs per phase: the die-wide phase list is one sequence for every frame, so it uses the fewest
                       # BF pairs of any frame master (col_h9 3: pairs 4 / 8 / 13; col_h10 4: 1 / 5 / 10 / 15 -> 3 used)


def nseg_total(K):
    """golden-aligned segments of BSEG elements (S.segments(K, s) with chunks c = 4); K % BSEG == 0"""
    import v41_rom_ksplit_bankmap as S
    assert K % BSEG == 0, ('BF K not a multiple of the segment', K)
    n = K // BSEG
    s = next(s for s in range(1, 64) if S.segments(K, s) == [(i * BSEG, BSEG) for i in range(n)])
    return n, s


def bf_vals(u16_rows, x):
    """per row: the golden segment sums (csum of the exact BF16 products of each BSEG segment), FP32 row (csum over K),
    BF16 row"""
    import hdc_golden_v41 as G
    wf = G.from_bits(np.asarray(u16_rows).astype(np.uint32) << 16)
    prod = G.mul(np.asarray(wf, dtype=G.F), G.to_bf16(x)[None, :])
    acc = G.csum(prod)
    n = prod.shape[1] // BSEG
    vals = [[int(G.bits(G.csum(prod[r, s * BSEG:(s + 1) * BSEG]))) for s in range(n)] for r in range(prod.shape[0])]
    return vals, [int(v) for v in G.bits(acc)], [int(v) >> 16 for v in G.bits(G.to_bf16(acc))]


def shape_key(master, land_e, frame=None):
    """every BF phase streams one BSEG x slice (8 units, one sub-block): ONE stream and one element calendar per frame
    master / frame variant (None = _l4, 'lp' = banded LP frame) / lane latency, whatever the rows or the segment index"""
    return f'{master}{"_" + frame if frame else ""}|E{land_e}|bseg{BSEG}'


def frame_variant(die_master):
    """'lp' for a landed-parent die frame (master *_lp, or OT_XS_BF_FRAME=lp while the die of record binds _l4), else None"""
    import os
    v = os.environ.get('OT_XS_BF_FRAME', '').strip() or None
    if v is None and die_master.endswith('_lp'):
        v = 'lp'
    assert v in (None, 'lp', 'l4'), ('OT_XS_BF_FRAME', v)
    return None if v == 'l4' else v


def frame_topology(master, frame=None):
    """the return topology the BF partials are composed on: the recorded _l4 frame topology, or (frame 'lp') the LP
    frame's source-pinned landed schedule topology (link edges include its landed crossings; sources hash-checked).
    The schedule attributes the landed crossings for the q leaves only (its station inputs list no BF pair): a BF leaf
    whose measured return latency differs carries a MEASURED correction (measure record 'leaf_ret_corr', added to its
    partial edge before composing): vgcs col_h9 e4w / e4e -3, e8w -6; col_h10 none."""
    import frame_return_plan as P
    if frame != 'lp':
        return P.load_topology(master)
    import hashlib
    import lower_xs
    sch = json.loads(lower_xs.source_frame_schedule(master + '_l4_lp').read_text())
    for f, sha in sch['source_sha256'].items():
        assert hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == sha, f'stale landed schedule: {f}'
    assert sch['topology']['master'] == master
    return sch['topology']


def load_meas():
    p = ROOT / MEAS
    return json.loads(p.read_text()) if p.exists() else {}


def meas_for(meas, master, land_e, frame=None):
    """the shape's measurement, or the same master measured at another lane latency E' moved by E - E' edges (every
    frame-internal event rides the landed lanes: frame_return_plan.x_shift; the programme is go-relative, unchanged);
    returns (record, 'measured_shape' | 'predicted_lane_shift') or (None, None)"""
    k = shape_key(master, land_e, frame)
    if k in meas:
        return meas[k], 'measured_shape'
    if frame == 'lp':
        # NOT on the LP frame: measured vgcs col_h9 E2 -> E5 moved every BF partial +5 edges, not E - E' = +3 (the q plan
        # set at LK 5 is +2 vs frame_return_plan.x_shift too, LDLY 3 and 4): every LP lane latency is measured itself
        return None, None
    mk = k.split('|')[0]
    for k2, m in sorted(meas.items()):
        mm, e2 = k2.split('|')[0], int(k2.split('|')[1][1:])
        if mm == mk:
            d = land_e - e2
            return dict(m, pv={c: [e + d for e in v] for c, v in m['pv'].items()}, shifted_from=k2, shift=d), \
                'predicted_lane_shift'
    return None, None


def leaf(p, j):
    return f'e{p}{"we"[j]}.r'


def place_bf(assign_slots, s, n):
    """image-writer _place: super row R of the phase on field slot `slot`, the phase's ONE BSEG slice (K = BSEG local),
    tagged as golden segment s of n of the row"""
    import v41_rom_ksplit_bankmap as S

    def place(field, mats):
        assert len(mats) == 1 and mats[0].K == BSEG
        m = mats[0]
        load = np.zeros(field.np, dtype=np.int64)
        out = []
        for slot, R in assign_slots:
            load[slot] += S.seg_words('bf16', 0, BSEG)
            out.append(dict(mi=0, tensor=0, fmt='bf16', K=BSEG, row=R, e0=0, elems=BSEG, pair=slot, seg=s, nseg=n))
        return out, [dict(off=0, srows=-(-m.rows // 2), s=n, segs=[(0, BSEG)])], int(load.max())
    return place


def bf_plan(master, bf_pairs, rows_vals, s, n, meas=None, base=None, frame=None):
    """placement (super row R -> BF pair R), programme descriptors (the shape's measured descriptor with this phase's
    ROM base) and return calendar of a BF phase: segment s of n of every row (no in-frame merge: one segment per row)"""
    import frame_return_plan as P
    import static_return_calendar as C
    nr = len(rows_vals)
    nsr = -(-nr // 2)
    assert nsr <= len(bf_pairs), (nsr, bf_pairs)
    rec = dict(assign=[(R, R) for R in range(nsr)], pairs=list(bf_pairs[:nsr]), seg=s, nseg=n, desc={}, ret=[],
               faults=0, ret_words=0)
    if meas is None:
        rec['calendar'] = 'calendar_unmeasured'
        return rec
    topo = frame_topology(master, frame)
    corr = meas.get('leaf_ret_corr') or {}
    lv = {}
    for R in range(nsr):
        p = bf_pairs[R]
        for j in range(2):
            r = 2 * R + j
            if r < nr:
                lv.setdefault(leaf(p, j), []).append((meas['pv'][leaf(p, j)][0] + corr.get(leaf(p, j), 0), C._mk((P.OPTAG << 14) | r, s, 0, n),
                                                      rows_vals[r][s], 0))
    rep, ret = P.compose(topo, lv)
    desc = {}
    for R in range(nsr):
        d = dict(meas['fits'][str(bf_pairs[R])]['descriptor'], base=base[R])
        desc[str(bf_pairs[R])] = d
    rec.update(calendar=meas.get('calendar', 'measured_shape'), desc=desc, nodes=rep, faults=P.nfaults(rep), ret=[list(w) for w in ret],
               ret_words=len(ret), emission=dict(rule='E(pair column) = measured partial edge of the shape (BF_LEGACY '
                                                      'trace); every BF phase of a master / lane latency has the same '
                                                      'BSEG stream', leaves={k: [w[0] for w in v] for k, v in lv.items()}))
    return rec


# ------------------------------------------------------------------------------------------------ measurement
def parse_trace(log):
    """BFG / BFI lines (tb_bf_issue_trace) per core instance -> bf_programme_compile phases; BFPV lines -> edges"""
    inst = {}
    for m in re.finditer(r'^BF([GI]) (\S+) (.*)$', log, re.M):
        k, path, rest = m.group(1), m.group(2), m.group(3).split()
        p = re.search(r'u_e(\d+)\b', path).group(1)
        d = inst.setdefault(p, dict(go=[], ev=[]))
        if k == 'G':
            d['go'].append(dict(edge=int(rest[0]), cyc=int(rest[1]), go_bf=int(rest[2])))
        else:
            edge, cyc, off, a, op, s, h, c, gb = map(int, rest[:9])
            d['ev'].append(dict(edge=edge, off=off, addr=a, op=op, seg=s, half=h, chain=c))
    pv = {}
    for m in re.finditer(r'^BFPV (\d+) (\S+) rows (\d+) seg (\d+) n (\d+)$', log, re.M):
        col = re.search(r'u_e(\d+)([we])\b', m.group(2))
        pv.setdefault(f'e{col.group(1)}{col.group(2)}.r', []).append(dict(edge=int(m.group(1)), row=int(m.group(3)),
                                                                          seg=int(m.group(4)), n=int(m.group(5))))
    return inst, pv


def fit(BC, ph):
    """bf_programme_compile.fit with both burst forms tried: its LB heuristic (two issues on adjacent edges = an FP8
    half pair) mistakes a BF calendar issuing on EVERY edge for bursts; LB 0 / PER 1 is the exact form there"""
    best = None
    for lb in (0, 1):
        ev = ph['ev']
        n = len(ev)
        per = (ev[1 << lb]['off'] - ev[0]['off']) if n > (1 << lb) else 0
        r = BC.fit(ph)
        d = dict(r if isinstance(r, dict) else r[0], lb=lb, per=per)
        lu = next((k for k in range(4) if (8 << k) >= max(e['op'] & 255 for e in ev) + 1), 0)
        d['lu'] = lu
        ssh = next((s for s in range(8) if all(e['seg'] == (i >> s) & d['sm'] for i, e in enumerate(ev))), 0)
        d['ssh'] = ssh
        bad = [i for i, e in enumerate(ev) if BC.word(d, i) != e]
        if best is None or len(bad) < len(best[1]):
            best = (d, bad)
    return best


def cmd_measure(a):
    sys.path.insert(0, str(ROOT / 'tools/s81'))
    import bf_programme_compile as BC
    log = Path(a.log).read_text()
    meta = json.loads((Path(a.vec) / 'meta.json').read_text())
    inst, pv = parse_trace(log)
    desc, fits, ok = {}, {}, True
    for p in meta['bf']['pairs']:
        d = inst.get(str(p))
        if not d or not d['ev']:
            print('NO_TRACE pair', p)
            ok = False
            continue
        bfgo = [g for g in d['go'] if g['go_bf'] == 1]
        assert len(bfgo) == 1, ('one BF go per run', p, d['go'])
        ph = dict(go_cycle=bfgo[0]['cyc'], go_bf=1, ev=[dict((k, e[k]) for k in ('off', 'addr', 'op', 'seg', 'half', 'chain'))
                                                       for e in d['ev']])
        dd, bad = fit(BC, ph)
        em = BC.advance_descriptor(dd)                 # c10_nlock: roots front programme register (+1 edge)
        bad += [i for i, e in enumerate(ph['ev']) if dict(BC.word(em, i), off=BC.word(em, i)['off'] + 1) != e]
        fits[str(p)] = dict(issues=len(ph['ev']), descriptor_fit=dd, descriptor=em, mismatches=len(bad),
                            first_issue_edge=d['ev'][0]['edge'], last_issue_edge=d['ev'][-1]['edge'],
                            go_edge=bfgo[0]['edge'])
        desc[str(p)] = BC.pack(em)
        ok &= not bad
    want = {leaf(p, j) for p, (R, _) in zip(meta['bf']['pairs'], meta['bf']['assign']) for j in (0, 1)
            if 2 * R + j < meta['nrows']}
    edges = {k: [w['edge'] for w in v] for k, v in pv.items() if k in want}
    ok &= set(edges) == want and all(len(v) == 1 for v in edges.values())
    land_e = meta['land_e'] if a.lk is None else a.lk
    key = shape_key(meta['master'], land_e, a.frame)
    # self-check: the probe run's own ret words = the measured partials composed on the frame's return topology
    import frame_return_plan as P
    import static_return_calendar as C
    lv = {}
    for p, (R, _) in zip(meta['bf']['pairs'], meta['bf']['assign']):
        for j in (0, 1):
            r = 2 * R + j
            if r < meta['nrows'] and leaf(p, j) in edges:
                lv[leaf(p, j)] = [(edges[leaf(p, j)][0], C._mk((P.OPTAG << 14) | r, meta['seg'], 0, meta['nseg']),
                                   meta['rows'][str(r)]['vals'][meta['seg']], 0)]
    # per leaf: the probe run's ret edge of the leaf's row (row tag of the ret word) - its partial edge = the leaf's
    # measured return latency; a leaf whose LP schedule path differs gets the difference added to its partial edge
    # (leaf_ret_corr; compose is linear in the leaf edge before its first node), then the composed calendar
    # (node rule, WIN / RST) must reproduce the run's ret words exactly
    from static_return_calendar import _f, norm
    got, ret_lat = [], {}
    for m_ in re.finditer(r'^RET (\d+) ([0-9a-f]+)$', log, re.M):
        e_, w_ = int(m_.group(1)), int(m_.group(2), 16)
        r_ = _f(norm((w_ >> 1) & 0xFFFFFFFF))[0] & 0x3FFF
        got.append(e_)
        R_ = r_ // 2
        p_ = next(p for p, (RR, _) in zip(meta['bf']['pairs'], meta['bf']['assign']) if RR == R_)
        if leaf(p_, r_ % 2) in edges:
            ret_lat[leaf(p_, r_ % 2)] = e_ - edges[leaf(p_, r_ % 2)][0]
    topo0 = frame_topology(meta['master'], a.frame)
    corr = {}
    if a.frame == 'lp':
        corr = {k: v - P.leaf_path(topo0, k)[0] for k, v in ret_lat.items() if v != P.leaf_path(topo0, k)[0]}
    lvc = {k: [(w[0] + corr.get(k, 0),) + tuple(w[1:]) for w in v] for k, v in lv.items()}
    rep_, ret = P.compose(topo0, lvc)
    ret_ok = sorted(w[0] for w in ret) == sorted(got) and P.nfaults(rep_) == 0
    ok &= ret_ok
    rec = dict(key=key, op=meta['op'], field_phase=meta['field_phase'], die_frame=meta['die_frame'], ok=bool(ok),
               frame=a.frame or 'l4', land_e=land_e, ret_composed=sorted(w[0] for w in ret), ret_run=sorted(got),
               ret_self_check=bool(ret_ok), log=str(a.log), ret_lat=ret_lat, leaf_ret_corr=corr,
               ret_uncorrected=sorted(w[0] for w in P.compose(topo0, lv)[1]),
               desc=desc, fits=fits, pv=edges, pv_all={k: v for k, v in pv.items()},
               lat_issue_to_pv={k: edges[k][0] - fits[k[1:-3]]['last_issue_edge'] for k in edges if k[1:-3] in fits})
    print('XS_BF_RET_SELF_CHECK', 'OK' if ret_ok else 'FAIL', 'composed', sorted(w[0] for w in ret), 'run', sorted(got),
          'leaf_ret_corr', corr)
    print('XS_BF_MEASURE', 'OK' if ok else 'FAIL', key, json.dumps({k: (v['issues'], v['descriptor'], v['mismatches'])
                                                                   for k, v in fits.items()}), 'pv', edges)
    if a.out:
        p = Path(a.out)
        allm = json.loads(p.read_text()) if p.exists() else {}
        allm[key] = rec
        p.write_text(json.dumps(allm, indent=1, sort_keys=True) + '\n')
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    m = sp.add_parser('measure')
    m.add_argument('--log', required=True)
    m.add_argument('--vec', required=True)
    m.add_argument('--out', default=None)
    m.add_argument('--frame', choices=('lp',), default=None, help='frame variant measured (default the _l4 frame)')
    m.add_argument('--lk', type=int, default=None, help='bench lane strap E when it differs from the vector die frame')
    a = ap.parse_args(argv)
    return {'measure': cmd_measure}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
