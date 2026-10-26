#!/usr/bin/env python3
"""Fail closed when Verilator emitted a packed-vector non-blocking loop WITHOUT its __Vdly shadow.

Root cause found 2026-10-15 (H-ATTQ): Verilator 5.050 with --unroll-count 1 compiled 96 instances of
ot_hdc_v41x_vdly (``for (i=1;i<=D;i++) r[i] <= (i==1) ? d : r[i-1];``, merge levels 1..3 of all 32 tiles in the
HG1 full-shape bench) as an in-place ascending loop on ``r`` itself: blocking semantics, every bit collapses to d,
valid crosses a merge level in 1 cycle instead of FPL=6 while its tags take 6 -> only 1 of 16 final PV beats
overlapped fin (observed 512/8192 words). The RTL is correct; the simulation model was not.

Usage: check_nba_loop_shadow.py OBJ_DIR [OBJ_DIR...]; exit 1 if any unshadowed loop is found.
Benches now use --unroll-count 128 (every vdly/dly loop is unrolled) and run this check after the build.
"""
import collections, glob, re, sys

PAT = re.compile(r'^\s*vlSelfRef\.(\S+?)\s*\n\s*=\s*\(\(\(~ \(\((?:IData|QData|CData|SData)\)\(1U\) << \((\w+) & '
                 r'vlSelfRef\.(\S+?)\)\)\)\s*\n\s*& \((?:IData|QData|CData|SData)\)\(vlSelfRef\.(\S+?)\)\)', re.M)


def scan(d):
    bad = collections.Counter(); good = 0
    for f in glob.glob(d + '/**/*.cpp', recursive=True):
        if 'Slow' in f:
            continue
        for m in PAT.finditer(open(f, errors='replace').read()):
            tgt = m.group(1)
            if tgt.startswith('__Vdly__'):
                good += 1
            else:
                bad[re.sub(r'BRA__\d+__KET', 'BRA__N__KET', tgt)] += 1
    return good, bad


def main():
    rc = 0
    for d in sys.argv[1:]:
        good, bad = scan(d)
        print(f'{d}: shadowed_loops={good} UNSHADOWED_loops={sum(bad.values())}')
        for k, v in bad.most_common(20):
            print(f'  UNSHADOWED x{v} {k[:220]}')
        rc |= bool(bad)
    sys.exit(rc)


if __name__ == '__main__':
    main()
