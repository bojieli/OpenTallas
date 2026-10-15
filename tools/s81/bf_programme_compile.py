#!/usr/bin/env python3
"""S81 static BF programme compiler (S-BIND 2026-10-15).

Input: a compiled issue calendar per phase (here: the exact legacy-model trace of the real BF bench,
ot_v41_bf_front_core +define+OT_BF_ISSUE_TRACE -- an OFFLINE compile step: the hardware never sees it).
Output: one 82-bit descriptor per phase for ot_s81_bf_prog_seq (hex, one line per go in order) and a JSON receipt.
Every descriptor is checked by regenerating the phase's full 38-bit word stream and issue edges; any phase that is not
affine / modular in the issue index FAILS (exit 1) -- no approximation, no fallback.

  bf_programme_compile.py --trace bf_issue_trace.txt --hex desc.hex --receipt receipt.json
"""
import argparse, json, sys
from pathlib import Path

DW = 82


def phases(path):
    out, cur = [], None
    for ln in Path(path).read_text().split('\n'):
        f = ln.split()
        if not f:
            continue
        if f[0] == 'G':
            cur = dict(go_cycle=int(f[1]), go_bf=int(f[2]), ev=[])
            out.append(cur)
        elif f[0] == 'I':
            off, a, op, s, h, c, gb = map(int, f[2:9])
            cur['ev'].append(dict(off=off, addr=a, op=op, seg=s, half=h, chain=c))
    return out


def word(d, i):
    lb, lu = d['lb'], d['lu']
    ib = i >> lb
    blk = (i >> (3 + lu + lb)) & 63
    unit = ib & ((8 << lu) - 1) & 255
    return dict(off=d['off'] + d['per'] * ib + (i & ((1 << lb) - 1)), addr=(d['base'] + (i & d['am'])) & 0x3fff,
                op=(d['fam'] << 14) | (blk << 8) | unit, seg=(i >> d['ssh']) & d['sm'], half=i & ((1 << lb) - 1),
                chain=i & d['cm'])


def fit(ph):
    ev = ph['ev']
    n = len(ev)
    if n == 0:
        return dict(n=0, lb=0, off=0, per=0, base=0, am=0, fam=0, lu=0, ssh=0, sm=0, cm=0)
    lb = 1 if n > 1 and ev[1]['off'] == ev[0]['off'] + 1 else 0
    per = (ev[1 << lb]['off'] - ev[0]['off']) if n > (1 << lb) else 0
    base = ev[0]['addr']
    am = 0
    for i, e in enumerate(ev):
        am = max(am, e['addr'] - base)
    am_p = 1
    while am_p - 1 < am:
        am_p <<= 1
    cm = max(e['chain'] for e in ev)
    sm = max(e['seg'] for e in ev)
    ssh = next((r for r in range(8) if all(e['seg'] == (i >> r) & sm for i, e in enumerate(ev))), None)
    units = [e['op'] & 255 for e in ev]
    umax = max(units) + 1
    lu = next((k for k in range(4) if (8 << k) >= umax), None)
    d = dict(n=n, lb=lb, off=ev[0]['off'], per=per, base=base, am=am_p - 1, fam=ev[0]['op'] >> 14, lu=lu or 0,
             ssh=ssh if ssh is not None else 0, sm=sm, cm=cm)
    bad = [i for i, e in enumerate(ev) if word(d, i) != e]
    return d, bad


def pack(d):
    v = (d['n'] | d['lb'] << 14 | d['off'] << 15 | d['per'] << 23 | d['base'] << 31 | d['am'] << 45 | d['fam'] << 59 |
         d['lu'] << 60 | d['ssh'] << 66 | d['sm'] << 69 | d['cm'] << 72)
    assert v < (1 << DW)
    assert d['off'] < 256 and d['per'] < 256 and d['n'] < (1 << 14) and d['sm'] < 8 and d['cm'] < 16
    return v


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--trace', required=True)
    ap.add_argument('--hex', required=True)
    ap.add_argument('--receipt', required=True)
    a = ap.parse_args()
    rec = dict(schema='opentallas.s81.bf_programme.v1', dw=DW, phases=[], pass_=True)
    lines = []
    for k, ph in enumerate(phases(a.trace)):
        r = fit(ph)
        if isinstance(r, dict):
            d, bad = r, []
        else:
            d, bad = r
        rec['phases'].append(dict(phase=k, go_bf=ph['go_bf'], issues=len(ph['ev']), descriptor=d, mismatches=len(bad)))
        if bad:
            rec['pass_'] = False
        lines.append('%021x' % pack(d))
    Path(a.hex).write_text('\n'.join(lines) + '\n')
    rec['pass'] = rec.pop('pass_')
    rec['total_issues'] = sum(p['issues'] for p in rec['phases'])
    Path(a.receipt).write_text(json.dumps(rec, indent=1) + '\n')
    print('BF_PROGRAMME_COMPILE', 'PASS' if rec['pass'] else 'FAIL', 'phases', len(lines), 'issues', rec['total_issues'])
    return 0 if rec['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
