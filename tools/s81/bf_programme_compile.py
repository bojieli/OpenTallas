#!/usr/bin/env python3
"""S81 static BF programme compiler (S-BIND 2026-10-15).

Input: a compiled issue calendar per phase (here: the exact legacy-model trace of the real BF bench,
ot_v41_bf_front_core +define+OT_BF_ISSUE_TRACE -- an OFFLINE compile step: the hardware never sees it).
Output: one 82-bit descriptor per phase for ot_s81_bf_prog_seq (hex, one line per go in order) and a JSON receipt.
Every descriptor is checked by regenerating the phase's full 38-bit word stream and issue edges; any phase that is not
affine / modular in the issue index FAILS (exit 1) -- no approximation, no fallback.

  bf_programme_compile.py --trace bf_issue_trace.txt --hex desc.hex --receipt receipt.json
"""
import argparse, hashlib, json, sys
from pathlib import Path

DW = 82
ROOT = Path(__file__).resolve().parents[2]
NLOCK_SOURCE = 'rtl/s81/ot_s81_bf_front_roots.sv'
NLOCK_SHA256 = '1f3ec5b8008dfdecd16305cd5519bfbb677b379b349fe933ef5571a8467f84a2'


def boundary_descriptor(d, profile='legacy', source_root=ROOT):
    """Advance only the descriptor OFF for the extra Nlock input register.

    The sequencer remains DELTA=0; the core sees the same edge and word.
    Empty phases retain every bit and do not establish reset/fault qualification.
    """
    if profile not in ('legacy', 'c10_nlock'):
        raise ValueError('unknown BF programme boundary profile')
    if profile == 'legacy':
        return dict(d)
    source = Path(source_root) / NLOCK_SOURCE
    if hashlib.sha256(source.read_bytes()).hexdigest() != NLOCK_SHA256:
        raise ValueError('unmeasured BF Nlock source; new boundary proof required')
    return advance_descriptor(d)


def advance_descriptor(d):
    out = dict(d)
    if d['n']:
        out['off'] -= 1
        # RTL first_e = OFF + DELTA - 1, with DELTA fixed at zero.
        if out['off'] < 1:
            raise ValueError('BF Nlock first_e underflow; programme cannot launch before go')
    return out



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
    ap.add_argument('--boundary-profile', choices=['legacy', 'c10_nlock'], default='legacy',
                    help='c10_nlock: exact measured front, advance descriptor OFF one edge; sequencer DELTA remains zero')
    ap.add_argument('--source-root', type=Path, default=ROOT)
    a = ap.parse_args()
    rec = dict(schema='opentallas.s81.bf_programme.v1', dw=DW, phases=[], pass_=True)
    lines = []
    for k, ph in enumerate(phases(a.trace)):
        r = fit(ph)
        if isinstance(r, dict):
            d, bad = r, []
        else:
            d, bad = r
        emitted = boundary_descriptor(d, a.boundary_profile, a.source_root)
        # Independent consumers still expect the original core issue edges.
        for i, expected in enumerate(ph['ev']):
            actual = word(emitted, i)
            actual['off'] += int(a.boundary_profile == 'c10_nlock')
            if actual != expected:
                bad.append(i)
        rec['phases'].append(dict(phase=k, go_bf=ph['go_bf'], issues=len(ph['ev']), descriptor=emitted, mismatches=len(bad)))
        if bad:
            rec['pass_'] = False
        lines.append('%021x' % pack(emitted))
    rec.update(boundary_profile=a.boundary_profile, sequencer_delta=0,
               programme_pin_to_core_edges=2 if a.boundary_profile == 'c10_nlock' else 1,
               full_native_qualified=False,
               scope='Offline descriptor lowering only; actual full canonical programme/native replay and physical clock phases remain required')
    if a.boundary_profile == 'c10_nlock':
        rec['boundary_source'] = dict(path=NLOCK_SOURCE, sha256=NLOCK_SHA256)
        rec['empty_phase_fault_check'] = 'OPEN: empty descriptors unchanged; sequencer currently diagnoses OFF0 even when N0'
    Path(a.hex).write_text('\n'.join(lines) + '\n')
    rec['pass'] = rec.pop('pass_')
    rec['total_issues'] = sum(p['issues'] for p in rec['phases'])
    Path(a.receipt).write_text(json.dumps(rec, indent=1) + '\n')
    print('BF_PROGRAMME_COMPILE', 'PASS' if rec['pass'] else 'FAIL', 'phases', len(lines), 'issues', rec['total_issues'])
    return 0 if rec['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
