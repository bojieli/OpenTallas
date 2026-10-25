#!/usr/bin/env python3
"""Norm rstd and quantised wire payloads from genuine layer-entry inputs.

The fixture operation outputs are assertions only. Producers are h/pre and the
checkpoint gain. Timing is supplied separately by norm_q's static finish model.
"""
from pathlib import Path
import json
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]
import norm_nx as N
import rtl_hdc_v41_blockdot_campaign as AQ


def golden(fixtures):
    V = N._golden()
    F = np.float32
    old = V.ARITH
    V.set_arith('chunk8')
    try:
        h = N._arr(fixtures, 'io/h_in.bin').astype(F)
        pre = N._arr(fixtures, 'io/pre_in.bin').astype(F)
        gain = N._arr(fixtures, 'weights/attn_norm.bin').copy()
        gain = (gain.view('<u2').reshape(-1).astype(np.uint32) << 16).view(F)
        x = V.to_bf16(V.seqsum([V.mul(pre[j], h[j]) for j in range(4)]))
        p = np.asarray(N.partials(fixtures), np.uint32).view(F)
        total = F(V.split_sum_parts(p))
        config = json.loads((HERE.parents[2] / 'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
        eps = F(config['norm_eps'])
        rstd = V.rsqrt(V.add(V.div(total, F(len(x))), eps))
        y = V.to_bf16(V.mul(gain, V.mul(x, rstd)))
        for rel, value in [('attn.norm.rsqrt', np.asarray(rstd).reshape(1)),
                           ('attn.norm.scale', y)]:
            want = N._arr(fixtures, 'ops/' + rel + '.bin').astype(F)
            if not np.array_equal(np.asarray(value, F).view(np.uint32), want.view(np.uint32)):
                raise ValueError('norm quant golden differs from fixture ' + rel)
        beats = []
        for b in range(80):
            block = y[64 * b:64 * b + 64]
            q = []
            for half in range(2):
                fault, exponent, codes, _ = AQ.aq_expect(block[32 * half:32 * half + 32], False)
                if fault:
                    raise ValueError('non-finite norm quant input')
                q.append((int(exponent) & 0x3FF, int.from_bytes(bytes(np.asarray(codes, np.uint8)), 'little')))
            (e0, q0), (e1, q1) = q
            xq = q0 | e0 << 256 | q1 << 266 | e1 << 522
            xb = sum(int(v) << (16 * k) for k, v in enumerate(block.view(np.uint32) >> 16))
            beats.append(dict(index=b, sid=b // 5, leaf=b % 5, xq=xq, xb=xb))
        return dict(rstd=int(np.asarray(rstd, F).view(np.uint32)), beats=beats)
    finally:
        V.set_arith(old)


def word(payload, index, sid, kind, hops):
    """The 1,104-bit rstop word; no payload truncation and no masked codes."""
    if not 0 <= index < 256 or not 0 <= sid < 16 or kind not in (1, 2) or not 0 <= hops < 32:
        raise ValueError('invalid quant wire header')
    if not 0 <= payload < 1 << (532 if kind == 1 else 1024):
        raise ValueError('quant payload overflow')
    return 1 | kind << 1 | hops << 4 | sid << 9 | index << 13 | payload << 21


def fragments(payload, index, sid, kind):
    w = word(payload, index, sid, kind, 1)
    return [(w >> (276 * k)) & ((1 << 276) - 1) for k in range(4)]


def predicted_edges(schedule, die, q_after_root):
    """Static NX arrivals -> finish root -> first own quant line word per slice."""
    import re
    import norm_q as Q
    slices = die.slices()
    by_sid = {s['sid']: inst for inst, s in slices.items()}
    snake = []
    for e in schedule['events']:
        m = re.fullmatch(r'attn\.nx\.o(\d+)\.h(\d+)', str(e.get('tag', '')))
        if not m or e.get('kind') != 'NX':
            continue
        origin, hops = map(int, m.groups())
        _, dst, _, age = N._lane0(die, e['inst'], e['port'])
        snake.append(dict(inst=e['inst'], origin=origin, edge=e['cycle'],
                          dst=dst, land=e['cycle'] + age,
                          own=e['inst'] == by_sid[origin] and hops in (N.HE, N.HW)))
    arrivals = Q.arrivals(snake)
    if set(arrivals) != set(slices) or any(len(v) != 16 for v in arrivals.values()):
        raise ValueError('quant encoder requires all 16 norm flits on every slice')
    roots = {inst: Q.finish_root(dl) for inst, dl in arrivals.items()}
    return roots, {inst: edge + q_after_root for inst, edge in roots.items()}


def events(die, quant, q_edges):
    """Own, V-partner and forwarded XQ/XB words, preserving each global beat index.

    The caller must reject collisions before adopting this schedule. Keeping
    colliding predicted words here lets a diagnostic identify both producers.
    q_edges names actual output-register edges; no elastic link is approximated.
    """
    import norm_q as Q
    slices = die.slices()
    by_pos = {(s['sid'] >> 1, s['sid'] & 1): inst for inst, s in slices.items()}
    result = []

    def append(inst, port, edge, value, width, tag, kind):
        e = dict(cycle=edge, inst=inst, port=port, ports=[port], dir='out', kind=kind,
                 tag=tag, width=width, words=[[edge, f'{value:x}', f'{(1 << width) - 1:x}']],
                 source='entry h/pre + checkpoint gain through hdc_golden_v41 and actquant reference')
        if width == 1104:
            e['valid_bit'] = 0
        result.append(e)

    def walk(inst, side, edge, payload, index, sid, kind, origin):
        col, tier = slices[inst]['sid'] >> 1, slices[inst]['sid'] & 1
        hops = 7 - col if side == 'e' else col
        port = 'ro_e' if side == 'e' else 'ro_w'
        while hops:
            append(inst, port, edge, word(payload, index, sid, kind, hops), 1104,
                   f'attn.q.o{origin}.b{index}.k{kind}.h{hops}', 'XQ' if kind == 1 else 'XB')
            if hops == 1:
                break
            # Full line beats must wait for the slowest lane, not NX's lane0 age.
            links = [L for L in die.links.values() if (inst, port) in map(tuple, L['src'])]
            edge += max(L['age_edges'] for L in links) + Q.LINE_STOP
            col += 1 if side == 'e' else -1
            inst = by_pos[col, tier]
            hops -= 1

    for inst, q0 in sorted(q_edges.items()):
        sid = slices[inst]['sid']
        partner = by_pos[sid >> 1, 1 - (sid & 1)]
        vage = N._lane0(die, inst, 'vo')[3]
        for b in quant['beats'][5 * sid:5 * sid + 5]:
            for kind, offset, payload in [(1, 4 * b['leaf'], b['xq']), (2, 20 + 4 * b['leaf'], b['xb'])]:
                edge = q0 + offset
                for k, fragment in enumerate(fragments(payload, b['index'], sid, kind)):
                    append(inst, 'vo', edge - 4 + k, fragment, 276,
                           f'attn.q.v.o{sid}.b{b["index"]}.k{kind}.f{k}', 'XQFRAG')
                for side in ('e', 'w'):
                    walk(inst, side, edge, payload, b['index'], sid, kind, sid)
                    walk(partner, side, edge + vage + 2, payload, b['index'],
                         slices[partner]['sid'], kind, sid)
    return result
