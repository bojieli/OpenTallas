#!/usr/bin/env python3
"""G0/G0C ERROR rows by class, old vs new report; flags latency / reset-equation rows (never baselinable, COORD 11-12).
usage: g0_classes.py OLD_g0_report.json NEW_g0_report.json"""
import collections
import json
import re
import sys

LAT = re.compile(r'latenc|equation|reset (release )?depth|lane .*cycles?|!= latency|STALE_TABLE', re.I)


def cls(f):
    m = f['msg']
    c = f['check']
    if c == 'clock_landings':
        if 'incoming edges' in m:
            return 'clock_landings/START fan-in 0'
        if 'envelope hop' in m:
            return 'clock_landings/START envelope hop >405'
        if 'actual endpoint hop' in m:
            return 'clock_landings/cland_mon endpoint hop >405'
    if c == 'complete':
        return 'complete/' + (m.split(']')[0].lstrip('[') if m.startswith('[') else 'other')
    return c


def load(p):
    errs = [f for f in json.load(open(p))['findings'] if f['level'] == 'ERROR']
    return errs, collections.Counter(cls(f) for f in errs)


def main(a):
    eo, co = load(a[1])
    en, cn = load(a[2])
    print(f'ERRORS old {len(eo)} new {len(en)}')
    for k in sorted(set(co) | set(cn), key=lambda k: -cn.get(k, 0)):
        d = cn.get(k, 0) - co.get(k, 0)
        print(f'  {k:48s} {co.get(k, 0):5d} -> {cn.get(k, 0):5d}  {d:+d}' if d else f'  {k:48s} {co.get(k, 0):5d} -> {cn.get(k, 0):5d}')
    lat = [f for f in en if f['check'] == 'latency' or LAT.search(f['msg'])]
    print(f'LATENCY_OR_RESET_EQ_ROWS {len(lat)}')
    for f in lat[:10]:
        print('   ', f['check'], f['msg'][:220])
    return 1 if lat else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
