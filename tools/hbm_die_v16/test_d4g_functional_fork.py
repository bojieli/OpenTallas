#!/usr/bin/env python3
"""DIE-HBM-LEAD 10-19: unit test of d4g_functional_bind.check on (1) fork landing stations hbfd_lh*_f<N> (b is N*W wide,
b[k*W + j] = a[j]) -- GEN2 post-landing: 62 cij idx_tx paths were reported 'undriven' because the trace kept the fork
index -- and (2) split parents (contract 'split_parents', l9_gen2c_views).  Pure python, no RTL.  Exit 1 on failure."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_functional_bind as FB  # noqa: E402


def contract(fork_branch=1, wrong_bit=False):
    W = 4
    inst = {
        'A': dict(master='ot_prod', ports={'x': dict(direction='output', bits=W)}),
        'f': dict(master='hbfd_lh_136_WE_f2', ports={'a': dict(direction='input', bits=W), 'b': dict(direction='output', bits=2 * W)}),
        'l': dict(master='hbfd_land_136_WE', ports={'a': dict(direction='input', bits=W), 'b': dict(direction='output', bits=W)}),
        'r': dict(master='hbfd_rly_136_WE', ports={'i': dict(direction='input', bits=W), 'o': dict(direction='output', bits=W)}),
        'Z_q': dict(master='ot_cons_q', ports={'y': dict(direction='input', bits=W)}),
    }
    lo = fork_branch * W
    e = [dict(name='e0', bits=W, source=['A', 'x', 0, W], sink=['f', 'a', 0, W]),
         dict(name='e1', bits=W, source=['f', 'b', lo, lo + W], sink=['l', 'a', 0, W]),
         dict(name='e2', bits=W, source=['l', 'b', 0, W], sink=['r', 'i', 0, W])]
    if wrong_bit:   # mutant: bits 0/1 swapped after the landing
        e += [dict(name='e3a', bits=1, source=['r', 'o', 1, 2], sink=['Z_q', 'y', 0, 1]),
              dict(name='e3b', bits=1, source=['r', 'o', 0, 1], sink=['Z_q', 'y', 1, 2]),
              dict(name='e3c', bits=2, source=['r', 'o', 2, 4], sink=['Z_q', 'y', 2, 4])]
    else:
        e.append(dict(name='e3', bits=W, source=['r', 'o', 0, W], sink=['Z_q', 'y', 0, W]))
    return dict(instances=inst, edges=e, straps=[], split_parents={'Z': dict(master='ot_cons', ports={'y': [['Z_q', 'y']]})})


def run(c):
    S = [dict(gap='G-T', cls='T', kind='data', src=['A', 'x', 0], dst=['Z', 'y', 0], w=4)]   # written against the parent Z
    return FB.check(c, S)[0]


ok = True
for br in (0, 1):
    r = run(contract(br))
    good = r['status'] == 'PASS' and r['landed']
    print(f'fork branch {br}: {r["status"]} landed {r["landed"]} {r["bad"]}', 'OK' if good else 'BAD')
    ok &= good
r = run(contract(1, wrong_bit=True))
good = r['status'] == 'FAIL'
print(f'mutant bit swap: {r["status"]} {r["bad"]}', 'OK' if good else 'BAD (mutant not caught)')
ok &= good
print('TEST_D4G_FUNCTIONAL_FORK', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
