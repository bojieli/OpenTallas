#!/usr/bin/env python3
"""LB2-S81/CC fork VPX: stimulus + expectations for tb_vpx_ag.sv from the compiler's lowering (lower_vpx.leg_program).

Vehicle: die A = rank 0 (u_s_0S, W end), die B = rank 3 = A's W peer (u_s_7S, E end).  The a_proj all-gather leg of each
die: its own part (fixture attn.a_allgather, rank rows per lower_vpx.a_rows) out of the outward port to the peer end slice.
Bench-only phases (labelled, not compiled programme): PRELOAD = the own part written into leaf 0 by RD beats on the inward
pin (stands for the a_proj return); READBACK = every gathered row read through the real store (RDOUT + send to the inward
side, the bench pin) after the leg.
    gen_vpx_ag.py --fixtures L0DIR --out DIR [--mut none|row|shift] [--sa 0 --sb 14]
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


def words(fx):
    meta = json.loads((fx / 'files.json').read_text())['ops/attn.a_allgather.bin']
    assert meta['dtype'] == 'float32' and meta['shape'] == [1792], meta
    raw = (fx / 'ops/attn.a_allgather.bin').read_bytes()
    return [int.from_bytes(raw[4 * i:4 * i + 4], 'little') for i in range(1792)]


def row(w, r):
    return sum(w[4 * r + i] << (32 * i) for i in range(4))


def beat_data(w, rows):
    return sum(row(w, r) << (128 * j) for j, r in enumerate(rows))


def ctl_beat(sid, c):
    p = LV._payload(1 << sid, c['target'], c['leaf_mask'], c['body'])
    return 1 | (1 << 4) | (4 << 9) | p << 21          # CTL, hops 1 (delivered at this end slice), src 4 (seq_host)


def gen(fx, out, mut='none', sa=0, sb=14):
    w = words(fx)
    out.mkdir(parents=True, exist_ok=True)
    stim, exp = [], dict(schema='opentallas.s81_dv.vpx_ag_expect.v1', mut=mut, sa=sa, sb=sb,
                         consts=dict(CFG_AT=LV.CFG_AT, LO_AFTER_CTL=LV.LO_AFTER_CTL, SEND_AFTER_GO=LV.SEND_AFTER_GO,
                                     RX_WR_AFTER_PIN=LV.RX_WR_AFTER_PIN, period=LV.beat_period()))
    dies = dict(A=dict(port=0, sid=sa, rank=0, dir='W', peer='B', psid=sb, rb_dir='E'),
                B=dict(port=1, sid=sb, rank=3, dir='E', peer='A', psid=sa, rb_dir='W'))
    # PRELOAD (bench)
    for d, D in dies.items():
        rows = LV.a_rows(D['rank'])
        for i in range(0, len(rows), 8):
            br = rows[i:i + 8]
            stim.append((WAIT + PRE_GAP * (i // 8), D['port'],
                         LV.rd_beat(4, 1, 1 << D['sid'], 0, br[0], len(br) // 2, beat_data(w, br))))
    t0 = WAIT + PRE_GAP * 16 + 40
    exp['t0'] = t0
    exp['sends'], exp['wr'], exp['readback'] = {}, {}, {}
    # the compiled leg (mutant applied by the compiler side)
    for d, D in dies.items():
        leg = LV.leg_program(D['sid'], D['dir'], D['psid'], LV.a_rows(D['rank']), t0=t0, mut=None if mut == 'none' else mut)
        good = LV.leg_program(D['sid'], D['dir'], D['psid'], LV.a_rows(D['rank']), t0=t0)
        for c in leg['ctl']:
            stim.append((c['cycle'], D['port'], ctl_beat(D['sid'], c)))
        exp['sends'][d] = [dict(cycle=s['cycle'], beat=f"{LV.rd_beat(s['src'], 1, s['dst_mask'], s['leaf'], s['dst_row'], s['pairs'], beat_data(w, s['rows'])):x}")
                           for s in good['sends']]
        # the peer's leaf 0 receives the rows (row pair writes, one a cycle, relative to the beat on its lep pin)
        exp['wr'][D['peer']] = [dict(row=s['rows'][2 * j], data=f"{row(w, s['rows'][2 * j]) | row(w, s['rows'][2 * j + 1]) << 128:x}",
                                     beat=i, pair=j) for i, s in enumerate(good['sends']) for j in range(s['pairs'])]
    t1 = t0 + 14 * LV.beat_period() + 1200
    exp['t1'] = t1
    # READBACK (bench): all gathered rows of ranks 0 and 3 out of the inward side to the bench pin, through the real store
    for d, D in dies.items():
        rows = LV.a_rows(0) + LV.a_rows(3)
        rb = LV.leg_program(D['sid'], D['rb_dir'], 15, rows, t0=t1)
        for c in rb['ctl']:
            stim.append((c['cycle'], D['port'], ctl_beat(D['sid'], c)))
        exp['readback'][d] = [dict(cycle=s['cycle'], rows=s['rows'], data=f"{beat_data(w, s['rows']):x}") for s in rb['sends']]
    end = t1 + 28 * LV.beat_period() + 300
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
    a = ap.parse_args(argv)
    e = gen(Path(a.fixtures), Path(a.out), a.mut, a.sa, a.sb)
    print(json.dumps(dict(t0=e['t0'], t1=e['t1'], end=e['end'], sends={k: len(v) for k, v in e['sends'].items()})))


if __name__ == '__main__':
    main()
