#!/usr/bin/env python3
"""LB2-S81/CC fork VPX: stimulus + expectations for tb_vpx_ag.sv from the compiler's lowering (lower_vpx.leg_program).

Vehicle: die A = rank 0 (u_s_0S, W end), die B = rank 3 = A's W peer (u_s_7S, E end).  The a_proj all-gather leg of each
die: its own part (fixture attn.a_allgather, rank rows per lower_vpx.a_rows) out of the outward port to the peer end slice.
Bench-only phases (labelled, not compiled programme): PRELOAD = the own part written into leaf 0 by RD beats on the inward
pin (stands for the a_proj return); READBACK = every gathered row read through the real store (RDOUT + send to the inward
side, the bench pin) after the leg.
    gen_vpx_ag.py --fixtures L0DIR --out DIR [--mut none|row|shift] [--sa 0 --sb 14] [--op a_allgather|router_allgather|
                  substage_hop0|out_allreduce_rs|out_allreduce_ag]  (TOK-DS-8: the other shared collectives, lower_vpx placement)
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import lower_vpx as LV  # noqa: E402

WAIT = 8000          # link lanes live (tb_s81sl_slice_lep WAIT)
PRE_GAP = 6          # preload RD beats: one every 6 edges (unpacker busy 4)


SHAPES = {'attn.a_allgather': [1792], 'ffn.router_allgather': [384], 'substage_hop0': [4, 5120],
          'attn.out_allreduce': [5120]}


def words(fx, name='attn.a_allgather'):
    meta = json.loads((fx / 'files.json').read_text())[f'ops/{name}.bin']
    assert meta['dtype'] == 'float32' and meta['shape'] == SHAPES[name], meta
    raw = (fx / f'ops/{name}.bin').read_bytes()
    n = len(raw) // 4
    return [int.from_bytes(raw[4 * i:4 * i + 4], 'little') for i in range(n)]


def row(w, r):
    return sum(w[4 * r + i] << (32 * i) for i in range(4))


def beat_data(w, rows):
    return sum(row(w, r) << (128 * j) for j, r in enumerate(rows))


def ctl_beat(sid, c):
    p = LV._payload(1 << sid, c['target'], c['leaf_mask'], c['body'])
    return 1 | (1 << 4) | (4 << 9) | p << 21          # CTL, hops 1 (delivered at this end slice), src 4 (seq_host)


def gen(fx, out, mut='none', sa=0, sb=14, op='a_allgather'):
    """op = a_allgather (10-18 case, unchanged) | router_allgather | substage_hop0 | out_allreduce_rs | out_allreduce_ag
    (TOK-DS-8): the legs of die A (rank 0, s_0S W) and die B (rank 3, s_7S E) from lower_vpx's placement of that op."""
    out.mkdir(parents=True, exist_ok=True)
    stim, exp = [], dict(schema='opentallas.s81_dv.vpx_ag_expect.v1', mut=mut, sa=sa, sb=sb, op=op,
                         consts=dict(CFG_AT=LV.CFG_AT, LO_AFTER_CTL=LV.LO_AFTER_CTL, SEND_AFTER_GO=LV.SEND_AFTER_GO,
                                     RX_WR_AFTER_PIN=LV.RX_WR_AFTER_PIN, period=LV.beat_period()))
    dies = dict(A=dict(port=0, sid=sa, rank=0, dir='W', peer='B', psid=sb, rb_dir='E'),
                B=dict(port=1, sid=sb, rank=3, dir='E', peer='A', psid=sa, rb_dir='W'))
    P = LV.beat_period()
    # per die: preload {(leaf, row): value} and legs [(leaf rows, leaf, dst leaf, dst off, t_rel)]
    mem = {d: {} for d in dies}
    legs = {d: [] for d in dies}
    if op in ('a_allgather', 'router_allgather'):
        name = 'attn.a_allgather' if op == 'a_allgather' else 'ffn.router_allgather'
        w = words(fx, name)
        rf = LV.a_rows if op == 'a_allgather' else LV.router_rows
        base = 0 if op == 'a_allgather' else 448
        for d, D in dies.items():
            for r in rf(D['rank']):
                mem[d][(0, r)] = row(w, r - base)
            legs[d].append((rf(D['rank']), 0, None, 0, 0))
    elif op == 'substage_hop0':
        w = words(fx, 'substage_hop0')                      # [4, 5120] row-major: stream r = words 5120 r ..
        D = dies['A']                                       # one direction: stage s (A, rank 0) -> stage s + 1 (B)
        trel = 0
        for lf, first, n in LV.STAGE_SEGS:
            for i in range(n):
                mem['A'][(lf, i)] = row(w, (5120 * D['rank']) // 4 + first + i)
            legs['A'].append((list(range(n)), lf, None, 0, trel))
            trel += (n // 8) * P
    elif op in ('out_allreduce_rs', 'out_allreduce_ag'):
        w = words(fx, 'attn.out_allreduce')                 # transport payload = the fixture words (partials not in it)
        for d, D in dies.items():
            pr = dies[D['peer']]['rank']
            q = pr if op == 'out_allreduce_rs' else D['rank']
            lf, r0 = LV.ar_quarter(q)
            for j in range(320):
                mem[d][(lf, r0 + j)] = row(w, 320 * q + j)
            if op == 'out_allreduce_rs':
                dl, dr = LV.rs_slot(D['rank'], pr)
                legs[d].append((list(range(r0, r0 + 320)), lf, dl, dr - r0, 0))
            else:
                legs[d].append((list(range(r0, r0 + 320)), lf, None, 0, 0))
    else:
        raise SystemExit(f'unknown op {op}')
    # PRELOAD (bench): every own row written by RD beats on the inward pin (stands for the producer capture)
    npre_max = 0
    for d, D in dies.items():
        npre = 0                                            # each die's preload starts at WAIT on its own pin
        by_leaf = {}
        for (lf, r) in sorted(mem[d]):
            by_leaf.setdefault(lf, []).append(r)
        for lf, rs_ in by_leaf.items():
            for i in range(0, len(rs_), 8):
                br = rs_[i:i + 8]
                stim.append((WAIT + PRE_GAP * (npre + i // 8), D['port'],
                             LV.rd_beat(4, 1, 1 << D['sid'], lf, br[0], len(br) // 2,
                                        sum(mem[d][(lf, r)] << (128 * j) for j, r in enumerate(br)))))
            npre += (len(rs_) + 7) // 8
        npre_max = max(npre_max, npre)
    t0 = WAIT + PRE_GAP * max(16, npre_max) + 40            # 16 = the 10-18 case margin (a_allgather byte-identical)
    exp['t0'] = t0
    exp['sends'], exp['wr'], exp['readback'] = {'A': [], 'B': []}, {'A': [], 'B': []}, {}
    after = {d: dict(mem[d]) for d in dies}
    owner = {d: {k: D['rank'] for k in mem[d]} for d, D in dies.items()}
    nbeats = 0
    for d, D in dies.items():
        for k, (own, lf, dl, doff, trel) in enumerate(legs[d]):
            m = None if mut == 'none' or k else mut         # the mutant applies to the first leg of each die
            leg = LV.leg_program(D['sid'], D['dir'], D['psid'], own, leaf=lf, t0=t0 + trel, mut=m, dst_leaf=dl, dst_off=doff)
            good = LV.leg_program(D['sid'], D['dir'], D['psid'], own, leaf=lf, t0=t0 + trel, dst_leaf=dl, dst_off=doff)
            nbeats = max(nbeats, (trel // P) + len(good['sends']))
            for c in leg['ctl']:
                stim.append((c['cycle'], D['port'], ctl_beat(D['sid'], c)))
            for s in good['sends']:
                data = sum(mem[d][(lf, r)] << (128 * j) for j, r in enumerate(s['rows']))
                exp['sends'][d].append(dict(cycle=s['cycle'], beat=f"{LV.rd_beat(s['src'], 1, s['dst_mask'], s['leaf'], s['dst_row'], s['pairs'], data):x}"))
            nb = len(exp['wr'][D['peer']]) and (exp['wr'][D['peer']][-1]['beat'] + 1)
            for i, s in enumerate(good['sends']):
                for j in range(s['pairs']):
                    r = s['rows'][2 * j]
                    dr = s['dst_row'] + 2 * j
                    exp['wr'][D['peer']].append(dict(leaf=s['leaf'], row=dr, beat=nb + i, pair=j,
                                                     data=f"{mem[d][(lf, r)] | mem[d][(lf, r + 1)] << 128:x}"))
                    after[D['peer']][(s['leaf'], dr)] = mem[d][(lf, r)]
                    after[D['peer']][(s['leaf'], dr + 1)] = mem[d][(lf, r + 1)]
                    owner[D['peer']][(s['leaf'], dr)] = owner[D['peer']][(s['leaf'], dr + 1)] = D['rank']
    t1 = t0 + nbeats * P + 1200
    exp['t1'] = t1
    # READBACK (bench): every row the die holds after the op (own + received) through the real store to the bench pin
    nrb = 0
    for d, D in dies.items():
        exp['readback'][d] = []
        by_leaf = {}
        for (lf, r) in sorted(after[d], key=lambda k: (k[0], owner[d][k])):   # stable: placement order in a rank
            by_leaf.setdefault(lf, []).append(r)
        trel = 0
        for lf, rs_ in by_leaf.items():
            rb = LV.leg_program(D['sid'], D['rb_dir'], 15, rs_, leaf=lf, t0=t1 + trel)
            for c in rb['ctl']:
                stim.append((c['cycle'], D['port'], ctl_beat(D['sid'], c)))
            exp['readback'][d] += [dict(cycle=s['cycle'], rows=s['rows'], leaf=lf,
                                        data=f"{sum(after[d][(lf, r)] << (128 * j) for j, r in enumerate(s['rows'])):x}")
                                   for s in rb['sends']]
            trel += len(rb['sends']) * P
        nrb = max(nrb, trel // P)
    end = t1 + nrb * P + 300
    exp['end'] = end
    stim.sort(key=lambda x: (x[0], x[1]))
    for a, b in zip(stim, stim[1:]):
        assert (a[0], a[1]) != (b[0], b[1]), f'two beats on one pin in one cycle: {a[:2]}'
    (out / 'stim.txt').write_text(f'END {end}\n' + ''.join(f'{c} {p} {b:0276x}\n' for c, p, b in stim))
    (out / 'expect.json').write_text(json.dumps(exp, indent=1) + '\n')
    return exp


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--mut', default='none', choices=('none', 'row', 'shift'))
    ap.add_argument('--sa', type=int, default=0)
    ap.add_argument('--sb', type=int, default=14)
    ap.add_argument('--op', default='a_allgather', choices=('a_allgather', 'router_allgather', 'substage_hop0', 'out_allreduce_rs', 'out_allreduce_ag'))
    a = ap.parse_args(argv)
    e = gen(Path(a.fixtures), Path(a.out), a.mut, a.sa, a.sb, a.op)
    print(json.dumps(dict(t0=e['t0'], t1=e['t1'], end=e['end'], sends={k: len(v) for k, v in e['sends'].items()})))


if __name__ == '__main__':
    main()
