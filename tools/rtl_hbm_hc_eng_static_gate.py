#!/usr/bin/env python3
"""H-NETLIST/hceng 2026-10-16: bench vectors + static programme for ot_hbm_hc_eng_static (full-form HC.HC_MIX,
W = 256, K = 20,480, 24 rows, P positions) and the gathered-mix (G22) tail case.

Writes into --run: prog.mem (event words, 256-b hex), tbl.mem (bases/scales rows), wmem.mem / xmem.mem (waves as
binary32 words), sched.txt (quadrant wave sources: q T count kind src word0), gm.txt (gathered-mix words),
expmix.mem / exptail.mem (golden), case.json (schedule constants).  The golden is tools/hdc_golden_v41 chunk8
(rtl_hdc_v41x_hcp_campaign.synth_case) for the mixes and the codex tail reference (sigmoid / exp / Sinkhorn 20) for
the 24-word result.

Timing model of the programme (event at time T fires on the sequencer edge t == T; everything below is in t):
  ingest event at T  -> quadrant wave n must be on the x_wave_v pins in cycle t == T + 1 + 4 n (registered at the
                        engine pin, due at t == T + 2 + 4 n); quadrant q's events are offset by q (one wave an edge).
  launch at TL       -> raw accumulation a (a = 25 p + i, i = 0 ss, 1..24 rows) reaches the raw FIFO at
                        TL + RAW0 + 10 a (RAW0 measured by --probe); pop ss at arrival, rows at
                        max(arrival, ss pop + RS) (RS measured); mix o_valid at pop + OV.
  tail launch        -> fixed L = 496 edges to the unit's result; emit one edge later or after.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41x_hcp_campaign as hc  # noqa: E402

K, ROWS, WPR = 20480, 24, 80
EPS = 0x358637bd
F = np.float32


def tail_ref(m, b, s):
    pre = G.add(G.sigmoid(G.add(G.mul(m[:4], s[0]), b[:4])), F(1e-6))
    post = G.mul(G.sigmoid(G.add(G.mul(m[4:8], s[1]), b[4:8])), F(2))
    c = G.add(G.mul(m[8:], s[2]), b[8:]).reshape(4, 4)
    e = G.exp(G.add(c, G.neg(np.max(c, axis=1, keepdims=True))))
    c = G.add(G.div(e, G.seqsum([e[:, k] for k in range(4)])[:, None]), F(1e-6))

    def cols(x): return G.div(x, G.add(G.seqsum([x[k, :] for k in range(4)]), F(1e-6))[None, :])

    def rows(x): return G.div(x, G.add(G.seqsum([x[:, k] for k in range(4)]), F(1e-6))[:, None])
    c = cols(c)
    for _ in range(19):
        c = cols(rows(c))
    return np.concatenate((pre, post, c.reshape(-1)))


def word(t, **f):
    """one event word (payload + time + magic/pc filled by the caller)."""
    v = t
    lay = dict(ing=(20, 1), ingq=(21, 2), kind=(23, 1), slot=(24, 2), lo=(26, 5), w=(31, 7), cnt=(38, 12),
               word=(50, 10), gm=(60, 1), gmq=(61, 2), gmo=(63, 1), launch=(64, 1), npos=(65, 4), wslot=(69, 2),
               eps=(71, 32), pop=(103, 1), clear=(104, 1), tf=(105, 1), tset=(106, 7), tl=(113, 1), tunit=(114, 1),
               tpos=(115, 3), emit=(118, 1), qmask=(119, 4), eunit=(123, 1))
    for k, x in f.items():
        lo, n = lay[k]
        assert 0 <= x < (1 << n), (k, x)
        v |= x << lo
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--npos', type=int, default=1)
    ap.add_argument('--mode', choices=('full', 'probe', 'g22'), default='full')
    ap.add_argument('--raw0', type=int, default=0)
    ap.add_argument('--rs', type=int, default=0)
    ap.add_argument('--seed', type=int, default=20261016)
    # HBM-B-RTL2 (2026-10-17): plan (b) split engine ot_hbm_hc_root_static + 4 x ot_hbm_hc_qeng_static
    # (tb_hbm_hc_eng4_static).  Waves keep the single-block cadence and times; quarter q ingests its quarter slice of
    # all 24 rows (480 quarter-local waves) and of every position (20 waves); each ingest event fires --ding edges
    # earlier (root out flop + quarter pin flop + XRD relays).  RAW0 from the split probe.
    ap.add_argument('--split', action='store_true')
    ap.add_argument('--ding', type=int, default=2)
    sys.path.insert(0, str(ROOT / 'tools' / 'hbm_static'))
    import leaf_split_latency as LS  # HBM-P6-CMP: default = LS 'hc_tail_result' (7 with OT_HBM_LEAF_SPLIT=1, else 0)
    ap.add_argument('--tail-extra', type=int, default=LS.shift('hc_tail_result'),
                    help='HBM-P5-RTLB 10-23: extra tail result edges (hc_root split twin: +7 = one sink edge); default '
                         'leaf_split_latency hc_tail_result (0 unless OT_HBM_LEAF_SPLIT=1)')
    a = ap.parse_args()
    run = a.run
    run.mkdir(parents=True, exist_ok=True)
    P = a.npos
    rng = np.random.default_rng(a.seed)
    G.set_arith('chunk8')
    c = hc.synth_case('production K20480 24 rows', rng, K, ROWS, P, 1, 'typical', {'fn_std': .001, 'x_std': 1.})
    fn, x, mix = c['fn'], c['x'], c['exp']                        # [24,K] f32, [P,K] bf16-valued f32, [P,24]
    nset = 3
    bases = rng.normal(0, 1, (nset, 24)).astype(F)
    scales = rng.uniform(.1, 2, (nset, 3)).astype(F)
    tset = 2                                                       # the record's (layer, set) table entry
    tail = np.array([tail_ref(mix[p], bases[tset], scales[tset]) for p in range(P)])
    u32 = lambda v: np.asarray(v, F).view(np.uint32)
    np.savetxt(run / 'wmem.mem', u32(fn).reshape(-1), fmt='%08x')
    np.savetxt(run / 'xmem.mem', u32(x).reshape(-1), fmt='%08x')
    np.savetxt(run / 'expmix.mem', u32(mix).reshape(-1), fmt='%08x')
    np.savetxt(run / 'exptail.mem', u32(tail).reshape(-1), fmt='%08x')
    with open(run / 'tbl.mem', 'w') as f:
        # F20 table rows (0600 collar fold): [255:224] = row header (written by the bench), payload 7 FP32 words;
        # set s = rows 4s..4s+3, base i = row i/7 word i%7, scale j = row 3 word 3 + j (payload word 24 + j)
        for s in range(nset):
            words = list(u32(bases[s])) + list(u32(scales[s])) + [0]
            for r4 in range(4):
                f.write('0' * 8 + ''.join('%08x' % words[r4 * 7 + i] for i in reversed(range(7))) + '\n')
    ev, sched, gm = {}, [], []

    def add(t, **f):
        ev.setdefault(t, {}).update(f)
    slot = 1
    T0 = 8
    if a.mode != 'g22':
        # phase A: the weight set (slot 1) from the 4 quadrants, quadrant q rows 6q..6q+5, 480 waves each
        for q in range(4):
            t = T0 + q
            if a.split:
                add(t - a.ding, ing=1, ingq=q, kind=1, slot=slot, lo=0, w=0, cnt=480, word=0)
                sched.append((q, t + 1, 480, 1, 0, 0))
                continue
            add(t, ing=1, ingq=q, kind=1, slot=slot, lo=6 * q, w=0, cnt=480, word=0)
            sched.append((q, t + 1, 480, 1, (6 * q) * WPR, 0))
        TB = T0 + 4 * 480 + 16                                     # record start (HC_MIX latency counts from here)
        # phase B: x of P positions; quadrant q supplies waves 20q..20q+19 of every position
        for p in range(P):
            for q in range(4):
                t = TB + q + 80 * p
                if a.split:
                    add(t - a.ding, ing=1, ingq=q, kind=0, slot=0, lo=p, w=0, cnt=20, word=(20 * p) % 1024)
                    sched.append((q, t + 1, 20, 0, p, (20 * p) % 1024))
                    continue
                add(t, ing=1, ingq=q, kind=0, slot=0, lo=p, w=20 * q, cnt=20, word=(20 * p) % 1024)
                sched.append((q, t + 1, 20, 0, p * WPR + 20 * q, (20 * p) % 1024))
        land0 = TB + 3 + 2 + 4 * 19 + 3                             # last wave of position 0 written in the banks
        TL = land0 + 2
        add(TL - 1, clear=1)
        add(TL, launch=1, npos=P, wslot=slot, eps=EPS)
        events = {'TB': TB, 'TL': TL}
        if a.mode == 'probe':
            add(TL + 1500 * P, clear=1)                            # keeps the programme (and t) running
        if a.mode == 'full':
            assert a.raw0 and a.rs, 'full mode needs --raw0/--rs from the probe'
            pops, ss_pop = {}, {}
            last = 0
            for p in range(P):
                for i in range(25):
                    arr = TL + a.raw0 + 10 * (25 * p + i)
                    tp = max(arr, last + 1)
                    if i == 0:
                        ss_pop[p] = tp
                    else:
                        tp = max(tp, ss_pop[p] + a.rs)
                    pops[(p, i)] = tp
                    last = tp
                    add(tp, pop=1)
            OV = 6
            tl_t, em_t, tf_t = {}, {}, {}
            unit_free = [0, 0]
            for p in range(P):
                ready = pops[(p, 24)] + OV + 1
                u = p % 2
                t = max(ready, unit_free[u])
                while t in ev and ('tl' in ev[t] or 'tf' in ev[t]):
                    t += 1
                tft = t - 7
                while tft in ev and 'tf' in ev[tft]:
                    tft -= 1
                add(tft, tf=1, tset=tset)
                add(t, tl=1, tunit=u, tpos=p)
                e = t + 497 + a.tail_extra
                while e in ev and 'emit' in ev[e]:
                    e += 1
                add(e, emit=1, qmask=0xf, eunit=u)
                unit_free[u] = e + 1
                tl_t[p], em_t[p], tf_t[p] = t, e, tft
            events.update(pops={f'{p},{i}': v for (p, i), v in pops.items()}, tail_launch=tl_t, emit=em_t)
    else:
        # G22 form: the 24 mixes of position 0 arrive as gathered words from quadrant 1 (one an edge), then tail
        TB = T0
        add(TB, gm=1, gmq=1, gmo=1)
        add(TB - 1, clear=1)
        for o in range(24):
            gm.append((1, TB + 2 + o, 0, o, int(u32(mix[0])[o])))
        add(TB + 2 + 24 + 4, gm=1, gmq=1, gmo=0)
        t = TB + 2 + 24 + 6
        add(t - 7, tf=1, tset=tset)
        add(t, tl=1, tunit=1, tpos=0)
        add(t + 497 + a.tail_extra, emit=1, qmask=0b0101, eunit=1)
        events = {'TB': TB, 'tail_launch': t}
        P = 1
    words = []
    for pc, t in enumerate(sorted(ev)):
        v = word(t, **ev[t]) | (0xc7a1 << 240) | (pc << 224)
        words.append('%064x' % v)
    assert len(words) <= 1024, len(words)
    (run / 'prog.mem').write_text('\n'.join(words) + '\n')
    (run / 'sched.txt').write_text(''.join('%d %d %d %d %d %d\n' % s for s in sched))
    (run / 'gm.txt').write_text(''.join('%d %d %d %d %d\n' % g for g in gm))
    meta = dict(split=a.split, ding=a.ding if a.split else 0, mode=a.mode, npos=P, words=len(words), events=events, waves=sum(s[2] for s in sched),
                gathered=len(gm), raw0=a.raw0, rs=a.rs, emits=P * (4 if a.mode == 'full' else 2) if a.mode != 'probe' else 0)
    (run / 'case.json').write_text(json.dumps(meta, indent=1) + '\n')
    (run / 'plus.txt').write_text(f"+NWORDS={len(words)} +NSCHED={len(sched)} +NGM={len(gm)} +NPOS={P} "
                                  f"+NEMIT={meta['emits']} +TB={events['TB']} +MODE={['full', 'probe', 'g22'].index(a.mode)}\n")
    print(json.dumps(meta)[:400])


if __name__ == '__main__':
    main()
