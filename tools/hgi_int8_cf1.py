#!/usr/bin/env python3
"""hbm-forks (2026-10-09, CF-1 / CF-SM of the SM INT8 front): the DS sequences run on ot_hbm_accel_smh with the INT8
front built in (ENABLE_INT8 = 1, PIPE 0 / 1) must be CYCLE-IDENTICAL to the default build (every op's event cycles
t_load0 / t_post / t_firstline / t_lastline / t_done and the total) and exact; the no-bypass mutant must differ.
  python3 tools/hgi_int8_cf1.py BASE.json CAND.json [--expect-differ]
"""
import json
import sys


def main():
    a, b = (json.load(open(p)) for p in sys.argv[1:3])
    differ = '--expect-differ' in sys.argv
    bad = []
    if a['status'] != 'pass' or b['status'] != 'pass':
        bad.append(f"status {a['status']} / {b['status']}")
    if a['total_cycles'] != b['total_cycles']:
        bad.append(f"total {a['total_cycles']} / {b['total_cycles']}")
    for x, y in zip(a['ops'], b['ops']):
        if x['rtl'] != y['rtl']:
            bad.append(f"op {x['op']} {x['tag']}: " + ', '.join(f"{k} {x['rtl'].get(k)}/{y['rtl'].get(k)}"
                                                                for k in x['rtl'] if x['rtl'].get(k) != y['rtl'].get(k)))
    same = not bad
    print('CF1_INT8', 'IDENTICAL' if same else 'DIFFER', a['seq'], a['total_cycles'], b['total_cycles'], '; '.join(bad[:4]))
    return 0 if same != differ else 1


if __name__ == '__main__':
    raise SystemExit(main())
