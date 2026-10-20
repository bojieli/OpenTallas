#!/usr/bin/env python3
"""QW-XHEAD XT1 bench driver (tb_xt1.sv): real L0 matvec ops through dvs_W5's column heads into the c16_W5_1 cluster with
real TP8 rank-0 code ROMs; every cluster rs word bit-exact vs the golden level-6 part (xt1_prep.py gold.json).

  xt1_bench.py gen   --gold prep/gold.json --out EV [--mode M] [--lead L] [--gap G]
  xt1_bench.py check --gold prep/gold.json --log LOG [--mode M] [--lead L] [--gap G]  -> one RESULT line + JSON

hr word driven in the SLICE's layout {go [452], ib [451:73] (ot_qwen_me_array_w12 order: nout .. mbase), xpf [72:1], v
[0]} built from the tt_ctlm ROM command (cmd380 {mbase .. nout, go}, the unit_c4 stage-1 log).  Per op: XPF on edge T,
the x beats (stream kind-0 words on st_up_i, 64 BF16, one an edge) from T + lead, go at last beat + gap.
Modes: nominal (lead 8 gap 4) | sweep values via --lead/--gap | asbuilt (hr exactly as qfd_tt_ctlm_dv emits it:
{cmd380, xpf, v}: the die path today) | xbase1 (ib xbase + 1) | romswap (same events; masks of tiles 16/17 swapped).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ibdec as I            # noqa: E402

ORDER = ('qkv', 'o', 'gu', 'down')
T0, SPACING = 60, 1600
LOG_XPF = dict(qkv='800112002010002001', o='800050002004018be1', gu='80040e002040002001', down='8000d000200c01afe1')
# full stage-1 ROM commands (cmd380 hex, unit_c4 log_m0_b0.txt edges 1224 / 3415 / 5062 / 5746)
LOG_ROM = dict(
    qkv='00000020000010000080003008000004800000800000000000100100000000100000800004000000000010000080601',
    o='00000020000010000080000008000184000000200000000000100c5f000000100000800001000004000004000182001',
    gu='0000002000001000008000b9f8000a83800002000000000000100100000000100000800010000007000040000081801',
    down='00000020000010000080000008001084000000600000000000100d7f00000010000080000300001700000c000182001')


def dec380(h):
    v = int(h, 16)
    out, pos = {'go': v & 1}, 1
    for n, w in I.FIELDS:
        out[n] = (v >> pos) & ((1 << w) - 1)
        pos += w
    return v, out


def xpf72(f):
    return ((f['round'] & 1) << 71) | (f['k'] << 53) | (f['split'] << 49) | (f['xks'] << 37) | (f['xcs'] << 25) | \
           (f['xbase'] << 1) | 1


def schedule(gold, lead, gap):
    s = {}
    for n, name in enumerate(ORDER):
        t = T0 + SPACING * n
        nb = len(gold[name]['x_beats'])
        s[name] = dict(xpf=t, beat0=t + lead, beat_last=t + lead + nb - 1, go=t + lead + nb - 1 + gap)
    return s


def gen(a, gold):
    ev = [(10, 0, 0x1 | (7 << 1) | (0 << 4))]            # SETID 0 (W5)
    sch = schedule(gold, a.lead, a.gap)
    for name in ORDER:
        raw, f = dec380(LOG_ROM[name])
        op = gold[name]['op']
        for k in ('nout', 'tiles', 'k', 'wbase', 'ts', 'ks', 'js', 'split', 'xbase', 'xcs', 'xks'):
            if f[k] != op[k]:
                raise SystemExit(f'{name}: ROM command {k} {f[k]} != prep {op[k]}')
        x72 = xpf72(f)
        if x72 != int(LOG_XPF[name], 16):
            raise SystemExit(f'{name}: XPF {x72:018x} != log {LOG_XPF[name]}')
        g = dict(f)
        if a.mode == 'xbase1':
            g['xbase'] += 1
        ib = I.enc_ib(g)
        s = sch[name]
        if a.mode == 'asbuilt':                           # qfd_tt_ctlm_dv: hr <= {ib = cmd380, xpf, hv}
            ev.append((s['xpf'], 1, (x72 << 1) | 1))
            ev.append((s['go'], 1, (raw << 73) | 1))
        else:
            ev.append((s['xpf'], 1, (x72 << 1) | 1))
            ev.append((s['go'], 1, (1 << 452) | (ib << 73) | 1))
        for i, b in enumerate(gold[name]['x_beats']):
            w = (1 << 1087) | (0 << 1084) | (0xF << 1080) | (b['eaddr'] << 1052) | int(b['payload'], 16)
            ev.append((s['beat0'] + i, 2, w))
    ev.sort(key=lambda e: (e[0], e[1]))
    with open(a.out, 'w') as fo:
        for c, p, v in ev:
            fo.write(f'{c} {p} {v:x}\n')
    Path(a.out + '.sched.json').write_text(json.dumps(sch))
    print(f'GEN {a.mode} lead {a.lead} gap {a.gap} events {len(ev)} ncyc {T0 + SPACING * len(ORDER)}')


def check(a, gold):
    sch = schedule(gold, a.lead, a.gap)
    lines = Path(a.log).read_text().split('\n')
    hr, cw, rs, faults, end = [], [], [], [], None
    for ln in lines:
        p = ln.split()
        if len(p) < 2:
            continue
        c = int(p[0])
        if p[1] == 'HRGO':
            hr.append(c)
        elif p[1] == 'CWGO':
            cw.append((c, p[2]))
        elif p[1] == 'RS':
            rs.append((c, int(p[2]), p[3]))
        elif p[1] == 'FAULT':
            faults.append((c, p[2]))
        elif p[1] == 'END':
            end = ln
    errs, per = [], {}
    nok = ntot = 0
    for n, name in enumerate(ORDER):
        s = sch[name]
        lo, hi = s['go'], s['go'] + SPACING - 200
        exp = gold[name]['words']
        allw = [r for r in rs if lo <= r[0] < hi]
        # the tiles' lanes emit the running accumulator every issue edge (t_vout each (r, k, j); XT1 trace 10-19: tile 16
        # t_out == the in-order lane sums 64/64); the op's level-6 result is the k = kc - 1 word of each (r, j): the
        # consumer selects it by the static schedule.  Count check on all words, value check on the final ones.
        kc = gold[name]['op']['k']
        nr = len(exp) // 8
        if len(allw) != nr * kc * 8:
            errs.append(f'{name}: {len(allw)} rs words, expected {nr * kc * 8} (= rounds x k x 8)')
        got = [allw[r * kc * 8 + (kc - 1) * 8 + j] for r in range(nr) for j in range(8) if r * kc * 8 + (kc - 1) * 8 + j < len(allw)]
        cws = [c for c in cw if lo <= c[0] < lo + 100]
        d = dict(hr_go=s['go'], cw_go=[c for c, _ in cws][:1], rs_edges=[r[0] for r in got])
        if not cws:
            errs.append(f'{name}: no column go on cw_s* after the hr go')
        else:
            d['d_head'] = cws[0][0] - s['go']
            d['cw_go_columns'] = cws[0][1]
        if got:
            d['d_clu'] = allw[0][0] - (cws[0][0] if cws else s['go'])
            d['first_rs'] = allw[0][0] - s['go']
            d['first_final'] = got[0][0] - s['go']
            d['last_final'] = got[-1][0] - s['go']
            rounds = []
            for r in range(len(exp) // 8):
                ed = [g[0] for g in got[8 * r:8 * r + 8]]
                if ed:
                    rounds.append(dict(first=ed[0] - s['go'], last=ed[-1] - s['go'], words=len(ed)))
            d['rounds'] = rounds
            if len(rounds) > 1:
                d['round_period'] = [rounds[i + 1]['first'] - rounds[i]['first'] for i in range(len(rounds) - 1)]
        ok = 0
        for i, e in enumerate(exp):
            ntot += 1
            if i < len(got) and got[i][1] == 0 and got[i][2] == e['word']:
                ok += 1
            elif i < len(got):
                if len(errs) < 12:
                    errs.append(f'{name} word {i} (round {e["round"]} block {e["block"]} j {e["j"]}) at {got[i][0]}: '
                                f'fault {got[i][1]} data mismatch' if got[i][2] != e['word'] else f'{name} word {i} fault')
        if len(got) != len(exp):
            errs.append(f'{name}: {len(got)} rs words, expected {len(exp)}')
        nok += ok
        d['exact'] = f'{ok}/{len(exp)}'
        per[name] = d
    if faults:
        errs.append(f'faults {faults}')
    v = 'PASS' if not errs and nok == ntot and ntot else 'FAIL'
    res = dict(verdict=v, mode=a.mode, lead=a.lead, gap=a.gap, exact=f'{nok}/{ntot}', per_op=per, errors=errs, end=end)
    print(f'RESULT XT1 {v} mode={a.mode} lead={a.lead} gap={a.gap} exact {nok}/{ntot} ' + json.dumps(
        {k: {kk: per[k].get(kk) for kk in ('d_head', 'd_clu', 'first_rs', 'first_final', 'last_final', 'round_period', 'exact')} for k in per}))
    for e in errs[:12]:
        print('  ERR', e)
    Path(a.log + '.result.json').write_text(json.dumps(res, indent=1))
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('gen', 'check'))
    ap.add_argument('--gold', required=True)
    ap.add_argument('--out')
    ap.add_argument('--log')
    ap.add_argument('--mode', default='nominal')
    ap.add_argument('--lead', type=int, default=8)
    ap.add_argument('--gap', type=int, default=4)
    a = ap.parse_args()
    gold = json.loads(Path(a.gold).read_text())
    if a.cmd == 'gen':
        gen(a, gold)
    else:
        sys.exit(0 if check(a, gold) == 'PASS' else 1)


if __name__ == '__main__':
    main()
