#!/usr/bin/env python3
"""ETM-ARCS one-time audit (coordinator 10-22 14:30; NOT a standing gate): every die master lib in a views dir is
classified by its timing groups.  A master with a clock-like input pin (clk*, *_clk*, pg_clk*, ck, ckf, ck_*, ckf_*)
and ZERO setup / clock-edge arcs is FAIL (sequential master invisible to die STA).  hbfd_* masters must have >= 1
clock-related arc.  Prints per-family counts and writes a JSON report.

  etm_arcs_audit.py VIEWS_DIR REPORT.json [--corner tt]
"""
import collections, json, re, sys
from pathlib import Path

CLK = re.compile(r'^(clk|clk_\w+|\w+_clk|\w+_clk_\w+|pg_clk\w*|ck|ckf|ck_\w+|ckf_\w+)$')


def audit(lib):
    t = lib.read_text(errors='replace')
    pins = {}
    for m in re.finditer(r'pin\s*\(\s*"([^"]+)"\s*\)\s*\{\s*direction\s*:\s*(\w+)', t):
        pins[m.group(1)] = m.group(2)
    types = collections.Counter(re.findall(r'timing_type\s*:\s*"?(\w+)', t))
    ck_in = sorted(p for p, d in pins.items() if d == 'input' and CLK.match(p))
    seq = sum(v for k, v in types.items() if k.startswith(('setup_', 'rising_edge', 'falling_edge', 'hold_')))
    clk_rel = len(re.findall(r'related_pin\s*:\s*"(?:%s)"' % '|'.join(map(re.escape, ck_in)), t)) if ck_in else 0
    return dict(groups=sum(types.values()), seq=seq, clk_related=clk_rel, ck_inputs=ck_in, types=dict(types))


def main():
    vd, out = Path(sys.argv[1]), Path(sys.argv[2])
    corner = sys.argv[sys.argv.index('--corner') + 1] if '--corner' in sys.argv else 'tt'
    rows, fam = {}, collections.Counter()
    for lib in sorted(vd.glob(f'*_{corner}.lib')):
        r = audit(lib)
        name = lib.name[:-len(f'_{corner}.lib')]
        hb = name.startswith('hbfd_')
        r['verdict'] = ('FAIL' if (r['ck_inputs'] and r['seq'] == 0) or (hb and r['clk_related'] == 0) else
                        'PASS' if r['ck_inputs'] else 'COMB_OR_NOCLK')
        rows[name] = r
        fam[(re.sub(r'(__pv\d+|_tw|_(NS|SN|EW|WE)|_f\d|_\d+)', '', name), r['verdict'])] += 1
    cnt = collections.Counter(r['verdict'] for r in rows.values())
    json.dump(dict(views=str(vd), corner=corner, counts=dict(cnt), families={f'{a}:{b}': n for (a, b), n in sorted(fam.items())},
                   masters=rows), open(out, 'w'), indent=1)
    print('ETM_ARCS_AUDIT', dict(cnt))
    for (a, b), n in sorted(fam.items()):
        if b == 'FAIL':
            print('  FAIL family', a, n)


if __name__ == '__main__':
    main()
